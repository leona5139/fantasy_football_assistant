"""Root parallelization for MCTS: run N independent trees (one per CPU core),
each searching the same state for the full time budget, then merge by summing
visit counts across trees' root children. This is the safe/bounded way to
parallelize MCTS -- each worker owns an independent tree with no shared
mutable state, so there's no risk of subtle concurrency bugs. It buys either
faster answers or more total playouts within the same wall-clock budget.

Kept in its own module (separate from mcts.py) to isolate multiprocessing/
pickling-specific code from the core search logic.
"""

import os
import random
from concurrent.futures import ProcessPoolExecutor

from project.draft.mcts import GameState, MCTS


def merge_visit_counts(visit_count_dicts):
    """Sum per-action visit counts across multiple trees' root children."""
    merged = {}
    for counts in visit_count_dicts:
        for action, visits in counts.items():
            merged[action] = merged.get(action, 0) + visits
    return merged


def _run_single_search(args):
    """Must be a module-level function (not a closure/bound method) so
    ProcessPoolExecutor can pickle it as the worker target."""
    (available_players, league_config, initial_pick, current_pick, current_round,
     rosters, current_player, exploration_constant, time_limit, seed) = args

    random.seed(seed)

    state = GameState(
        available_players, league_config, initial_pick,
        current_pick, current_round, rosters, current_player,
    )
    mcts = MCTS(exploration_constant)
    root = mcts.search_and_return_root(state, time_limit)

    return {action: child.visits for action, child in root.children.items()}


def get_best_pick_parallel(available_players, league_config, initial_pick, current_pick,
                            current_round, rosters, current_player, exploration_constant,
                            time_limit, num_workers=None):
    num_workers = num_workers or os.cpu_count() or 1

    # Each worker gets the FULL time budget, not a divided share -- that's
    # the point of root parallelization: same wall clock, more total playouts.
    args_list = [
        (available_players, league_config, initial_pick, current_pick, current_round,
         rosters, current_player, exploration_constant, time_limit, seed)
        for seed in range(num_workers)
    ]

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(_run_single_search, args_list))

    merged = merge_visit_counts(results)
    if not merged:
        return None
    return max(merged, key=merged.get)
