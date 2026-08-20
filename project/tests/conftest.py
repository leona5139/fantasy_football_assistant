import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def sample_player_pool():
    """Small, deterministic, hand-built player pool spanning all positions.
    Fast and fully inspectable -- not the real 400-600 row live/static data.
    """
    rows = []
    # (position, count, top_fpts, step)
    specs = [
        ("QB", 6, 360, 20),
        ("RB", 8, 330, 18),
        ("WR", 8, 310, 16),
        ("TE", 5, 250, 15),
        ("K", 3, 116, 5),
        ("DST", 3, 106, 5),
    ]
    for pos, count, top_fpts, step in specs:
        for i in range(count):
            total_fpts = top_fpts - i * step
            rows.append(
                {
                    "Total_FPTS": float(total_fpts),
                    "Average_FPTS": round(total_fpts / 17, 1),
                    "Player": f"{pos}_{i + 1}",
                    "Team": "AAA",
                    "Position": pos,
                }
            )

    df = pd.DataFrame(rows).sort_values("Total_FPTS", ascending=False).reset_index(drop=True)
    df.insert(0, "Rank", range(1, len(df) + 1))
    return df
