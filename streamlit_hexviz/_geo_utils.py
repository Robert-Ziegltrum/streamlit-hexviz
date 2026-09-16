"""
Optional GeoPandas input support.

Lets `h3_map`, `h3_heatmap`, `s2_map`, and `a5_map` accept a GeoDataFrame
of Point geometries in place of a plain DataFrame + lat/lon column
names. Kept as a lazy-imported, optional dependency — mirrors the
existing pattern for S2 (_s2_utils.py) and A5 (_a5_utils.py): the rest
of the package has no hard dependency on geopandas, and
`normalize_input()` is a no-op for any caller that isn't passing a
GeoDataFrame.

A Polars DataFrame is explicitly rejected with a clear TypeError (via a
duck-typed module-name check, so this doesn't add a polars dependency
just to detect and reject it) rather than left to fail later with a
confusing error inside points_to_h3/points_to_s2/points_to_a5.

Scope: points only. Polygon/line geometries are rejected with a clear
error rather than silently reduced to (e.g.) a centroid — that would
quietly expand what this function claims to support. Polygon-to-hex
conversion is a distinct, unbuilt feature (see CLAUDE.md roadmap).

Null/missing geometry handling is deliberately NOT special-cased here.
Whatever points_to_h3 / points_to_s2 / points_to_a5 currently do with a
NaN lat/lon value (no dropna today — see _h3_utils.points_to_h3, which
iterates every row through h3.latlng_to_cell with no guard) is exactly
what happens with a NaN produced by a missing/None geometry too. This
keeps both input paths behaving identically instead of one silently
dropping rows and the other raising deep inside h3-py/a5/s2sphere.
Revisit if/when the plain-DataFrame path gets explicit null handling.
"""

from __future__ import annotations

import warnings

import pandas as pd

try:
    import geopandas as gpd

    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False


def normalize_input(df, lat: str, lon: str) -> pd.DataFrame:
    """
    Return a plain pandas DataFrame with `lat`/`lon` columns populated.

    If `df` isn't a GeoDataFrame (or geopandas isn't installed), it's
    returned unchanged — existing plain-DataFrame + lat/lon-column-name
    callers see no change in behaviour.

    If `df` is a GeoDataFrame:
      - geometry must be all Points; anything else raises ValueError
        (points-only scope — see module docstring).
      - a missing CRS emits a UserWarning and is assumed to be
        EPSG:4326 (WGS84) rather than silently guessed without a trace.
      - a CRS other than EPSG:4326 is reprojected automatically.
      - `lat`/`lon` columns are added (or overwritten) from the
        geometry's y/x, and the geometry column is dropped, so the
        result is a plain DataFrame the existing points_to_* pipelines
        can consume with zero further changes.
    """
    if type(df).__module__.startswith("polars"):
        raise TypeError(
            "Polars DataFrames aren't supported as input — convert with "
            "`.to_pandas()` first. (Polars input support was considered "
            "and deliberately deferred; see project notes.)"
        )

    if not (GEOPANDAS_AVAILABLE and isinstance(df, gpd.GeoDataFrame)):
        return df

    geom_types = set(df.geometry.geom_type.dropna().unique())
    if not geom_types.issubset({"Point"}):
        raise ValueError(
            "GeoDataFrame input only supports Point geometries, got "
            f"{sorted(geom_types)}. Polygon-to-hex conversion isn't "
            "supported yet — extract point coordinates yourself "
            "(e.g. via `.centroid`) before calling, if that's an "
            "acceptable approximation for your use case."
        )

    if df.crs is None:
        warnings.warn(
            "GeoDataFrame has no CRS set — assuming EPSG:4326 (WGS84). "
            "Set `gdf.crs` explicitly to silence this warning.",
            UserWarning,
            stacklevel=2,
        )
    elif df.crs.to_epsg() != 4326:
        df = df.to_crs(epsg=4326)

    plain = pd.DataFrame(df.drop(columns=df.geometry.name))
    plain[lat] = df.geometry.y.values
    plain[lon] = df.geometry.x.values
    return plain
