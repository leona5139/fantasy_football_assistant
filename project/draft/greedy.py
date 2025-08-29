import pandas as pd

class GreedyDraftAssistant():
    def __init__(self, full_player_pool):
        self.roster = {"QB":0,
                       "RB":0,
                       "WR":0,
                       "TE":0,
                       "K":0,
                       "DST":0}  
        self.needs =  {"QB":2,
                       "RB":4,
                       "WR":4,
                       "TE":2,
                       "K":1,
                       "DST":1} 

        self.establish_replacement_baselines(full_player_pool)  

    def establish_replacement_baselines(self, full_player_pool):
        self.baseline_ranks = {}
        self.baseline_points = {}
        self.baseline_counts = {}
        
        replacement_levels = {
            "QB": 18,   # ~1.5 QBs per team
            "RB": 36,   # ~3 RBs per team  
            "WR": 48,   # ~4 WRs per team
            "TE": 18,   # ~1.5 TEs per team
            "K": 15,    # ~1.25 Ks per team
            "DST": 15   # ~1.25 DSTs per team
        }
        
        for pos in ["QB", "WR", "RB", "TE", "K", "DST"]:
            pos_players = full_player_pool.loc[full_player_pool["Position"] == pos]
            pos_players = pos_players.sort_values("Rank")

            replacement_idx = min(replacement_levels[pos] - 1, len(pos_players) - 1)

            self.baseline_ranks[pos] = pos_players.iloc[replacement_idx]["Rank"]
            self.baseline_points[pos] = pos_players.iloc[replacement_idx]["Total_FPTS"]
            self.baseline_counts[pos] = len(pos_players)

    def get_draft_efficiency(self, player, player_pool, round_num):
        vorp = max(0, player["Total_FPTS"] - self.baseline_points[player["Position"]])
        
        pos_adjustment = self.get_positional_adjustment(player["Position"], round_num)
        adjusted_value = vorp * pos_adjustment
        
        cost = self.get_opportunity_cost(player, player_pool)
        
        return adjusted_value / cost

    def get_positional_adjustment(self, position, round_num):
        
        if round_num <= 6:
            adjustments = {
                "QB": 0.7, 
                "RB": 1.2, 
                "WR": 1.1,   
                "TE": 0.9, 
                "K": 0.1,    
                "DST": 0.1   
            }
        
        elif round_num <= 12:
            adjustments = {
                "QB": 1.3,
                "RB": 1.0,  
                "WR": 1.0, 
                "TE": 1.1,  
                "K": 0.3,   
                "DST": 0.3 
            }
        
        else:
            adjustments = {
                "QB": 1.0, 
                "RB": 1.0, 
                "WR": 1.0, 
                "TE": 1.0, 
                "K": 1.0,    
                "DST": 1.0   
            }
        
        return adjustments.get(position, 1.0)

    def get_opportunity_cost(self, player, player_pool):
        pos = player["Position"]
        positions_filled = self.roster[pos]
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

    def get_best_player(self, player_pool, round_num):
        best_efficiency = -float("inf")
        best_player = player_pool.iloc[0]
        for idx, player in player_pool.iterrows():
            cur_eff = self.get_draft_efficiency(player, player_pool, round_num)
            if cur_eff > best_efficiency:
                best_efficiency = cur_eff
                best_player = player

        return best_player
    
class DraftEnv():
    def __init__(self, full_player_pool, num_players, draft_style, num_rounds, initial_pick):
        self.all_players = full_player_pool
        self.num_players = num_players
        self.draft_style = draft_style
        self.num_rounds = num_rounds
        self.initial_pick = initial_pick
        self.recommender = GreedyDraftAssistant(full_player_pool)

        self.get_pick_positions()

    def get_pick_positions(self):
        self.pick_positions = []
        if self.draft_style == "regular":
            for n in range(0,self.num_rounds):
                self.pick_positions += [n*self.num_players + self.initial_pick]
        elif self.draft_style == "snake":
            for n in range(0,self.num_rounds):
                if n%2 == 0:
                    self.pick_positions += [n*self.num_players + self.initial_pick]
                else:
                    self.pick_positions += [n*self.num_players + (self.num_players - self.initial_pick) + 1]

    def draft(self):
        self.round_num = 1
        self.available_players = self.all_players
        print(f"------\nSTARTING ROUND {self.round_num}\n------")
        max_picks = self.num_players*self.num_rounds
        for p in range(1,max_picks):
            print(f"\nPick Number {p}\n")
            if p in self.pick_positions:
                while True:
                    print("Greedy Recommendation:", self.recommender.get_best_player(self.available_players, self.round_num))
                    selection = input("\nSelect a player to draft:\n")
                    if selection in self.available_players["Player"].values:
                        self.available_players = self.available_players[self.available_players['Player'] != selection]

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
                        self.available_players = self.available_players[self.available_players['Player'] != opponent_selection]

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
    player_pool = pd.read_csv("./project/data/cleaned_data.csv")
    draft = DraftEnv(player_pool, 12, "snake", 16, 12)
    draft.draft()

if __name__ == "__main__":
    main()