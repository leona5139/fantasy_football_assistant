import pytest

from project.draft.config import LeagueConfig
from project.draft.greedy import DraftEnv
from project.draft.mcts import MCTSDraftEnv
from project.draft.pick_order import (
    calculate_pick_order,
    our_pick_positions,
    round_for_pick,
    team_for_pick,
)

CONFIGS = [
    (10, "snake", 1),
    (10, "snake", 5),
    (10, "snake", 10),
    (10, "regular", 4),
    (12, "snake", 12),
    (2, "snake", 1),
    (2, "snake", 2),
]


@pytest.mark.parametrize("num_teams, draft_style, initial_pick", CONFIGS)
def test_our_pick_positions_matches_draft_env(sample_player_pool, num_teams, draft_style, initial_pick):
    cfg = LeagueConfig(num_teams=num_teams, draft_style=draft_style)
    env = DraftEnv(sample_player_pool, cfg, initial_pick=initial_pick)

    ours = our_pick_positions(initial_pick, num_teams, cfg.num_rounds, draft_style)

    assert ours == env.pick_positions


@pytest.mark.parametrize("num_teams, draft_style, initial_pick", CONFIGS)
def test_team_for_pick_matches_mcts_draft_env(sample_player_pool, num_teams, draft_style, initial_pick):
    cfg = LeagueConfig(num_teams=num_teams, draft_style=draft_style)
    env = MCTSDraftEnv(sample_player_pool, cfg, initial_pick=initial_pick, mcts_time_limit=0)

    max_picks = num_teams * cfg.num_rounds
    for pick_number in range(1, max_picks + 1):
        env.current_pick = pick_number
        expected_team = env.get_current_player()
        assert team_for_pick(pick_number, num_teams, draft_style) == expected_team


@pytest.mark.parametrize("num_teams, draft_style, initial_pick", CONFIGS)
def test_calculate_pick_order_matches_team_for_pick(num_teams, draft_style, initial_pick):
    num_rounds = 6
    order = calculate_pick_order(num_teams, num_rounds, draft_style)

    assert order == [
        team_for_pick(p, num_teams, draft_style) for p in range(1, num_teams * num_rounds + 1)
    ]


def test_round_for_pick():
    assert round_for_pick(1, 10) == 1
    assert round_for_pick(10, 10) == 1
    assert round_for_pick(11, 10) == 2
    assert round_for_pick(20, 10) == 2
    assert round_for_pick(21, 10) == 3
