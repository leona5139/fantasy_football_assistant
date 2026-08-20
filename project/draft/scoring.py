"""Roster-value scoring for MCTS reward, isolated from the search so it's
independently testable.

Fixes two bugs found in the pre-refactor mcts.py `GameState.get_reward`:
1. It compared lowercase position strings ("qb", "rb", ...) against the real
   data's uppercase values ("QB", "RB", ...), so every positional bucket was
   always empty.
2. It called `.nlargest` on a nonexistent `actual_points` column against a
   plain list (a roster is `list[pd.Series]`, not a DataFrame) -- this raised
   / returned nothing meaningful rather than a real starter-lineup value.
"""

import pandas as pd


def compute_roster_value(roster, league_config):
    """Starter-lineup value (best player filling each roster slot, including
    FLEX) plus 0.3x the value of whatever's left on the bench.
    """
    if not roster:
        return 0.0

    df = pd.DataFrame(roster)
    used_index = set()
    play_score = 0.0

    for pos, count in league_config.roster_slots.items():
        if pos == "FLEX" or count <= 0:
            continue
        top = df[df["Position"] == pos].sort_values("Total_FPTS", ascending=False).head(count)
        play_score += top["Total_FPTS"].sum()
        used_index.update(top.index)

    flex_count = league_config.roster_slots.get("FLEX", 0)
    if flex_count > 0:
        flex_pool = df[df["Position"].isin(league_config.flex_eligible) & ~df.index.isin(used_index)]
        flex_top = flex_pool.sort_values("Total_FPTS", ascending=False).head(flex_count)
        play_score += flex_top["Total_FPTS"].sum()
        used_index.update(flex_top.index)

    bench_score = df.loc[~df.index.isin(used_index), "Total_FPTS"].sum() * 0.3

    return float(play_score + bench_score)
