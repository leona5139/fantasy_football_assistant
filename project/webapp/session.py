"""Single unified draft-session state model for the webapp.

DraftEnv (greedy.py) and MCTSDraftEnv (mcts.py) are separate,
non-interoperable stateful wrappers -- one only knows about greedy
recommendations, the other only about MCTS. DraftSession is the one new
object the webapp needs: it owns the single source of truth (available
players, rosters, pick history) and drives a GreedyDraftAssistant
incrementally plus calls MCTSDraftAssistant statelessly, from that shared
state, instead of trying to reconcile two disjoint state models.
"""

from project.data.loader import load_player_pool
from project.draft.config import LeagueConfig
from project.draft.greedy import GreedyDraftAssistant
from project.draft.mcts import MCTSDraftAssistant
from project.draft.pick_order import round_for_pick, team_for_pick
from project.draft.scoring import compute_roster_value


class DraftSession:
    def __init__(self, full_player_pool, league_config=None, initial_pick=1, mcts_time_limit=12):
        self.league_config = league_config or LeagueConfig()
        self.initial_pick = initial_pick
        self.full_player_pool = full_player_pool

        self.available_players = full_player_pool.copy()
        self.rosters = {i: [] for i in range(self.league_config.num_teams)}
        self.pick_history = []  # list[dict]: pick_number, round_num, team_idx, is_ours, player (dict)

        self.greedy = GreedyDraftAssistant(full_player_pool, self.league_config)
        self.mcts = MCTSDraftAssistant(
            full_player_pool, self.league_config, initial_pick, time_limit=mcts_time_limit, parallel=True
        )

    @property
    def our_team_idx(self):
        return self.initial_pick - 1

    @property
    def current_pick(self):
        return len(self.pick_history) + 1

    @property
    def current_round(self):
        return round_for_pick(self.current_pick, self.league_config.num_teams)

    @property
    def current_team(self):
        return team_for_pick(self.current_pick, self.league_config.num_teams, self.league_config.draft_style)

    @property
    def is_our_pick(self):
        return self.current_team == self.our_team_idx

    @property
    def draft_complete(self):
        return self.current_pick > self.league_config.num_teams * self.league_config.num_rounds

    def _row_for(self, player_name):
        matches = self.available_players.loc[self.available_players["Player"] == player_name]
        if matches.empty:
            if player_name in self.full_player_pool["Player"].values:
                raise ValueError(f"{player_name} has already been drafted.")
            raise ValueError(f"Unknown player: {player_name}")
        return matches.iloc[0]

    def apply_pick(self, player_name):
        if self.draft_complete:
            raise ValueError("Draft is already complete.")

        row = self._row_for(player_name)
        is_ours = self.is_our_pick
        team_idx = self.current_team
        pick_number = self.current_pick
        round_num = self.current_round

        self.greedy.record_pick(row["Position"], is_ours)
        self.available_players = self.available_players[self.available_players["Player"] != player_name]
        self.rosters[team_idx].append(row)
        self.pick_history.append(
            {
                "pick_number": pick_number,
                "round_num": round_num,
                "team_idx": team_idx,
                "is_ours": is_ours,
                "player": row.to_dict(),
            }
        )
        return {"row": row, "is_ours": is_ours, "team_idx": team_idx, "pick_number": pick_number}

    def undo(self):
        """Pop the last pick and rebuild all state from scratch by replaying
        the rest of history. At most ~200 picks, only run on a button click --
        keeps one deterministic source of truth instead of a fragile
        decrement-based undo that could drift from apply_pick's logic.
        """
        if not self.pick_history:
            return
        self.pick_history.pop()

        self.available_players = self.full_player_pool.copy()
        self.rosters = {i: [] for i in range(self.league_config.num_teams)}
        self.greedy = GreedyDraftAssistant(self.full_player_pool, self.league_config)

        replay = self.pick_history
        self.pick_history = []
        for entry in replay:
            self.apply_pick(entry["player"]["Player"])

    def our_roster_value(self):
        return compute_roster_value(self.rosters[self.our_team_idx], self.league_config)

    def positional_scarcity(self):
        counts = self.available_players["Position"].value_counts().to_dict()
        return {
            pos: {"remaining": counts.get(pos, 0), "total": total}
            for pos, total in self.greedy.baseline_counts.items()
        }

    def state(self):
        return {
            "current_pick": self.current_pick,
            "current_round": self.current_round,
            "current_team": self.current_team,
            "is_our_pick": self.is_our_pick,
            "our_team_idx": self.our_team_idx,
            "draft_complete": self.draft_complete,
            "pick_history": self.pick_history,
            "our_roster": [row.to_dict() for row in self.rosters[self.our_team_idx]],
            "our_roster_value": self.our_roster_value(),
            "positional_scarcity": self.positional_scarcity(),
            "league_config": {
                "num_teams": self.league_config.num_teams,
                "scoring": self.league_config.scoring,
                "draft_style": self.league_config.draft_style,
                "roster_slots": self.league_config.roster_slots,
                "bench_slots": self.league_config.bench_slots,
                "num_rounds": self.league_config.num_rounds,
            },
            "initial_pick": self.initial_pick,
        }


_session = None


def create_session(
    num_teams=10,
    scoring="ppr",
    draft_style="snake",
    initial_pick=1,
    roster_slots=None,
    bench_slots=7,
    source="auto",
    _player_pool_loader=None,
):
    """Builds a fresh LeagueConfig + player pool + DraftSession and installs
    it as the process-wide active session. Single-user, single-machine, one
    draft at a time -- no session-id/multi-tenancy needed.

    _player_pool_loader is overridable purely for tests, to avoid any network
    call to the live Sleeper API. Resolved from the module global (not a
    default-argument value) so tests can monkeypatch `load_player_pool` on
    this module and have it take effect here.
    """
    global _session
    kwargs = {"num_teams": num_teams, "scoring": scoring, "draft_style": draft_style, "bench_slots": bench_slots}
    if roster_slots is not None:
        kwargs["roster_slots"] = roster_slots
    league_config = LeagueConfig(**kwargs)

    loader = _player_pool_loader or load_player_pool
    full_player_pool = loader(source=source, scoring=scoring)
    _session = DraftSession(full_player_pool, league_config, initial_pick=initial_pick)
    return _session


def get_session():
    if _session is None:
        raise RuntimeError("No draft session has been created yet.")
    return _session
