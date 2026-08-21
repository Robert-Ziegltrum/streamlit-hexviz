"""S2 grid utilities: point binning and cell aggregation."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

try:
    import s2sphere as s2
    S2_AVAILABLE = True
except ImportError:
    S2_AVAILABLE = False


def _require_s2() -> None:
    if not S2_AVAILABLE:
        raise ImportError(
            "S2 support is an optional dependency.\n"
            "Install with:\n"
            "  pip install \"streamlit-hexviz[s2]\"\n"
            "\n"
            "Or install directly:\n"
            "  pip install s2sphere"
        )


# ---------------------------------------------------------------------------
# Core transform: points → aggregated S2 DataFrame
# ---------------------------------------------------------------------------


def points_to_s2(
    df: pd.DataFrame,
    lat: str,
    lon: str,
    level: int = 12,
    weight: str | None = None,
    agg: str = "sum",
) -> pd.DataFrame:
    """
    Bin lat/lon points into S2 cells and aggregate.

    Parameters
    ----------
    df        : input DataFrame with point coordinates
    lat, lon  : column names
    level     : S2 level (0-30, typical range 8-15)
    weight    : optional weight column; defaults to count
    agg       : "sum", "mean", "count", "max", "min"

    Returns
    -------
    DataFrame with: s2_token, value, lat, lon, geometry (polygon coords list)
    """
    _require_s2()

    work = df[[lat, lon]].copy()
    work["_weight"] = df[weight].values if weight else 1.0
    work["s2_token"] = [_latlng_to_token(
        row[lat], row[lon], level) for _, row in work.iterrows()]

    agg_map = {"sum": "sum", "mean": "mean",
               "count": "count", "max": "max", "min": "min"}
    if agg not in agg_map:
        raise ValueError(f"agg must be one of {list(agg_map)}, got {agg!r}")

    grouped = (
        work.groupby("s2_token")["_weight"]
        .agg(agg_map[agg])
        .reset_index()
        .rename(columns={"_weight": "value"})
    )
    grouped = _attach_s2_geometry(grouped, level)
    return grouped


# ---------------------------------------------------------------------------
# Geometry helpers (s2sphere backend)
# ---------------------------------------------------------------------------


def _latlng_to_token(lat: float, lon: float, level: int) -> str:
    ll = s2.LatLng.from_degrees(lat, lon)
    cell = s2.CellId.from_lat_lng(ll).parent(level)
    return cell.to_token()


def _attach_s2_geometry(df: pd.DataFrame, level: int) -> pd.DataFrame:
    """Add centroid and polygon boundary for each S2 token."""
    centroids, polygons = [], []
    for token in df["s2_token"]:
        cell_id = s2.CellId.from_token(token)
        cell = s2.Cell(cell_id)
        center = s2.LatLng.from_point(cell.get_center())
        centroids.append((center.lat().degrees, center.lng().degrees))

        vertices = []
        for i in range(4):
            v = s2.LatLng.from_point(cell.get_vertex(i))
            vertices.append([v.lng().degrees, v.lat().degrees])
        vertices.append(vertices[0])  # close ring
        polygons.append({"type": "Polygon", "coordinates": [vertices]})

    df["lat"] = [c[0] for c in centroids]
    df["lon"] = [c[1] for c in centroids]
    df["geometry"] = polygons
    return df
