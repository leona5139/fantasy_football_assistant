import itertools
import pandas as pd
import tqdm
import random

def get_schedule():
    schedule_df = pd.read_csv("./project/playoff_odds_calculator/schedule.csv")
    all_games = {}
    teams = []
    for index, row in schedule_df.iterrows():
        if row["team_a"] not in teams:
            teams.append(row["team_a"])

        if row["week"] not in all_games:
            all_games[row["week"]] = []

        all_games[row["week"]].append((row["team_a"], row["team_b"]))

    return teams, all_games

def get_current_records(teams):
    record = {}
    tie_break = {}
    for t in teams:
        while True:
            wins = input(f"How many wins does {t} have?\n")
            if wins.isdigit():
                record[t] = int(wins)
                break
            else:
                print("Please enter a valid number\n")

        while True:
            tie_break_rank = input("What is their predicted point total ranking?\n")
            if tie_break_rank.isdigit():
                tie_break[t] = -int(tie_break_rank)
                break
            else:
                print("Please enter a valid number\n")
  

    return record, tie_break


def monte_carlo_odds(teams, current_wins, remaining_games, tie_breaker_weight, playoff=6, bye=2, n_sim=10000000):
    """
    Monte Carlo simulation to estimate playoff/seed probabilities.
    
    n_sim: number of random outcomes to simulate
    """
    seed_counts = {t: [0.0] * len(teams) for t in teams}

    for _ in tqdm.tqdm(range(n_sim), desc="Simulating outcomes"):
        wins = current_wins.copy()

        for a, b in remaining_games:
            if random.random() < 0.5:
                wins[a] += 1
            else:
                wins[b] += 1

        ranked = sorted(teams, key=lambda t: (wins[t], tie_breaker_weight[t], t), reverse=True)

        for seed, t in enumerate(ranked, start=1):
            seed_counts[t][seed - 1] += 1

    probs_dict = {t: [count / n_sim for count in counts] for t, counts in seed_counts.items()}

    for t in probs_dict.keys():
        probs_dict[t].append(sum(probs_dict[t][0:playoff])) 
        probs_dict[t].append(sum(probs_dict[t][0:bye]))  

    return probs_dict

if __name__ == "__main__":
    teams, all_games = get_schedule()
    num_teams = len(teams)
    num_weeks = max(all_games.keys())

    while True:          
        week = input("What is current week?\n")
        if week.isdigit():
            cur_week = int(week)
            break
        else:
            print("Please enter a valid number\n")

    cur_records, cur_tie_break = get_current_records(teams)
        
    remaining_games = []
    for week in all_games.keys():
        if int(week) >= int(cur_week):
            for game in all_games[week]:
                remaining_games.append((game))

    probs = monte_carlo_odds(
        teams, cur_records, remaining_games, cur_tie_break
    )

    probs_df = pd.DataFrame(probs).T
    probs_df.columns = ["seed_1", "seed_2", "seed_3", "seed_4",
                        "seed_5", "seed_6", "seed_7", "seed_8",
                        "seed_9", "seed_10", "seed_11", "seed_12",
                        "playoffs", "bye"]

    probs_df.to_csv(f"./project/playoff_odds_calculator/probabilities_{cur_week}.csv")
