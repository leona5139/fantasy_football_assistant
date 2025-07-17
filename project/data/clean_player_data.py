import pandas as pd

# Load Excel
df = pd.read_csv('./project/data/scraped_data.csv')

# List of known NFL team codes
team_codes = [
    'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 'DAL', 'DEN',
    'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC', 'LAC', 'LAR', 'LV', 'MIA',
    'MIN', 'NE', 'NO', 'NYG', 'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WAS'
]

# List of position codes
position_codes = ['QB', 'RB', 'WR', 'TE', 'K', 'DST', 'DEF']
team_codes = [
    'ARI', 'ATL', 'BAL', 'BUF', 'CAR', 'CHI', 'CIN', 'CLE', 'DAL', 'DEN',
    'DET', 'GB', 'HOU', 'IND', 'JAX', 'KC', 'LAC', 'LAR', 'LV', 'MIA',
    'MIN', 'NE', 'NO', 'NYG', 'NYJ', 'PHI', 'PIT', 'SEA', 'SF', 'TB', 'TEN', 'WSH', 'FA'
]
position_codes = ['QB', 'RB', 'WR', 'TE', 'K', 'DST', 'DEF']

# Lowercase versions for matching
team_codes_lower = [team.lower() for team in team_codes]
position_codes_lower = [pos.lower() for pos in position_codes]

def split_merged_field(s):
    if not isinstance(s, str):
        return pd.Series([None, None, None])
    
    s_lower = s.lower()
    
    for pos_lc, pos_orig in zip(position_codes_lower, position_codes):
        if s_lower.endswith(pos_lc):
            s_wo_pos = s[:-len(pos_lc)]
            s_wo_pos_lower = s_lower[:-len(pos_lc)]

            for team_lc, team_orig in zip(team_codes_lower, team_codes):
                if s_wo_pos_lower.endswith(team_lc):
                    player = s_wo_pos[:-len(team_lc)]
                    return pd.Series([player.strip(), team_orig, pos_orig])
    
    return pd.Series([None, None, None]) 

df[['Player', 'Team', 'Position']] = df['Players'].apply(split_merged_field)
df = df.drop(columns=["Players"])
df.to_csv('./project/data/cleaned_data.csv', index=False)