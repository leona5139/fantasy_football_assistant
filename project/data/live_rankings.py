"""Live 2026 player rankings, pulled from the Sleeper API.

Produces a DataFrame in the same shape as the historical `cleaned_data.csv`
(`Rank, Total_FPTS, Average_FPTS, Player, Team, Position`) so `greedy.py`/
`mcts.py` don't need to change their data contract.

Source order: Sleeper's projections endpoint (free, no auth) is the primary
source -- confirmed to expose real preseason consensus (rotowire) projections
and ADP for the upcoming season. nfl_data_py was considered per the top-level
improvement plan but its public API (import_schedules, import_weekly_data,
import_seasonal_data, import_draft_picks, import_ids, etc.) has no
projections/ADP endpoint, only historical actuals -- so it isn't a candidate
here. If Sleeper is unreachable or returns bad data, this falls back to the
static `cleaned_data.csv` snapshot as a last resort.
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Inside a PyInstaller frozen bundle, __file__ resolves into the temp
# extraction dir (sys._MEIPASS), not the original repo -- packaging/app.spec
# bundles cleaned_data.csv at "project/data/cleaned_data.csv" relative to
# that dir, matching the source-tree layout so this branch is the only
# difference.
if getattr(sys, "frozen", False):
    REPO_ROOT = Path(sys._MEIPASS)
else:
    REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATIC_CSV = REPO_ROOT / "project" / "data" / "cleaned_data.csv"
DEFAULT_CACHE_CSV = REPO_ROOT / "project" / "data" / "live_rankings_cache.csv"

SLEEPER_BASE = "https://api.sleeper.app"
SLEEPER_POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")
POSITION_REMAP = {"DEF": "DST"}  # Sleeper's team-defense code -> our contract
SCORING_FIELD = {"ppr": "pts_ppr", "half_ppr": "pts_half_ppr", "standard": "pts_std"}
OUTPUT_COLUMNS = ["Rank", "Total_FPTS", "Average_FPTS", "Player", "Team", "Position"]
VALID_POSITIONS = {"QB", "RB", "WR", "TE", "K", "DST"}

# NFL regular season length. Used as a fixed averaging divisor rather than
# each record's own `gp` field: `gp` is inconsistent across position types in
# Sleeper's data (e.g. team defenses report gp=1 for a season-total
# projection), which would otherwise produce a wildly inflated Average_FPTS.
GAMES_PER_SEASON = 17


def fetch_sleeper_projections(season, positions=SLEEPER_POSITIONS, scoring="ppr", session=None):
    """Fetch season-aggregate projections from Sleeper for the given positions.

    Returns a DataFrame with columns Player, Team, Position, Total_FPTS,
    Average_FPTS (not yet Rank-assigned or column-ordered).
    """
    if scoring not in SCORING_FIELD:
        raise ValueError(f"Unknown scoring format: {scoring!r}. Expected one of {list(SCORING_FIELD)}")
    stats_field = SCORING_FIELD[scoring]

    http = session or requests
    rows = []
    for pos in positions:
        url = f"{SLEEPER_BASE}/projections/nfl/{season}"
        params = {"season_type": "regular", "position[]": pos}
        data = None
        last_error = None
        for attempt in range(2):
            try:
                resp = http.get(url, params=params, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                break
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
        if data is None:
            raise RuntimeError(f"Failed to fetch Sleeper projections for position {pos}") from last_error

        for record in data:
            stats = record.get("stats") or {}
            total_fpts = stats.get(stats_field)
            if total_fpts is None:
                continue

            player = record.get("player") or {}
            first_name = player.get("first_name") or ""
            last_name = player.get("last_name") or ""
            name = f"{first_name} {last_name}".strip()
            team = player.get("team") or record.get("team")
            raw_position = player.get("position") or pos
            position = POSITION_REMAP.get(raw_position, raw_position)

            if not name or not team or position not in VALID_POSITIONS:
                continue

            rows.append(
                {
                    "Player": name,
                    "Team": team,
                    "Position": position,
                    "Total_FPTS": float(total_fpts),
                    "Average_FPTS": round(float(total_fpts) / GAMES_PER_SEASON, 1),
                }
            )

    return pd.DataFrame(rows)


def _assign_overall_rank(df):
    df = df.sort_values("Total_FPTS", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df[OUTPUT_COLUMNS]


def load_static_fallback(path=DEFAULT_STATIC_CSV):
    """Escape hatch: the original manually-scraped, one-time snapshot."""
    return pd.read_csv(path)


def validate_rankings(df):
    """Raise AssertionError if `df` doesn't match the expected data contract."""
    assert list(df.columns) == OUTPUT_COLUMNS, f"Unexpected columns: {list(df.columns)}"
    assert df["Rank"].is_unique, "Rank column has duplicates"
    assert list(df["Rank"]) == list(range(1, len(df) + 1)), "Rank is not a contiguous 1..N sequence"
    assert df["Position"].isin(VALID_POSITIONS).all(), f"Unexpected position values: {set(df['Position']) - VALID_POSITIONS}"
    assert df["Player"].notna().all(), "Null Player values present"
    assert df["Team"].notna().all(), "Null Team values present"
    assert 300 <= len(df) <= 700, f"Row count {len(df)} outside the sane band (300-700)"


def build_live_rankings(season=2026, scoring="ppr", source="auto"):
    """Build the player pool DataFrame.

    source: "auto" tries Sleeper and falls back to the static CSV on any
    failure or failed validation (logged as a warning). "sleeper" forces the
    live path and raises on failure. "static" forces the fallback CSV.
    """
    if source not in {"auto", "sleeper", "static"}:
        raise ValueError(f"Unknown source: {source!r}. Expected 'auto', 'sleeper', or 'static'")

    if source == "static":
        return load_static_fallback()

    try:
        raw = fetch_sleeper_projections(season, scoring=scoring)
        df = _assign_overall_rank(raw)
        validate_rankings(df)
        return df
    except Exception:
        if source == "sleeper":
            raise
        logger.warning("Live Sleeper rankings unavailable, falling back to static CSV", exc_info=True)
        return load_static_fallback()


def _parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--scoring", choices=list(SCORING_FIELD), default="ppr")
    parser.add_argument("--source", choices=["auto", "sleeper", "static"], default="auto")
    parser.add_argument("--refresh-cache", action="store_true", help="Write the result to live_rankings_cache.csv")
    return parser.parse_args()


def main():
    args = _parse_args()
    df = build_live_rankings(season=args.season, scoring=args.scoring, source=args.source)
    print(df.head(20).to_string(index=False))
    print(f"\n{len(df)} total players.")
    for pos in sorted(VALID_POSITIONS):
        print(f"\nTop 5 {pos}:")
        print(df[df["Position"] == pos].head(5).to_string(index=False))

    if args.refresh_cache:
        df.to_csv(DEFAULT_CACHE_CSV, index=False)
        print(f"\nWrote cache to {DEFAULT_CACHE_CSV}")


if __name__ == "__main__":
    main()
