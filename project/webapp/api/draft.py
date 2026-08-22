from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from project.draft.config import DEFAULT_ROSTER_SLOTS
from project.webapp import session as session_module

router = APIRouter(prefix="/api")


class SessionCreateRequest(BaseModel):
    num_teams: int = 10
    scoring: str = "ppr"
    draft_style: str = "snake"
    initial_pick: int
    roster_slots: Optional[dict] = None
    bench_slots: int = 7
    source: str = "auto"


class PickRequest(BaseModel):
    player: str


def _player_rows(df):
    cols = ["Rank", "Player", "Team", "Position", "Total_FPTS", "Average_FPTS"]
    return df[cols].to_dict(orient="records")


@router.post("/session")
def create_session(req: SessionCreateRequest):
    if req.initial_pick < 1 or req.initial_pick > req.num_teams:
        raise HTTPException(status_code=400, detail="initial_pick must be between 1 and num_teams.")

    session = session_module.create_session(
        num_teams=req.num_teams,
        scoring=req.scoring,
        draft_style=req.draft_style,
        initial_pick=req.initial_pick,
        roster_slots=req.roster_slots,
        bench_slots=req.bench_slots,
        source=req.source,
    )
    return session.state()


@router.get("/players")
def get_players():
    session = session_module.get_session()
    return _player_rows(session.available_players)


@router.get("/state")
def get_state():
    return session_module.get_session().state()


@router.get("/recommend/greedy")
def recommend_greedy(n: int = 5):
    session = session_module.get_session()
    candidates = session.greedy.get_top_candidates(
        session.available_players, session.current_round, n=n, explain=True
    )
    return {
        "round_num": session.current_round,
        "candidates": candidates.to_dict(orient="records"),
    }


@router.post("/pick")
def apply_pick(req: PickRequest):
    session = session_module.get_session()
    try:
        result = session.apply_pick(req.player)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "applied": {
            "player": result["row"].to_dict(),
            "is_ours": result["is_ours"],
            "team_idx": result["team_idx"],
            "pick_number": result["pick_number"],
        },
        "next": session.state(),
    }


@router.post("/undo")
def undo_pick():
    session = session_module.get_session()
    session.undo()
    return session.state()


@router.post("/recommend/mcts")
def recommend_mcts():
    """Sync (not async) route: get_best_pick blocks for the full
    time_limit (10-15s) and spawns a ProcessPoolExecutor. A sync def lets
    Starlette dispatch this to its threadpool so /health and other requests
    aren't blocked for the duration.
    """
    session = session_module.get_session()
    player_name = session.mcts.get_best_pick(
        session.available_players,
        session.current_pick,
        session.current_round,
        session.rosters,
        session.current_team,
    )
    if player_name is None:
        raise HTTPException(status_code=503, detail="MCTS search returned no recommendation.")

    row = session.available_players.loc[session.available_players["Player"] == player_name].iloc[0]
    return {"player": row.to_dict(), "time_limit_used": session.mcts.time_limit}


@router.get("/config/defaults")
def config_defaults():
    return {"roster_slots": DEFAULT_ROSTER_SLOTS, "bench_slots": 7, "num_teams": 10, "scoring": "ppr"}
