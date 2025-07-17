import nfl_data_py as nfl
import pandas as pd
import numpy as np

def import_player_data():
    player_list = pd.read_csv("./project/data/cleaned_data.csv")
    player_df = player_list[["Player", "Team", "Position"]]

    player_df = player_df[player_df["Team"] != "FA"]

    return player_df

# sit/play features
def get_vegas_odds(df, year, week):
    odds = nfl.import_schedules([year])
    odds = odds.loc[odds["week"] == week]
    odds = odds[["home_team",
                "away_team",
                "total_line", 
                "spread_line"]]
    
    team_features = []
    for idx, row in odds.iterrows():
        d_home = {}
        d_home["team"] = row["home_team"]

        d_away = {}
        d_away["team"] = row["away_team"]

        t = row["total_line"]
        s = row["spread_line"]

        if s < -6:
            d_home["favored"] = 1
            d_away["favored"] = -1
        elif s > 6:
            d_home["favored"] = -1
            d_away["favored"] = 1
        else:
            d_home["favored"] = 0
            d_away["favored"] = 0

        if t >= 49:
            d_home["pace"] = 1
            d_away["pace"] = 1
        elif t <= 42:
            d_home["pace"] = -1
            d_away["pace"] = -1
        else:
            d_home["pace"] = 0
            d_away["pace"] = 0

        team_features.append(d_home)
        team_features.append(d_away)
    team_odds = pd.DataFrame(team_features)
    team_odds.loc[team_odds["team"] == "LA", "team"] = "LAR"
    team_odds.loc[team_odds["team"] == "WAS", "team"] = "WSH"

    df["favored_flag"] = 0
    df["pace_flag"] = 0
    for idx, player in df.iterrows():
        team_row = team_odds.loc[team_odds["team"] == player["Team"]].iloc[0]

        favored_flag = team_row["favored"]

        if team_row["pace"] == 0:
            pace_flag = 0
        elif team_row["pace"] == 1:
            if player["Position"] == "DST":
                pace_flag = -1
            else:
                pace_flag = 1
        else:
            if player["Position"] == "DST":
                pace_flag = 1
            else:
                pace_flag = -1

        df.at[idx, "favored_flag"] = favored_flag
        df.at[idx, "pace_flag"] = pace_flag

    return df

def get_trends(df, year, week):
    df['fpts_trend_flag'] = 0
    df['consistency_flag'] = 0

    weeks_back = min(week - 1, 6)
    if weeks_back <= 1:
        return df
    
    window = list(range(week-weeks_back, week))

    weekly_data = nfl.import_weekly_data([year])
    weekly_data = weekly_data.loc[weekly_data["week"].isin(window)]

    for idx, player in df.iterrows():
        player_weekly = weekly_data.loc[weekly_data["player_display_name"] == player["Player"]]

        points = list(player_weekly["fantasy_points"])

        if len(points) < 2:
            continue

        pos = 0
        neg = 0
        for i in range(len(points) - 1):
            if points[i+1] > points[i]:
                pos += 1
            elif points[i+1] < points[i]:
                neg += 1

        if pos == len(points) - 1:
            df.at[idx, "fpts_trend_flag"] = 1
        elif neg == len(points) - 1:
            df.at[idx, "fpts_trend_flag"] = -1
        else: 
            df.at[idx, "fpts_trend_flag"] = 0

        cv = np.std(points) / np.mean(points)

        if cv < 0.25:
            df.at[idx, "consistency_flag"] = 1
        elif cv < 0.5:
            df.at[idx, "consistency_flag"] = 0
        else:
            df.at[idx, "consistency_flag"] = -1

    return df

# add/drop features
def get_upcoming_difficulty(df, year, week):
    schedules = nfl.import_schedules([year])

    upcoming = list(range(week+1, min(week+4, 19)))
    schedules = schedules.loc[schedules["week"].isin(upcoming)]

    team_favored_count = {}
    for idx, game in schedules.iterrows():
        home_team = game["home_team"]
        if home_team == "LA":
            home_team = "LAR"
        if home_team == "WAS":
            home_team = "WSH"

        away_team = game["away_team"]
        if away_team == "LA":
            away_team = "LAR"
        if away_team == "WAS":
            away_team = "WSH"

        if home_team not in team_favored_count:
            team_favored_count[home_team] = 0

        if away_team not in team_favored_count:
            team_favored_count[away_team] = 0

        if game["spread_line"] <= 0:
            team_favored_count[home_team] += 1

        else:
            team_favored_count[away_team] += 1

    team_favored_flags = {}
    for team in team_favored_count:
        if team_favored_count[team]/len(upcoming) > 0.6:
            team_favored_flags[team] = 1
        else:
            team_favored_flags[team] = 0

    df["upcoming_favored_flag"] = 0
    for idx, player in df.iterrows():
        player_team = player["Team"]
        if player_team == "FA":
            continue
        flag = team_favored_flags[player_team]

        df.at[idx, "upcoming_favored_flag"] = flag

    return df

def get_playoff_difficulty(df, year):
    schedules = nfl.import_schedules([year])

    playoff_weeks = [15,16,17,18]
    schedules = schedules.loc[schedules["week"].isin(playoff_weeks)]

    team_favored_count = {}
    for idx, game in schedules.iterrows():
        home_team = game["home_team"]
        if home_team == "LA":
            home_team = "LAR"
        if home_team == "WAS":
            home_team = "WSH"

        away_team = game["away_team"]
        if away_team == "LA":
            away_team = "LAR"
        if away_team == "WAS":
            away_team = "WSH"

        if home_team not in team_favored_count:
            team_favored_count[home_team] = 0

        if away_team not in team_favored_count:
            team_favored_count[away_team] = 0

        if game["spread_line"] <= 0:
            team_favored_count[home_team] += 1

        else:
            team_favored_count[away_team] += 1

    team_favored_flags = {}
    for team in team_favored_count:
        if team_favored_count[team]/len(playoff_weeks) > 0.5:
            team_favored_flags[team] = 1
        else:
            team_favored_flags[team] = 0

    df["playoff_favored_flag"] = 0
    for idx, player in df.iterrows():
        player_team = player["Team"]
        if player_team == "FA":
            continue
        flag = team_favored_flags[player_team]

        df.at[idx, "playoff_favored_flag"] = flag

    return df

def generate_data(year, week):
    df = import_player_data()
    df = get_vegas_odds(df, year, week)
    try:
        df = get_trends(df, year, week)
    except:
        df['fpts_trend_flag'] = 0
        df['consistency_flag'] = 0
    df = get_upcoming_difficulty(df, year, week)
    df = get_playoff_difficulty(df, year)
    
    return df

if __name__ == "__main__":
    print(generate_data(2025, 1))