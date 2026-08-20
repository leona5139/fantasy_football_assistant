"""Shared league configuration for the draft engines.

Built once per draft session and passed into both GreedyDraftAssistant and
the MCTS engine, so team count / scoring / roster construction live in one
place instead of being hardcoded separately in each file. This is also the
exact shape the future webapp setup screen (milestone 0.3) will construct
and hand to either engine.
"""

from dataclasses import dataclass, field

DEFAULT_ROSTER_SLOTS = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "K": 1, "DST": 1}
DEFAULT_FLEX_ELIGIBLE = ("RB", "WR", "TE")
DEFAULT_BENCH_MULTIPLIER = {"QB": 1.5, "RB": 1.5, "WR": 1.5, "TE": 1.5, "K": 1.1, "DST": 1.1}
DIRECT_POSITIONS = ("QB", "RB", "WR", "TE", "K", "DST")


@dataclass
class LeagueConfig:
    num_teams: int = 10
    scoring: str = "ppr"
    draft_style: str = "snake"
    roster_slots: dict = field(default_factory=lambda: dict(DEFAULT_ROSTER_SLOTS))
    flex_eligible: tuple = DEFAULT_FLEX_ELIGIBLE
    bench_slots: int = 7
    # How much bench-relevant demand exists beyond pure starters, per position.
    # E.g. QB's 1.5 mirrors the "~1.5 startable QBs per team" rule of thumb;
    # K/DST get a much smaller bench allocation since teams rarely stream them.
    bench_multiplier: dict = field(default_factory=lambda: dict(DEFAULT_BENCH_MULTIPLIER))

    @property
    def num_rounds(self):
        return self.total_roster_size()

    def total_roster_size(self):
        return sum(self.roster_slots.values()) + self.bench_slots

    def _starters_per_team(self):
        """Starter slots per position, with FLEX split evenly across flex_eligible."""
        flex_share = self.roster_slots.get("FLEX", 0) / len(self.flex_eligible) if self.flex_eligible else 0
        starters = {}
        for pos in DIRECT_POSITIONS:
            starters[pos] = self.roster_slots.get(pos, 0)
            if pos in self.flex_eligible:
                starters[pos] += flex_share
        return starters

    def compute_needs(self):
        """Per-team target draft count by position (starters + a proportional
        share of bench slots). Replaces greedy.py's old hardcoded self.needs.
        """
        starters = self._starters_per_team()
        weights = {pos: starters[pos] * self.bench_multiplier.get(pos, 1.0) for pos in DIRECT_POSITIONS}
        total_weight = sum(weights.values())

        needs = {}
        for pos in DIRECT_POSITIONS:
            bench_share = (self.bench_slots * weights[pos] / total_weight) if total_weight else 0
            needs[pos] = round(starters[pos] + bench_share, 2)
        return needs

    def replacement_levels(self):
        """League-wide 'startable' player count by position -- used to find
        the replacement-level baseline player. Replaces greedy.py's old
        hardcoded replacement_levels dict, now scaling with num_teams and
        roster_slots instead of assuming a fixed 12-team league.
        """
        starters = self._starters_per_team()
        return {
            pos: max(1, round(self.num_teams * starters[pos] * self.bench_multiplier.get(pos, 1.0)))
            for pos in DIRECT_POSITIONS
        }
