import math
import random
import copy
import pandas as pd
import time

class MCTSNode:
    def __init__(self, state, parent=None, action=None):
        self.state = state              # Game state at this node
        self.parent = parent            # Parent node
        self.action = action            # Action that led to this node
        self.children = {}              # Dict of action -> child node
        self.visits = 0                 # Number of times visited
        self.value = 0.0               # Total value accumulated
        self.untried_actions = None     # Actions not yet expanded
        
    def is_fully_expanded(self):
        return len(self.untried_actions) == 0
    
    def is_terminal(self):
        return self.state.is_terminal()
    
    def ucb1_value(self, exploration_constant=1.414):
        """Upper Confidence Bound formula for node selection"""
        if self.visits == 0:
            return float('inf')
        
        exploitation = self.value / self.visits
        exploration = exploration_constant * math.sqrt(math.log(self.parent.visits) / self.visits)
        return exploitation + exploration
    
    def best_child(self, exploration_constant=1.414):
        """Select child with highest UCB1 value"""
        return max(self.children.values(), 
                  key=lambda child: child.ucb1_value(exploration_constant))
    
    def add_child(self, action, state):
        """Add a new child node"""
        child = MCTSNode(state, parent=self, action=action)
        self.children[action] = child
        return child

class GameState:
    def __init__(self, available_players, num_players, draft_style, num_rounds, 
                 initial_pick, current_pick=1, current_round=1, rosters=None, 
                 current_player=0):
        self.available_players = available_players.copy()
        self.num_players = num_players
        self.draft_style = draft_style
        self.num_rounds = num_rounds
        self.initial_pick = initial_pick
        self.current_pick = current_pick
        self.current_round = current_round
        self.current_player = current_player

        if rosters is None:
            self.rosters = {i: [] for i in range(num_players)}
        else:
            self.rosters = copy.deepcopy(rosters)

        self.pick_order = self._calculate_pick_order()

    def _calculate_pick_order(self):
        pick_order = []
        
        for round_num in range(1, self.num_rounds + 1):
            if self.draft_style == "snake" and round_num % 2 == 0:
                for player_id in range(self.num_players - 1, -1, -1):
                    pick_order.append(player_id)
            else:
                for player_id in range(self.num_players):
                    pick_order.append(player_id)

        return pick_order
    
    def get_legal_actions(self):
        if self.is_terminal():
            return []

        available = self.available_players.copy()
        available = available.sort_values('Rank').head(30)

        return available['Player'].to_list()
    
    def make_move(self, action):
        if action not in self.available_players['Player'].values:
            raise ValueError(f"Player {action} not available")
        
        new_rosters = copy.deepcopy(self.rosters)

        new_rosters[self.current_player].append(self.available_players.loc[self.available_players["Player"] == action].iloc[0])

        new_available = self.available_players[self.available_players['Player'] != action].copy()
        

        new_pick = self.current_pick + 1
        new_round = self.current_round

        if new_pick > self.num_players * self.current_round:
            new_round += 1
            
        # Determine next player
        if new_pick <= len(self.pick_order):
            new_current_player = self.pick_order[new_pick - 1]
        else:
            new_current_player = 0  # Draft is over
            
        return GameState(
            new_available, self.num_players, self.draft_style, 
            self.num_rounds, self.initial_pick, new_pick, 
            new_round, new_rosters, new_current_player
        )
    
    def is_terminal(self):
        return self.current_pick > self.num_players * self.num_rounds
    
    def get_reward(self, player):
        roster = self.rosters[player]

        play_score = (
                self.max_player_points([p for p in roster if p["Position"] == "qb"], 1) +
                self.max_player_points([p for p in roster if p["Position"] == "rb"], 2) +
                self.max_player_points([p for p in roster if p["Position"] == "wr"], 2) +
                self.max_player_points([p for p in roster if p["Position"] == "te"], 1) +
                self.max_player_points([p for p in roster if p["Position"] in ["rb", "wr", "te"]], 1) +
                self.max_player_points([p for p in roster if p["Position"] == "dst"], 1) +
                self.max_player_points([p for p in roster if p["Position"] == "k"], 1)
            )
    
        bench_score = (sum(p["Total_FPTS"] for p in roster) - play_score) * 0.3

        return play_score + bench_score
    
    def max_player_points(self, players, count):
        if len(players) == 0:
            return 0
        
        return players['actual_points'].nlargest(count).sum()

    def get_current_player(self):
        return self.current_player

class MCTS:
    def __init__(self, exploration_constant=1.414):
        self.exploration_constant = exploration_constant
    
    def search(self, initial_state, time_limit = 30, iterations=1000):
        """Main MCTS search function"""
        root = MCTSNode(initial_state)
        root.untried_actions = initial_state.get_legal_actions()
        
        start_time = time.time()
        #for _ in range(iterations):
        while time.time() - start_time < time_limit:
            # 1. Selection + Expansion
            node = self._select_and_expand(root)
            
            # 2. Simulation
            reward = self._simulate(node.state, start_time, time_limit)
            
            # 3. Backpropagation
            self._backpropagate(node, reward)
        
        # Return best action
        return self._get_best_action(root)
    
    def _select_and_expand(self, node):
        """Selection and Expansion phases"""
        # Selection: traverse down tree using UCB1
        while not node.is_terminal() and node.is_fully_expanded():
            node = node.best_child(self.exploration_constant)
        
        # Expansion: add one new child if possible
        if not node.is_terminal() and not node.is_fully_expanded():
            action = random.choice(node.untried_actions)
            node.untried_actions.remove(action)
            new_state = node.state.make_move(action)
            node = node.add_child(action, new_state)
            node.untried_actions = new_state.get_legal_actions()
        
        return node
    
    def _simulate(self, state, start_time, time_limit):
        """Simulation phase - random playout"""
        current_state = state
        
        while not current_state.is_terminal():
            if time.time() - start_time > time_limit:
                break
            actions = current_state.get_legal_actions()
            current_player = current_state.get_current_player()

            if current_player == state.get_current_player():
                # This is "us" — allow exploration
                action = random.choice(actions)
            else:
                top_k = min(5, len(actions))
                action = random.choice(actions[:top_k])
        
            current_state = current_state.make_move(action)

        # Return reward for the player who started the search
        return current_state.get_reward(state.get_current_player())
    
    def _backpropagate(self, node, reward):
        """Backpropagation phase"""
        while node is not None:
            node.visits += 1
            node.value += reward
            node = node.parent
    
    def _get_best_action(self, root):
        """Get best action based on visit count (most robust)"""
        if not root.children:
            return None
        
        return max(root.children.keys(), 
                  key=lambda action: root.children[action].visits)

class MCTSDraftAssistant():
    def __init__(self, full_player_pool, num_players, draft_style, num_rounds, 
                 initial_pick, exploration_constant=1.414, time_limit = 30, iterations=1000):
        self.full_player_pool = full_player_pool
        self.num_players = num_players
        self.draft_style = draft_style
        self.num_rounds = num_rounds
        self.initial_pick = initial_pick
        self.iterations = iterations
        self.time_limit = time_limit
        self.mcts = MCTS(exploration_constant)

    def get_best_pick(self, available_players, current_pick, current_round, 
                     rosters, current_player):
        """Use MCTS to find the best pick"""
        # Create current state
        state = GameState(
            available_players, self.num_players, self.draft_style,
            self.num_rounds, self.initial_pick, current_pick,
            current_round, rosters, current_player
        )
        
        best_action = self.mcts.search(state, self.time_limit, self.iterations)
        return best_action
    

class MCTSDraftEnv:
    def __init__(self, full_player_pool, num_players, draft_style, num_rounds, 
                 initial_pick, exploration_constant = 1.414, mcts_time_limit = 30, mcts_iterations=1000):
        self.all_players = full_player_pool
        self.num_players = num_players
        self.draft_style = draft_style
        self.num_rounds = num_rounds
        self.initial_pick = initial_pick
        
        # Initialize MCTS assistant
        self.mcts_assistant = MCTSDraftAssistant(
            full_player_pool, num_players, draft_style, 
            num_rounds, initial_pick, exploration_constant, mcts_time_limit, mcts_iterations
        )
        
        # Track draft state
        self.available_players = full_player_pool.copy()
        self.rosters = {i: [] for i in range(num_players)}
        self.current_pick = 1
        self.current_round = 1
        
        # Calculate our pick positions
        self.our_pick_positions = self._calculate_our_picks()
        
    def _calculate_our_picks(self):
        """Calculate which pick numbers are ours"""
        picks = []
        our_position = self.initial_pick - 1  # Convert to 0-indexed
        
        for round_num in range(self.num_rounds):
            if self.draft_style == "snake" and round_num % 2 == 1:
                # Even rounds (0-indexed) go in reverse for snake
                pick_in_round = self.num_players - our_position - 1
            else:
                pick_in_round = our_position
                
            pick_number = round_num * self.num_players + pick_in_round + 1
            picks.append(pick_number)
            
        return picks
    
    def get_current_player(self):
        """Determine whose turn it is"""
        if self.current_pick > self.num_players * self.num_rounds:
            return -1  # Draft over
            
        round_num = (self.current_pick - 1) // self.num_players
        pick_in_round = (self.current_pick - 1) % self.num_players
        
        if self.draft_style == "snake" and round_num % 2 == 1:
            return self.num_players - pick_in_round - 1
        else:
            return pick_in_round
    
    def make_pick(self, player_name, is_our_pick=False):
        """Record a pick and update state"""
        if player_name not in self.available_players['Player'].values:
            raise ValueError(f"Player {player_name} not available")
        
        # Remove player from available pool
        self.available_players = self.available_players[
            self.available_players['Player'] != player_name
        ]
        
        # Add to appropriate roster
        current_player = self.get_current_player()
        if current_player >= 0:
            self.rosters[current_player].append(self.all_players.loc[self.all_players["Player"] == player_name].iloc[0])
        
        # Advance pick
        self.current_pick += 1
        self.current_round = ((self.current_pick - 1) // self.num_players) + 1
        
        print(f"Pick {self.current_pick - 1}: {player_name} "
              f"({'Our pick' if is_our_pick else 'Opponent pick'})")
    
    def get_mcts_recommendation(self):
        """Get MCTS recommendation for current pick"""
        current_player = self.get_current_player()
        
        recommendation = self.mcts_assistant.get_best_pick(
            self.available_players, self.current_pick, self.current_round,
            self.rosters, current_player
        )
        
        return recommendation
    
    def run_draft(self):
        """Run a draft simulation with MCTS recommendations"""
        print(f"Starting draft simulation...")
        print(f"Draft style: {self.draft_style}")
        print(f"Our pick position: {self.initial_pick}")
        print(f"Our picks will be at: {self.our_pick_positions}")
        print("-" * 50)
        
        while self.current_pick <= self.num_players * self.num_rounds:            
            if self.current_pick in self.our_pick_positions:
                # Our turn - get MCTS recommendation
                recommendation = self.get_mcts_recommendation()
                print(f"\nRound {self.current_round}, Pick {self.current_pick}")
                print(f"MCTS Recommendation: {self.available_players[self.available_players["Player"] == recommendation]}")
                selection = input("\nSelect a player to draft:\n")
                while True:
                    if selection in self.available_players["Player"].values:
                        self.make_pick(selection, is_our_pick=True)

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
                        self.make_pick(opponent_selection, is_our_pick=False)

                        print(f"{opponent_selection} has been drafted by your opponent.")
                        break
                    elif opponent_selection in self.all_players["Player"].values:
                        print("Player already selected. Please select again.")
                    else:
                        print("Player not found. Please select again.")
        
        print("\nDraft Complete!")
        print(f"Our final roster: {self.rosters[self.initial_pick - 1]}")


def main():
    player_pool = pd.read_csv("./project/data/cleaned_data.csv")
    draft = MCTSDraftEnv(full_player_pool=player_pool, 
                         num_players=12, 
                         draft_style="snake", 
                         num_rounds=16, 
                         initial_pick=12, 
                         exploration_constant = 2, 
                         mcts_time_limit= 30)
    draft.run_draft()

if __name__ == "__main__":
    main()