"""
Optional GeoPandas input support, plus lat/lon column auto-detection for
plain DataFrame input.

Lets `h3_map`, `h3_heatmap`, `s2_map`, and `a5_map` accept either:
  - a plain DataFrame, with `lat`/`lon` column names either given
    explicitly or auto-detected (mirroring `st.map`'s convention), or
  - a GeoDataFrame of Point geometries, with `lat`/`lon` used only as
    the target column names to write the extracted coordinates into.

Kept as a lazy-imported, optional dependency — mirrors the existing
pattern for S2 (_s2_utils.py) and A5 (_a5_utils.py): the rest of the
package has no hard dependency on geopandas, and `normalize_input()`
falls straight through to the plain-DataFrame path for any caller
that isn't passing a GeoDataFrame.

`normalize_input()` is the single public entry point, called at the
top of each raw-point function (`h3_map`/`s2_map`/`a5_map`). It
dispatches, in this order:

  1. Polars rejection — checked first and unconditionally, before any
     other branching, so a Polars DataFrame gets one clear TypeError
     instead of falling into the plain-DataFrame branch and failing
     confusingly inside column-name resolution. Uses a duck-typed
     module-name check so this doesn't add a polars dependency just
     to detect and reject it.
  2. GeoDataFrame branch (`_normalize_geodataframe`) — geometry is
     always the source of truth here, even if lat/lon-shaped columns
     also happen to be present. Auto-detection never runs here.
  3. Plain-DataFrame branch (`_normalize_pandas_dataframe`) — resolves
     `lat`/`lon` column names via `resolve_lat_lon_columns`, either
     explicit or auto-detected.

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


# Column-name candidates for auto-detection on plain-DataFrame input.
# Deliberately matches st.map's own convention (see
# streamlit/lib/streamlit/elements/map.py) so users learn no new
# vocabulary. Unlike st.map — which stores these as a plain `set` and
# silently takes whichever candidate its (arbitrary, hash-order-
# dependent) iteration happens to hit first — `resolve_lat_lon_columns`
# below raises if more than one candidate is present, rather than
# picking one for the user.
_DEFAULT_LAT_COL_NAMES = {"lat", "latitude", "LAT", "LATITUDE"}
_DEFAULT_LON_COL_NAMES = {"lon", "longitude", "LON", "LONGITUDE"}


def normalize_input(
    df, lat: str | None = None, lon: str | None = None
) -> tuple[pd.DataFrame, str, str]:
    """
    Resolve `df` into (plain_dataframe, lat_col, lon_col).

    `lat`/`lon` are optional. Their meaning differs by input type:
      - Plain DataFrame: the name of an *existing* column to use, or
        None to auto-detect (see `resolve_lat_lon_columns`).
      - GeoDataFrame: the name to *write* the coordinates extracted
        from geometry into, or None to default to "latitude"/
        "longitude". Never used to look up an existing column — see
        `_normalize_geodataframe`.

    Raises TypeError for Polars input, ValueError for anything
    `resolve_lat_lon_columns` or `_normalize_geodataframe` rejects.
    """
    if type(df).__module__.startswith("polars"):
        raise TypeError(
            "Polars DataFrames aren't supported as input — convert with "
            "`.to_pandas()` first. (Polars input support was considered "
            "and deliberately deferred; see project notes.)"
        )

    if GEOPANDAS_AVAILABLE and isinstance(df, gpd.GeoDataFrame):
        return _normalize_geodataframe(df, lat, lon)

    return _normalize_pandas_dataframe(df, lat, lon)


def resolve_lat_lon_columns(
    df: pd.DataFrame, lat: str | None, lon: str | None
) -> tuple[str, str]:
    """
    Resolve which columns of a plain DataFrame hold latitude/longitude.

    If `lat`/`lon` are given explicitly, they must exist in `df`.
    Otherwise, auto-detect using the same candidate names as `st.map`
    (see module docstring) — but raise on ambiguity (more than one
    candidate present) rather than silently picking one, and raise if
    none are found.
    """

    def _resolve(explicit: str | None, candidates: set[str], label: str) -> str:
        if explicit is not None:
            if explicit not in df.columns:
                raise ValueError(
                    f"{label} column {explicit!r} not found in DataFrame. "
                    f"Existing columns: {sorted(df.columns)}"
                )
            return explicit

        found = [c for c in candidates if c in df.columns]
        if not found:
            raise ValueError(
                f"Couldn't find a {label} column. Pass `{label}=` explicitly, "
                f"or name a column one of: {sorted(candidates)}. "
                f"Existing columns: {sorted(df.columns)}"
            )
        if len(found) > 1:
            raise ValueError(
                f"Ambiguous {label} column — found more than one candidate: "
                f"{sorted(found)}. Pass `{label}=` explicitly to disambiguate."
            )
        return found[0]

    lat_col = _resolve(lat, _DEFAULT_LAT_COL_NAMES, "lat")
    lon_col = _resolve(lon, _DEFAULT_LON_COL_NAMES, "lon")
    return lat_col, lon_col


def _normalize_pandas_dataframe(
    df: pd.DataFrame, lat: str | None, lon: str | None
) -> tuple[pd.DataFrame, str, str]:
    """Plain-DataFrame branch: resolve column names, pass df through unchanged."""
    lat_col, lon_col = resolve_lat_lon_columns(df, lat, lon)
    return df, lat_col, lon_col


def _normalize_geodataframe(
    gdf: "gpd.GeoDataFrame", lat: str | None, lon: str | None
) -> tuple[pd.DataFrame, str, str]:
    """
    GeoDataFrame branch: extract Point geometry into `lat`/`lon` columns.

    - geometry must be all Points; anything else raises ValueError
      (points-only scope — see module docstring).
    - a missing CRS emits a UserWarning and is assumed to be EPSG:4326
      (WGS84) rather than silently guessed without a trace.
    - a CRS other than EPSG:4326 is reprojected automatically.
    - `lat`/`lon` default to "latitude"/"longitude" if not given. If
      the resolved target name already exists as a *non-geometry*
      column in `gdf`, raises rather than silently overwriting or
      dropping that column — the caller may be relying on it for
      something else (a tooltip field, a weight column, etc.).
    """
    lat_col = lat or "latitude"
    lon_col = lon or "longitude"

    for col_name in (lat_col, lon_col):
        if col_name in gdf.columns and col_name != gdf.geometry.name:
            raise ValueError(
                f"GeoDataFrame already has a column named {col_name!r} that "
                "isn't the geometry column. Extracting coordinates into it "
                "would silently overwrite existing data — pass `lat=`/`lon=` "
                "with different target names, or rename/drop that column "
                "first."
            )

    geom_types = set(gdf.geometry.geom_type.dropna().unique())
    if not geom_types.issubset({"Point"}):
        raise ValueError(
            "GeoDataFrame input only supports Point geometries, got "
            f"{sorted(geom_types)}. Polygon-to-hex conversion isn't "
            "supported yet — extract point coordinates yourself "
            "(e.g. via `.centroid`) before calling, if that's an "
            "acceptable approximation for your use case."
        )

    if gdf.crs is None:
        warnings.warn(
            "GeoDataFrame has no CRS set — assuming EPSG:4326 (WGS84). "
            "Set `gdf.crs` explicitly to silence this warning.",
            UserWarning,
            stacklevel=4,
        )
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    plain = pd.DataFrame(gdf.drop(columns=gdf.geometry.name))
    plain[lat_col] = gdf.geometry.y.values
    plain[lon_col] = gdf.geometry.x.values
    return plain, lat_col, lon_col
