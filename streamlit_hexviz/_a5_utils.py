"""
A5 grid utilities: point binning and cell aggregation.

A5 (https://a5geo.org) partitions the globe into pentagonal cells across
31 resolution levels (0 = coarsest, continent-scale; 30 = finest,
~30mm^2), addressed as unsigned 64-bit cell IDs.

Install: pip install "streamlit-hexviz[a5]"  ->  pulls in `pya5` from PyPI,
which is imported as `import a5`. This is the official package published
by A5's own maintainer (felixpalmer) — verified against the real API
below, not inferred from the JS reference docs.

Cell IDs are represented as hex strings (via a5.u64_to_hex /
a5.hex_to_u64), not raw Python ints. A5 cell IDs are 64-bit, which
exceeds JavaScript's safe integer range (2^53) — pydeck serialises
DataFrame columns to JSON for the browser, so raw ints risk silent
precision loss there. Hex strings round-trip safely, and match the
`pentagon: string` field type used in deck.gl's own A5Layer example.
"""
from __future__ import annotations

import pandas as pd
from typing import Literal

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
            "  pip install \"streamlit-hexviz[a5]\""
        )


def _coerce_a5_token(value: object, *, a5_index_type: Literal["hex", "int"]) -> str:
    """Coerce an A5 cell value into the canonical hex-string token."""
    _require_a5()

    if a5_index_type == "hex":
        return str(value)
    if a5_index_type == "int":
        return a5.u64_to_hex(int(value))
    raise ValueError(
        f"a5_index_type must be 'hex' or 'int', got {a5_index_type!r}")


# A5 resolution levels: 0 (coarsest) to 30 (finest) — confirmed via a5.MAX_RESOLUTION.
A5_RANGE: tuple[int, int] = (0, 30)

# Default resolution for point-binning entry points.
# Calibrated against a5.cell_area(resolution): H3's res-7 default averages
# ~5.16 km^2 per cell; A5 resolution 11 averages ~8.1 km^2, the closest
# match on the log scale (res 12 averages ~2.0 km^2, further away). A5
# roughly quarters cell area per resolution step vs. H3's ~7x factor per
# step, hence landing at a higher resolution number for similar detail.
A5_DEFAULT_RESOLUTION: int = 11


def validate_resolution(resolution: int) -> None:
    lo, hi = A5_RANGE
    if not (lo <= resolution <= hi):
        raise ValueError(
            f"A5 resolution must be in {A5_RANGE}, got {resolution}")


def a5_resolution_area_km2(resolution: int) -> float:
    """Average cell area at a given A5 resolution, in km^2."""
    _require_a5()
    return a5.cell_area(resolution) / 1e6


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

    Returns DataFrame with: a5_index (hex str), value, lat (centroid), lon (centroid).
    No geometry column needed — pydeck's A5Layer resolves pentagon
    boundaries from the a5_index directly (get_pentagon), the same way
    H3HexagonLayer resolves hex boundaries from get_hexagon.
    """
    _require_a5()
    validate_resolution(resolution)

    work = df[[lat, lon]].copy()
    work["_weight"] = df[weight].values if weight else 1.0
    # a5.lonlat_to_cell takes the coordinate as a single (lon, lat) pair,
    # not two separate positional args.
    work["a5_index"] = [
        a5.u64_to_hex(a5.lonlat_to_cell((row[lon], row[lat]), resolution))
        for _, row in df[[lat, lon]].iterrows()
    ]

    agg_map = {"sum": "sum", "mean": "mean",
               "count": "count", "max": "max", "min": "min"}
    if agg not in agg_map:
        raise ValueError(f"agg must be one of {list(agg_map)}, got {agg!r}")

    grouped = (
        work.groupby("a5_index")["_weight"]
        .agg(agg_map[agg])
        .reset_index()
        .rename(columns={"_weight": "value"})
    )

    # Attach centroids (used for map auto-centring). a5.cell_to_lonlat
    # returns (lon, lat) — reversed vs. h3.cell_to_latlng's (lat, lon).
    centroids = [a5.cell_to_lonlat(a5.hex_to_u64(idx))
                 for idx in grouped["a5_index"]]
    grouped["lon"] = [c[0] for c in centroids]
    grouped["lat"] = [c[1] for c in centroids]

    return grouped


def a5_df_to_aggregated(
    df: pd.DataFrame,
    a5_col: str,
    value_col: str,
    agg: str = "sum",
    a5_index_type: Literal["hex", "int"] = "hex",
) -> pd.DataFrame:
    """
    Aggregate a DataFrame that already has an A5 index column.
    Returns: a5_index (hex str), value, lat (centroid), lon (centroid).
    """
    _require_a5()

    agg_fn = {"sum": "sum", "mean": "mean",
              "count": "count", "max": "max", "min": "min"}
    if agg not in agg_fn:
        raise ValueError(f"agg must be one of {list(agg_fn)}, got {agg!r}")

    grouped = (
        df.groupby(a5_col)[value_col]
        .agg(agg_fn[agg])
        .reset_index()
        .rename(columns={a5_col: "a5_index", value_col: "value"})
    )

    # Callers may already have hex tokens or raw 64-bit ints; normalise to hex.
    grouped["a5_index"] = [
        _coerce_a5_token(v, a5_index_type=a5_index_type) for v in grouped["a5_index"]
    ]

    centroids = [a5.cell_to_lonlat(a5.hex_to_u64(idx))
                 for idx in grouped["a5_index"]]
    grouped["lon"] = [c[0] for c in centroids]
    grouped["lat"] = [c[1] for c in centroids]

    return grouped
