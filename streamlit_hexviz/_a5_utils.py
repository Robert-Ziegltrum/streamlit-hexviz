"""
A5 grid utilities: point binning and cell aggregation.

A5 (https://a5geo.org) partitions the globe into pentagonal cells across
31 resolution levels (0 = coarsest, continent-scale; 30 = finest,
millimetre-scale), addressed as unsigned 64-bit cell IDs.

IMPORTANT — PyPI name collision:
`pip install a5` on public PyPI currently resolves to an unrelated package
(an OpenAI-agent helper), NOT the A5 geospatial index. If your local `a5`
import is the geospatial library, make sure it's installed from the
correct source (e.g. a git URL or private index) rather than a bare
`a5` PyPI dependency — otherwise downstream installs of this extra will
silently pull the wrong package. See pyproject.toml's `a5` extra.

API assumption:
This module calls `a5.lonlat_to_cell`, `a5.cell_to_lonlat`, matching the
A5 JS reference API (lonLatToCell / cellToLonLat) translated to Python's
snake_case convention, the same way h3-py v4 mirrors the H3 JS/C API.
Verify these names against your installed `a5` build — if they differ,
this is the only file that needs adjusting.
"""
from __future__ import annotations

import pandas as pd

try:
    import a5
    A5_AVAILABLE = True
except ImportError:
    A5_AVAILABLE = False


def _require_a5() -> None:
    if not A5_AVAILABLE:
        raise ImportError(
            "a5 is required for A5 support.\n"
            "Install with:\n"
            "  pip install \"streamlit-hexviz[a5]\"\n"
            "\n"
            "Note: verify this resolves to the A5 geospatial library "
            "(https://a5geo.org), not the unrelated PyPI package of the "
            "same name."
        )


# A5 resolution levels: 0 (coarsest) to 30 (finest).
A5_RANGE: tuple[int, int] = (0, 30)

# Default resolution for point-binning entry points.
# TODO: calibrate against a5.cell_area(resolution) so the default visually
# matches h3_map's res-7 default (~5.16 km^2 average cell area) rather than
# guessing — A5 halves cell edge length (~quarters area) per resolution
# step, vs. H3's ~7x area factor per step, so the "equivalent" level sits
# deeper in A5's 0-30 range than H3's 0-15.
A5_DEFAULT_RESOLUTION: int = 10


def validate_resolution(resolution: int) -> None:
    lo, hi = A5_RANGE
    if not (lo <= resolution <= hi):
        raise ValueError(f"A5 resolution must be in {A5_RANGE}, got {resolution}")


def points_to_a5(
    df: pd.DataFrame,
    lat: str,
    lon: str,
    resolution: int = A5_DEFAULT_RESOLUTION,
    weight: str | None = None,
    agg: str = "sum",
) -> pd.DataFrame:
    """
    Bin lat/lon points into A5 cells and aggregate.

    Returns DataFrame with: a5_index, value, lat (centroid), lon (centroid).
    No geometry column needed — pydeck's A5Layer resolves pentagon
    boundaries from the a5_index directly (get_pentagon), the same way
    H3HexagonLayer resolves hex boundaries from get_hexagon.
    """
    _require_a5()
    validate_resolution(resolution)

    work = df[[lat, lon]].copy()
    work["_weight"] = df[weight].values if weight else 1.0
    work["a5_index"] = [
        a5.lonlat_to_cell(row[lon], row[lat], resolution)
        for _, row in df[[lat, lon]].iterrows()
    ]

    agg_map = {"sum": "sum", "mean": "mean", "count": "count", "max": "max", "min": "min"}
    if agg not in agg_map:
        raise ValueError(f"agg must be one of {list(agg_map)}, got {agg!r}")

    grouped = (
        work.groupby("a5_index")["_weight"]
        .agg(agg_map[agg])
        .reset_index()
        .rename(columns={"_weight": "value"})
    )

    # Attach centroids (used for map auto-centring).
    # A5's reference API returns (lon, lat) — note the reversed order vs h3's
    # cell_to_latlng, which returns (lat, lon).
    centroids = [a5.cell_to_lonlat(idx) for idx in grouped["a5_index"]]
    grouped["lon"] = [c[0] for c in centroids]
    grouped["lat"] = [c[1] for c in centroids]

    return grouped


def a5_df_to_aggregated(
    df: pd.DataFrame,
    a5_col: str,
    value_col: str,
    agg: str = "sum",
) -> pd.DataFrame:
    """
    Aggregate a DataFrame that already has an A5 index column.
    Returns: a5_index, value, lat (centroid), lon (centroid).
    """
    _require_a5()

    agg_fn = {"sum": "sum", "mean": "mean", "count": "count", "max": "max", "min": "min"}
    if agg not in agg_fn:
        raise ValueError(f"agg must be one of {list(agg_fn)}, got {agg!r}")

    grouped = (
        df.groupby(a5_col)[value_col]
        .agg(agg_fn[agg])
        .reset_index()
        .rename(columns={a5_col: "a5_index", value_col: "value"})
    )

    centroids = [a5.cell_to_lonlat(idx) for idx in grouped["a5_index"]]
    grouped["lon"] = [c[0] for c in centroids]
    grouped["lat"] = [c[1] for c in centroids]

    return grouped
