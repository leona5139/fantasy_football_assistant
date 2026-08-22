import pytest

from project.draft.config import LeagueConfig
from project.draft.scoring import compute_roster_value
from project.webapp.session import DraftSession


def _top_names(pool, n):
    return pool.sort_values("Rank")["Player"].head(n).tolist()


def test_apply_pick_advances_pick_round_team_across_snake_boundary(sample_player_pool):
    cfg = LeagueConfig(num_teams=10)
    session = DraftSession(sample_player_pool, cfg, initial_pick=1)

    names = _top_names(sample_player_pool, 11)
    for name in names[:10]:
        session.apply_pick(name)

    assert session.current_pick == 11
    assert session.current_round == 2
    # Snake round 2 reverses order -- team 9 (0-indexed) picks first.
    assert session.current_team == 9
    assert session.is_our_pick is False  # our_team_idx is 0

    session.apply_pick(names[10])
    assert len(session.pick_history) == 11
    assert session.pick_history[-1]["team_idx"] == 9
    assert session.pick_history[-1]["is_ours"] is False


def test_apply_pick_raises_on_unknown_player(sample_player_pool):
    session = DraftSession(sample_player_pool, LeagueConfig(num_teams=10), initial_pick=1)
    with pytest.raises(ValueError):
        session.apply_pick("Not A Real Player")


def test_apply_pick_raises_on_already_drafted_player(sample_player_pool):
    session = DraftSession(sample_player_pool, LeagueConfig(num_teams=10), initial_pick=1)
    name = _top_names(sample_player_pool, 1)[0]
    session.apply_pick(name)
    with pytest.raises(ValueError):
        session.apply_pick(name)


def test_undo_restores_state_byte_for_byte(sample_player_pool):
    cfg = LeagueConfig(num_teams=10)
    session = DraftSession(sample_player_pool, cfg, initial_pick=1)
    names = _top_names(sample_player_pool, 3)

    session.apply_pick(names[0])
    session.apply_pick(names[1])
    snapshot = session.state()
    snapshot_available = session.available_players.copy()
    snapshot_roster_filled = dict(session.greedy.roster_filled)

    session.apply_pick(names[2])
    session.undo()

    assert session.state() == snapshot
    assert session.available_players["Player"].tolist() == snapshot_available["Player"].tolist()
    assert session.greedy.roster_filled == snapshot_roster_filled


def test_multiple_sequential_undos(sample_player_pool):
    cfg = LeagueConfig(num_teams=10)
    session = DraftSession(sample_player_pool, cfg, initial_pick=1)
    names = _top_names(sample_player_pool, 3)

    for name in names:
        session.apply_pick(name)
    assert session.current_pick == 4

    session.undo()
    session.undo()
    session.undo()

    assert session.current_pick == 1
    assert session.pick_history == []
    assert len(session.available_players) == len(sample_player_pool)
    assert all(v == 0 for v in session.greedy.roster_filled.values())

    # Undoing with no history left is a no-op, not an error.
    session.undo()
    assert session.current_pick == 1


def test_our_roster_value_matches_direct_compute_roster_value(sample_player_pool):
    cfg = LeagueConfig(num_teams=10)
    session = DraftSession(sample_player_pool, cfg, initial_pick=1)

    for name in _top_names(sample_player_pool, 5):
        session.apply_pick(name)

    expected = compute_roster_value(session.rosters[session.our_team_idx], cfg)
    assert session.our_roster_value() == expected
