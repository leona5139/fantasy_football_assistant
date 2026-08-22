import pytest
from fastapi.testclient import TestClient

from project.draft.config import LeagueConfig
from project.draft.greedy import GreedyDraftAssistant
from project.webapp import session as session_module
from project.webapp.server import app
from project.webapp.session import DraftSession

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_session():
    session_module._session = None
    yield
    session_module._session = None


@pytest.fixture(autouse=True)
def _no_network_player_pool(sample_player_pool, monkeypatch):
    """Every /api/session call in these tests must use the deterministic
    fixture pool instead of hitting the live Sleeper API."""

    def fake_loader(source="auto", scoring="ppr"):
        return sample_player_pool.copy()

    monkeypatch.setattr(session_module, "load_player_pool", fake_loader)
    yield


def _create_session(**overrides):
    body = {"num_teams": 10, "scoring": "ppr", "draft_style": "snake", "initial_pick": 1}
    body.update(overrides)
    return client.post("/api/session", json=body)


def test_health_works_with_no_session_created():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_session_echoes_defaults():
    resp = _create_session()
    assert resp.status_code == 200
    body = resp.json()
    assert body["league_config"]["num_teams"] == 10
    assert body["league_config"]["scoring"] == "ppr"
    assert body["current_pick"] == 1
    assert body["is_our_pick"] is True


def test_create_session_rejects_bad_initial_pick():
    resp = _create_session(initial_pick=99)
    assert resp.status_code == 400


def test_players_endpoint_returns_full_pool_before_any_pick(sample_player_pool):
    _create_session()
    resp = client.get("/api/players")
    assert resp.status_code == 200
    assert len(resp.json()) == len(sample_player_pool)


def test_recommend_greedy_matches_direct_assistant_call(sample_player_pool):
    _create_session()
    session = session_module.get_session()

    resp = client.get("/api/recommend/greedy?n=3")
    assert resp.status_code == 200
    body = resp.json()

    direct = GreedyDraftAssistant(sample_player_pool, session.league_config).get_top_candidates(
        session.available_players, session.current_round, n=3
    )
    assert [c["Player"] for c in body["candidates"]] == direct["Player"].tolist()


def test_pick_state_undo_round_trip(sample_player_pool):
    _create_session()
    top_player = sample_player_pool.sort_values("Rank").iloc[0]["Player"]

    pick_resp = client.post("/api/pick", json={"player": top_player})
    assert pick_resp.status_code == 200
    assert pick_resp.json()["applied"]["player"]["Player"] == top_player
    assert pick_resp.json()["next"]["current_pick"] == 2

    state_resp = client.get("/api/state")
    assert state_resp.json()["current_pick"] == 2
    assert state_resp.json()["pick_history"][0]["player"]["Player"] == top_player

    undo_resp = client.post("/api/undo")
    assert undo_resp.status_code == 200
    assert undo_resp.json()["current_pick"] == 1
    assert undo_resp.json()["pick_history"] == []


def test_pick_unknown_player_returns_400():
    _create_session()
    resp = client.post("/api/pick", json={"player": "Not A Real Player"})
    assert resp.status_code == 400


@pytest.mark.slow
def test_recommend_mcts_returns_available_player(sample_player_pool):
    # Tiny config + 1s time_limit, same pattern as test_mcts_parallel.py's
    # _tiny_league_config -- exercises the real sync-route-under-threadpool
    # dispatch (ProcessPoolExecutor spawn) rather than mocking it out.
    cfg = LeagueConfig(
        num_teams=2,
        roster_slots={"QB": 1, "RB": 1, "WR": 1, "K": 1, "DST": 1},
        flex_eligible=(),
        bench_slots=1,
    )
    session_module._session = DraftSession(sample_player_pool, cfg, initial_pick=1, mcts_time_limit=1)

    resp = client.post("/api/recommend/mcts")
    assert resp.status_code == 200
    body = resp.json()
    assert body["player"]["Player"] in sample_player_pool["Player"].values
    assert body["time_limit_used"] == 1
