import pandas as pd

from project.draft.config import LeagueConfig
from project.draft.scoring import compute_roster_value


def _roster(rows):
    return [pd.Series(row) for row in rows]


def test_reward_uses_correct_case_and_column():
    roster = _roster(
        [
            {"Player": "QB1", "Position": "QB", "Total_FPTS": 300.0},
            {"Player": "RB1", "Position": "RB", "Total_FPTS": 200.0},
        ]
    )
    value = compute_roster_value(roster, LeagueConfig())
    # Previously this returned 0 (lowercase-position bug emptied every
    # bucket) or raised (nonexistent actual_points column / .nlargest on a
    # plain list).
    assert value > 0


def test_reward_respects_flex_and_bench_weighting():
    cfg = LeagueConfig()  # RB starters=2, FLEX=1 (RB/WR/TE eligible)
    roster = _roster(
        [
            {"Player": "RB1", "Position": "RB", "Total_FPTS": 250.0},
            {"Player": "RB2", "Position": "RB", "Total_FPTS": 200.0},
            {"Player": "RB3", "Position": "RB", "Total_FPTS": 150.0},  # -> FLEX
            {"Player": "RB4", "Position": "RB", "Total_FPTS": 50.0},   # -> bench
        ]
    )
    value = compute_roster_value(roster, cfg)
    expected = 250.0 + 200.0 + 150.0 + 50.0 * 0.3
    assert value == expected
