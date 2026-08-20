import pytest

from project.draft.config import LeagueConfig
from project.draft.mcts import MCTSDraftAssistant
from project.draft.mcts_parallel import get_best_pick_parallel, merge_visit_counts


def test_merge_sums_visits_across_fake_trees():
    fake_trees = [
        {"Player A": 10, "Player B": 5},
        {"Player A": 3, "Player C": 7},
        {"Player B": 2},
    ]
    merged = merge_visit_counts(fake_trees)

    assert merged == {"Player A": 13, "Player B": 7, "Player C": 7}
    assert max(merged, key=merged.get) == "Player A"


def _tiny_league_config():
    # Small enough (2 teams x 6 rounds = 12 total picks) that a rollout can
    # never deplete the 33-row sample_player_pool before hitting the
    # pick-count terminal condition -- see the depletion note in
    # MCTS._simulate. Real usage stays clear of this because the live/static
    # data (400-600+ rows) comfortably outlasts realistic league sizes.
    return LeagueConfig(
        num_teams=2,
        roster_slots={"QB": 1, "RB": 1, "WR": 1, "K": 1, "DST": 1},
        flex_eligible=(),
        bench_slots=1,
    )


@pytest.mark.slow
def test_parallel_search_completes_within_time_budget(sample_player_pool):
    cfg = _tiny_league_config()
    rosters = {i: [] for i in range(cfg.num_teams)}

    pick = get_best_pick_parallel(
        sample_player_pool, cfg, initial_pick=1, current_pick=1, current_round=1,
        rosters=rosters, current_player=0, exploration_constant=1.414,
        time_limit=1, num_workers=2,
    )

    assert pick in sample_player_pool["Player"].values


def test_single_threaded_path_still_available(sample_player_pool):
    cfg = _tiny_league_config()
    rosters = {i: [] for i in range(cfg.num_teams)}
    assistant = MCTSDraftAssistant(sample_player_pool, cfg, initial_pick=1,
                                    time_limit=1, parallel=False)

    pick = assistant.get_best_pick(sample_player_pool, current_pick=1,
                                    current_round=1, rosters=rosters, current_player=0)

    assert pick in sample_player_pool["Player"].values
