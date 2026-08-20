"""Thin, path-safe wrapper for loading the player pool.

Replaces the CWD-relative `pd.read_csv("./project/data/cleaned_data.csv")`
calls duplicated in greedy.py's and mcts.py's main() -- those only worked if
the process happened to be launched from the repo root.
"""

from project.data.live_rankings import build_live_rankings


def load_player_pool(source="auto", season=2026, scoring="ppr"):
    return build_live_rankings(season=season, scoring=scoring, source=source)
