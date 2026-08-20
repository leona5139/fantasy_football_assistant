import numpy as np

from project.data.loader import load_player_pool
from project.draft.config import DIRECT_POSITIONS, LeagueConfig

# Positional value multiplier by draft-round bucket: early rounds favor RB/WR
# over QB/K/DST, middle rounds start valuing QB more, late rounds flatten out.
ROUND_ADJUSTMENTS = [
    (6, {"QB": 0.7, "RB": 1.2, "WR": 1.1, "TE": 0.9, "K": 0.1, "DST": 0.1}),
    (12, {"QB": 1.3, "RB": 1.0, "WR": 1.0, "TE": 1.1, "K": 0.3, "DST": 0.3}),
    (float("inf"), {"QB": 1.0, "RB": 1.0, "WR": 1.0, "TE": 1.0, "K": 1.0, "DST": 1.0}),
]


def _adjustment_table_for_round(round_num):
    for max_round, adjustments in ROUND_ADJUSTMENTS:
        if round_num <= max_round:
            return adjustments
    return ROUND_ADJUSTMENTS[-1][1]


class GreedyDraftAssistant:
    def __init__(self, full_player_pool, league_config=None):
        self.league_config = league_config or LeagueConfig()
        # Only OUR drafted positions -- feeds the needs/opportunity-cost logic.
        # Opponent picks aren't counted here; positional scarcity is already
        # captured separately via remaining player counts in the pool passed
        # to get_top_candidates/get_opportunity_cost.
        self.roster_filled = {pos: 0 for pos in DIRECT_POSITIONS}
        self.needs = self.league_config.compute_needs()

        self.establish_replacement_baselines(full_player_pool)

    def record_pick(self, position, is_ours):
        if is_ours and position in self.roster_filled:
            self.roster_filled[position] += 1

    def establish_replacement_baselines(self, full_player_pool):
        self.baseline_ranks = {}
        self.baseline_points = {}
        self.baseline_counts = {}

        replacement_levels = self.league_config.replacement_levels()

        for pos in DIRECT_POSITIONS:
            pos_players = full_player_pool.loc[full_player_pool["Position"] == pos]
            pos_players = pos_players.sort_values("Rank")

            replacement_idx = min(replacement_levels[pos] - 1, len(pos_players) - 1)

            self.baseline_ranks[pos] = pos_players.iloc[replacement_idx]["Rank"]
            self.baseline_points[pos] = pos_players.iloc[replacement_idx]["Total_FPTS"]
            self.baseline_counts[pos] = len(pos_players)

    def get_positional_adjustment(self, position, round_num):
        return _adjustment_table_for_round(round_num).get(position, 1.0)

    def get_opportunity_cost(self, player, player_pool):
        pos = player["Position"]
        positions_filled = self.roster_filled[pos]
        positions_needed = self.needs[pos]

        if positions_filled >= positions_needed:
            need_factor = 20
        else:
            remaining_need = positions_needed - positions_filled
            need_factor = max(0.5, 1.0 / remaining_need)

        remaining_players = len(player_pool[player_pool["Position"] == pos])
        total_players = self.baseline_counts[pos]
        scarcity_factor = max(0.5, remaining_players / max(1, total_players))

        quality_factor = max(0.2, player["Rank"] / max(1, self.baseline_ranks[pos]))

        return need_factor * scarcity_factor * quality_factor

    def get_draft_efficiency(self, player, player_pool, round_num):
        vorp = max(0, player["Total_FPTS"] - self.baseline_points[player["Position"]])

        pos_adjustment = self.get_positional_adjustment(player["Position"], round_num)
        adjusted_value = vorp * pos_adjustment

        cost = self.get_opportunity_cost(player, player_pool)

        return adjusted_value / cost

    def get_top_candidates(self, player_pool, round_num, n=5):
        """Vectorized equivalent of scoring every row with get_draft_efficiency
        and taking the top n. Replaces the old iterrows() scan (O(n) full
        pandas passes instead of O(n) Python-level dict lookups per row, and
        a single groupby instead of re-filtering the pool inside the loop).
        """
        pool = player_pool.copy()
        adjustments = _adjustment_table_for_round(round_num)

        baseline_points = pool["Position"].map(self.baseline_points)
        vorp = (pool["Total_FPTS"] - baseline_points).clip(lower=0)
        pos_adjustment = pool["Position"].map(adjustments).fillna(1.0)
        adjusted_value = vorp * pos_adjustment

        filled = pool["Position"].map(self.roster_filled)
        needed = pool["Position"].map(self.needs)
        remaining_need = (needed - filled).clip(lower=1e-9)
        need_factor = np.where(filled >= needed, 20.0, np.maximum(0.5, 1.0 / remaining_need))

        remaining_counts = pool.groupby("Position")["Player"].transform("size")
        total_counts = pool["Position"].map(self.baseline_counts).clip(lower=1)
        scarcity_factor = np.maximum(0.5, remaining_counts / total_counts)

        baseline_ranks = pool["Position"].map(self.baseline_ranks).clip(lower=1)
        quality_factor = np.maximum(0.2, pool["Rank"] / baseline_ranks)

        cost = need_factor * scarcity_factor * quality_factor
        pool["_efficiency"] = adjusted_value / cost

        return pool.nlargest(n, "_efficiency").drop(columns="_efficiency")

    def get_best_player(self, player_pool, round_num):
        return self.get_top_candidates(player_pool, round_num, n=1).iloc[0]

    def _get_best_player_iterrows(self, player_pool, round_num):
        """Reference implementation kept for the vectorization-equivalence
        test. Not used by the draft loop."""
        best_efficiency = -float("inf")
        best_player = player_pool.iloc[0]
        for idx, player in player_pool.iterrows():
            cur_eff = self.get_draft_efficiency(player, player_pool, round_num)
            if cur_eff > best_efficiency:
                best_efficiency = cur_eff
                best_player = player

        return best_player


class DraftEnv:
    def __init__(self, full_player_pool, league_config=None, initial_pick=1):
        self.all_players = full_player_pool
        self.league_config = league_config or LeagueConfig()
        self.num_players = self.league_config.num_teams
        self.draft_style = self.league_config.draft_style
        self.num_rounds = self.league_config.num_rounds
        self.initial_pick = initial_pick
        self.recommender = GreedyDraftAssistant(full_player_pool, self.league_config)

        self.get_pick_positions()

    def get_pick_positions(self):
        self.pick_positions = []
        if self.draft_style == "regular":
            for n in range(0, self.num_rounds):
                self.pick_positions += [n * self.num_players + self.initial_pick]
        elif self.draft_style == "snake":
            for n in range(0, self.num_rounds):
                if n % 2 == 0:
                    self.pick_positions += [n * self.num_players + self.initial_pick]
                else:
                    self.pick_positions += [n * self.num_players + (self.num_players - self.initial_pick) + 1]

    def apply_pick(self, player_name, is_ours):
        """Non-interactive pick application: looks up the player's position
        before removing them from the pool, records it against our roster
        (if it's our pick), and filters them out of available_players.
        """
        row = self.available_players.loc[self.available_players["Player"] == player_name].iloc[0]
        self.recommender.record_pick(row["Position"], is_ours)
        self.available_players = self.available_players[self.available_players["Player"] != player_name]
        return row

    def draft(self):
        self.round_num = 1
        self.available_players = self.all_players
        print(f"------\nSTARTING ROUND {self.round_num}\n------")
        max_picks = self.num_players * self.num_rounds
        for p in range(1, max_picks):
            print(f"\nPick Number {p}\n")
            if p in self.pick_positions:
                while True:
                    print("Greedy Recommendation:", self.recommender.get_best_player(self.available_players, self.round_num))
                    selection = input("\nSelect a player to draft:\n")
                    if selection in self.available_players["Player"].values:
                        self.apply_pick(selection, is_ours=True)
                        print(f"{selection} has been drafted.")
                        break
                    elif selection in self.all_players["Player"].values:
                        print("Player already selected. Please select again.")
                    else:
                        print("Player not found. Please select again.")
            else:
                while True:
                    opponent_selection = input("What did your opponent draft?:\n")
                    if opponent_selection in self.available_players["Player"].values:
                        self.apply_pick(opponent_selection, is_ours=False)
                        print(f"{opponent_selection} has been drafted by your opponent.")
                        break
                    elif opponent_selection in self.all_players["Player"].values:
                        print("Player already selected. Please select again.")
                    else:
                        print("Player not found. Please select again.")

            if p % self.num_players == 0:
                self.round_num += 1
                print(f"------\nSTARTING ROUND {self.round_num}\n------")


def main():
    player_pool = load_player_pool()
    draft = DraftEnv(player_pool, LeagueConfig(), initial_pick=12)
    draft.draft()


if __name__ == "__main__":
    main()
