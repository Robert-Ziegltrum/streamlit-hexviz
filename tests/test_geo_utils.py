"""
Tests for streamlit_hexviz._geo_utils.normalize_input.

Run directly (no pytest needed for streamlit_hexviz itself, since
_geo_utils.py has no Streamlit import) with:
    pytest tests/test_geo_utils.py -v

Requires geopandas + shapely to exercise the GeoDataFrame paths; the
plain-pandas-passthrough tests run either way. If geopandas isn't
installed, the GeoDataFrame-specific tests are skipped rather than
failing, since geopandas is an optional dependency for this module.
"""

from __future__ import annotations

import warnings

import pandas as pd
import pytest

from streamlit_hexviz._geo_utils import normalize_input

gpd = pytest.importorskip("geopandas", reason="geopandas is optional")
from shapely.geometry import LineString, Point, Polygon  # noqa: E402


# ---------------------------------------------------------------------------
# Plain pandas passthrough — must be a complete no-op
# ---------------------------------------------------------------------------


def test_plain_dataframe_passthrough_is_identity():
    """A plain DataFrame must come back as the exact same object — zero
    behaviour change for every existing caller that doesn't use GeoPandas."""
    df = pd.DataFrame({"lat": [1.0, 2.0], "lon": [3.0, 4.0]})
    out = normalize_input(df, "lat", "lon")
    assert out is df


def test_plain_dataframe_with_arbitrary_columns_untouched():
    df = pd.DataFrame({"foo": [1], "bar": ["x"]})
    out = normalize_input(df, "lat", "lon")
    assert out is df
    assert list(out.columns) == ["foo", "bar"]


# ---------------------------------------------------------------------------
# Happy path: Point geometry, WGS84
# ---------------------------------------------------------------------------


def test_geodataframe_points_wgs84_extracts_lat_lon():
    gdf = gpd.GeoDataFrame(
        {"sales": [10, 20]},
        geometry=[Point(10.0, 53.5), Point(9.9, 53.6)],
        crs="EPSG:4326",
    )
    out = normalize_input(gdf, "lat", "lon")

    assert isinstance(out, pd.DataFrame)
    assert not isinstance(out, gpd.GeoDataFrame)  # geometry column is gone
    assert list(out["lat"]) == [53.5, 53.6]
    assert list(out["lon"]) == [10.0, 9.9]
    assert "sales" in out.columns  # non-geometry columns survive
    assert "geometry" not in out.columns


def test_geodataframe_respects_custom_lat_lon_param_names():
    """normalize_input must write to whatever column names the caller's
    lat/lon parameters specify, not hardcode 'lat'/'lon'."""
    gdf = gpd.GeoDataFrame(
        {"sales": [1]}, geometry=[Point(10.0, 53.5)], crs="EPSG:4326"
    )
    out = normalize_input(gdf, "latitude", "longitude")
    assert out["latitude"].iloc[0] == 53.5
    assert out["longitude"].iloc[0] == 10.0


def test_geodataframe_with_custom_geometry_column_name():
    """The active geometry column isn't always literally named 'geometry'."""
    gdf = gpd.GeoDataFrame(
        {"sales": [1]}, geometry=[Point(10.0, 53.5)], crs="EPSG:4326"
    )
    gdf = gdf.rename_geometry("geom")
    out = normalize_input(gdf, "lat", "lon")
    assert "geom" not in out.columns
    assert out["lat"].iloc[0] == 53.5


# ---------------------------------------------------------------------------
# CRS handling
# ---------------------------------------------------------------------------


def test_missing_crs_warns_and_assumes_wgs84():
    gdf = gpd.GeoDataFrame({"x": [1]}, geometry=[Point(1.0, 2.0)])  # no crs
    assert gdf.crs is None

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = normalize_input(gdf, "lat", "lon")

    assert any(issubclass(w.category, UserWarning) for w in caught)
    assert any("no CRS" in str(w.message) for w in caught)
    # Coordinates pass through unprojected (assumed already WGS84).
    assert out["lon"].iloc[0] == 1.0
    assert out["lat"].iloc[0] == 2.0


def test_non_wgs84_crs_is_reprojected():
    # A UTM point reprojects to a very different lat/lon than its raw x/y.
    gdf = gpd.GeoDataFrame(
        {"x": [1]}, geometry=[Point(560000, 5930000)], crs="EPSG:32632"
    )
    out = normalize_input(gdf, "lat", "lon")
    assert out["lat"].iloc[0] == pytest.approx(53.5, abs=0.1)
    assert out["lon"].iloc[0] == pytest.approx(9.9, abs=0.1)


def test_wgs84_crs_is_not_reprojected_or_warned():
    gdf = gpd.GeoDataFrame({"x": [1]}, geometry=[Point(10.0, 53.5)], crs="EPSG:4326")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = normalize_input(gdf, "lat", "lon")
    assert len(caught) == 0
    assert out["lon"].iloc[0] == 10.0
    assert out["lat"].iloc[0] == 53.5


# ---------------------------------------------------------------------------
# Points-only scope
# ---------------------------------------------------------------------------


def test_polygon_geometry_raises_value_error():
    gdf = gpd.GeoDataFrame(
        {"x": [1]},
        geometry=[Polygon([(0, 0), (1, 0), (1, 1)])],
        crs="EPSG:4326",
    )
    with pytest.raises(ValueError, match="Point geometries"):
        normalize_input(gdf, "lat", "lon")


def test_linestring_geometry_raises_value_error():
    gdf = gpd.GeoDataFrame(
        {"x": [1]},
        geometry=[LineString([(0, 0), (1, 1)])],
        crs="EPSG:4326",
    )
    with pytest.raises(ValueError, match="Point geometries"):
        normalize_input(gdf, "lat", "lon")


def test_mixed_point_and_polygon_raises_value_error():
    """Even one non-Point row must reject the whole call — no silent
    partial handling."""
    gdf = gpd.GeoDataFrame(
        {"x": [1, 2]},
        geometry=[Point(1.0, 2.0), Polygon([(0, 0), (1, 0), (1, 1)])],
        crs="EPSG:4326",
    )
    with pytest.raises(ValueError, match="Point geometries"):
        normalize_input(gdf, "lat", "lon")


# ---------------------------------------------------------------------------
# Null / missing geometry — deliberately NOT special-cased
# ---------------------------------------------------------------------------


def test_none_geometry_does_not_raise_and_produces_nan():
    """A None geometry must not trip the points-only check (it's excluded
    via .dropna() before the type check), and must flow through as NaN
    lat/lon — matching whatever the existing plain-DataFrame path already
    does with a NaN coordinate. This is a deliberate non-decision: see
    the module docstring."""
    gdf = gpd.GeoDataFrame(
        {"x": [1, 2]},
        geometry=[Point(1.0, 2.0), None],
        crs="EPSG:4326",
    )
    out = normalize_input(gdf, "lat", "lon")
    assert out["lat"].iloc[0] == 2.0
    assert pd.isna(out["lat"].iloc[1])
    assert pd.isna(out["lon"].iloc[1])


# ---------------------------------------------------------------------------
# Polars rejection (duck-typed — no real polars dependency needed)
# ---------------------------------------------------------------------------


def test_polars_like_object_raises_type_error():
    class FakePolarsDataFrame:
        pass

    FakePolarsDataFrame.__module__ = "polars.dataframe.frame"

    with pytest.raises(TypeError, match="Polars"):
        normalize_input(FakePolarsDataFrame(), "lat", "lon")


def test_real_polars_dataframe_raises_type_error_if_installed():
    polars = pytest.importorskip("polars", reason="polars not installed")
    pdf = polars.DataFrame({"lat": [1.0], "lon": [2.0]})
    with pytest.raises(TypeError, match="Polars"):
        normalize_input(pdf, "lat", "lon")


# ---------------------------------------------------------------------------
# Optional-dependency contract: behaves as passthrough when geopandas
# is "unavailable", even if a GeoDataFrame-shaped object is passed
# ---------------------------------------------------------------------------


def test_passthrough_when_geopandas_marked_unavailable(monkeypatch):
    """If GEOPANDAS_AVAILABLE is False (e.g. geopandas isn't installed
    in some environment), normalize_input must not attempt the
    isinstance check at all and must return input unchanged — this is
    the contract that keeps geopandas an optional, lazy dependency."""
    import streamlit_hexviz._geo_utils as geo_utils

    monkeypatch.setattr(geo_utils, "GEOPANDAS_AVAILABLE", False)

    gdf = gpd.GeoDataFrame({"x": [1]}, geometry=[Point(1.0, 2.0)], crs="EPSG:4326")
    out = geo_utils.normalize_input(gdf, "lat", "lon")
    assert out is gdf  # unchanged — not converted, not flattened
