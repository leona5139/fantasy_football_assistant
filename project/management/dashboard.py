from data_generation import generate_data
from dashboard_utils import render

import streamlit as st
import math

week = st.number_input("Select Week:", min_value = 1, max_value = 18, step = 1)

st.title("Roster Details Inputs")
your_roster_input = st.text_area("Paste your current team (one player per line):", height=150)
roster_col1, roster_col2 = st.columns(2)
with roster_col1:
    opponent_roster_text = st.text_area("Paste all opponent teams (one player per line):", height = 165)
with roster_col2:
    opponent_roster_file = st.file_uploader("Upload roster file (.txt)", type=["txt"])

if opponent_roster_file is not None:
    opponent_roster_input = opponent_roster_file.read().decode("utf-8")
else:
    opponent_roster_input = opponent_roster_text

@st.cache_data
def load_data(week):
    return generate_data(2025, week)

df = load_data(week)

if your_roster_input:
    your_roster_list = [name.strip() for name in your_roster_input.split("\n") if name.strip()]

    team_df = df[df["Player"].isin(your_roster_list)]
    team_df = team_df[["Player", "Position", "Team", "favored_flag", "pace_flag", "consistency_flag"]]

    st.title(f"Your Team - Week {int(week)}")

    team_df = team_df.rename(columns = {
        "favored_flag": "favored",
        "pace_flag": "pace",
        "consistency_flag": "consistent"
    })
    render(team_df)
else:
    pass

if df is not None:
    st.title(f"Waiver - Week {int(week)}")
    waiver_df = df
    if your_roster_input:
        waiver_df = waiver_df[~waiver_df["Player"].isin(your_roster_list)]
    if opponent_roster_input:
        opponent_roster_list = [name.strip() for name in opponent_roster_input.split("\n") if name.strip()]
        waiver_df = waiver_df[~waiver_df["Player"].isin(opponent_roster_list)]

    positions = st.multiselect(
        "Filter by Position",
        options=waiver_df["Position"].unique(),
        default=waiver_df["Position"].unique()
    )

    avoid_neutral = st.checkbox("Don't show players without tags")

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        st.text("Short term considerations")
        favored_only = st.checkbox("Show only players who are favored in their next game")
        pace_only = st.checkbox("Show only players who have a fast pace in their next game")
        points_trending_up_only = st.checkbox("Show only players with points trending up")

    with filter_col2:
        st.text("Long term considerations")
        consistency_only = st.checkbox("Show only players who are consistent")
        upcoming_favored_only = st.checkbox("Show only players who are favored in their next few games")
        playoff_favored_only = st.checkbox("Show only players who are favored in their playoff games")

    filtered_data = waiver_df[waiver_df["Position"].isin(positions)]

    if favored_only:
        filtered_data = filtered_data[filtered_data["favored_flag"] == 1]
    if pace_only:
        filtered_data = filtered_data[filtered_data["pace_flag"] == 1]
    if points_trending_up_only:
        filtered_data = filtered_data[filtered_data["fpts_trend_flag"] == 1]
    if consistency_only:
        filtered_data = filtered_data[filtered_data["consistency_flag"] == 1]
    if upcoming_favored_only:
        filtered_data = filtered_data[filtered_data["upcoming_favored_flag"] == 1]
    if playoff_favored_only:
        filtered_data = filtered_data[filtered_data["playoff_favored_flag"] == 1]

    filtered_data = filtered_data.rename(columns = {
        "favored_flag": "favored",
        "pace_flag": "pace",
        "consistency_flag": "consistent",
        "upcoming_favored_flag": "strong upcoming schedule",
        "playoff_favored_flag": "strong playoff schedule"
    })

    render(df, avoid_neutral)

else:
    st.warning(f"Waiver - Week {int(week)}")