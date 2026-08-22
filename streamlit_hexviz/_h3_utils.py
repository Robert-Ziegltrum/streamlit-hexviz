"""H3 grid utilities: point binning and cell aggregation."""

from __future__ import annotations

import pandas as pd
from typing import Literal

try:
    import h3

    H3_AVAILABLE = True
except ImportError:
    H3_AVAILABLE = False


def _require_h3() -> None:
    if not H3_AVAILABLE:
        raise ImportError("h3 is required: pip install h3")


def _coerce_h3_token(value: object, *, h3_index_type: Literal["str", "int"]) -> str:
    """
    Coerce an H3 index value into the canonical string token.

    The h3-py v4 API expects string tokens for functions like `cell_to_latlng`.
    """
    _require_h3()

    if h3_index_type == "str":
        return str(value)
    if h3_index_type == "int":
        return h3.int_to_str(int(value))
    raise ValueError(f"h3_index_type must be 'str' or 'int', got {h3_index_type!r}")


def points_to_h3(
    df: pd.DataFrame,
    lat: str,
    lon: str,
    resolution: int = 7,
    weight: str | None = None,
    agg: str = "sum",
) -> pd.DataFrame:
    """
    Bin lat/lon points into H3 cells and aggregate.

    Returns DataFrame with: h3_index, value, lat (centroid), lon (centroid).
    The geometry column is NOT needed — pydeck's H3HexagonLayer resolves
    hex boundaries from h3_index directly.
    """
    _require_h3()

    work = df[[lat, lon]].copy()
    work["_weight"] = df[weight].values if weight else 1.0
    work["h3_index"] = [
        h3.latlng_to_cell(row[lat], row[lon], resolution)
        for _, row in df[[lat, lon]].iterrows()
    ]

    agg_map = {
        "sum": "sum",
        "mean": "mean",
        "count": "count",
        "max": "max",
        "min": "min",
    }
    if agg not in agg_map:
        raise ValueError(f"agg must be one of {list(agg_map)}, got {agg!r}")

    grouped = (
        work.groupby("h3_index")["_weight"]
        .agg(agg_map[agg])
        .reset_index()
        .rename(columns={"_weight": "value"})
    )

    # Attach centroids (used for map auto-centring and HeatmapLayer)
    centroids = [h3.cell_to_latlng(idx) for idx in grouped["h3_index"]]
    grouped["lat"] = [c[0] for c in centroids]
    grouped["lon"] = [c[1] for c in centroids]

    return grouped


def h3_df_to_aggregated(
    df: pd.DataFrame,
    h3_col: str,
    value_col: str,
    agg: str = "sum",
    h3_index_type: Literal["str", "int"] = "str",
) -> pd.DataFrame:
    """
    Aggregate a DataFrame that already has an H3 index column.
    Returns: h3_index, value, lat (centroid), lon (centroid).
    """
    _require_h3()

    agg_fn = {
        "sum": "sum",
        "mean": "mean",
        "count": "count",
        "max": "max",
        "min": "min",
    }
    if agg not in agg_fn:
        raise ValueError(f"agg must be one of {list(agg_fn)}, got {agg!r}")

    grouped = (
        df.groupby(h3_col)[value_col]
        .agg(agg_fn[agg])
        .reset_index()
        .rename(columns={h3_col: "h3_index", value_col: "value"})
    )

    # h3-py v4 expects string tokens; coerce if caller provided integer ids.
    grouped["h3_index"] = [
        _coerce_h3_token(v, h3_index_type=h3_index_type) for v in grouped["h3_index"]
    ]

    centroids = [h3.cell_to_latlng(idx) for idx in grouped["h3_index"]]
    grouped["lat"] = [c[0] for c in centroids]
    grouped["lon"] = [c[1] for c in centroids]

    return grouped


def validate_resolution(resolution: int) -> None:
    if not (0 <= resolution <= 15):
        raise ValueError(f"H3 resolution must be 0-15, got {resolution}")


def h3_resolution_area_km2(resolution: int) -> float:
    _require_h3()
    return h3.average_hexagon_area(resolution, unit="km^2")
