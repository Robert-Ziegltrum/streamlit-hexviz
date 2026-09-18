"""
Tests for streamlit_hexviz._geo_utils.

Run directly (no pytest needed for streamlit_hexviz itself, since
_geo_utils.py has no Streamlit import) with:
    pytest tests/test_geo_utils.py -v

Structural note vs. the previous version of this file: only the tests
that actually touch a GeoDataFrame are gated on geopandas being
installed. The plain-DataFrame / auto-detection tests exercise real
logic (lat/lon column resolution) that has nothing to do with
geopandas, so gating the whole file behind a single
`pytest.importorskip("geopandas")` would silently skip that coverage
in any environment without the optional extra installed.
"""

from __future__ import annotations

import sys
import warnings

import pandas as pd
import pytest

from streamlit_hexviz._geo_utils import normalize_input, resolve_lat_lon_columns

try:
    import geopandas as gpd
    from shapely.geometry import LineString, Point, Polygon

    GEOPANDAS_INSTALLED = True
except ImportError:
    GEOPANDAS_INSTALLED = False

geopandas_required = pytest.mark.skipif(
    not GEOPANDAS_INSTALLED, reason="geopandas is an optional dependency"
)


# ---------------------------------------------------------------------------
# Polars rejection — checked first and unconditionally, before any other
# branching (see normalize_input's docstring)
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
# resolve_lat_lon_columns — unit tests for the shared resolver directly
# ---------------------------------------------------------------------------


def test_resolve_explicit_names_used_as_is_when_present():
    df = pd.DataFrame({"y": [1.0], "x": [2.0]})
    assert resolve_lat_lon_columns(df, "y", "x") == ("y", "x")


def test_resolve_explicit_lat_not_in_columns_raises():
    df = pd.DataFrame({"lon": [1.0]})
    with pytest.raises(ValueError, match="not found"):
        resolve_lat_lon_columns(df, "lat", "lon")


@pytest.mark.parametrize(
    "lat_name,lon_name",
    [
        ("lat", "lon"),
        ("latitude", "longitude"),
        ("LAT", "LON"),
        ("LATITUDE", "LONGITUDE"),
    ],
)
def test_resolve_autodetects_st_map_candidate_names(lat_name, lon_name):
    """Must match st.map's own candidate set exactly — same convention,
    no new vocabulary for users coming from st.map."""
    df = pd.DataFrame({lat_name: [1.0], lon_name: [2.0], "other": [0]})
    assert resolve_lat_lon_columns(df, None, None) == (lat_name, lon_name)


def test_resolve_autodetect_raises_when_no_candidate_present():
    df = pd.DataFrame({"foo": [1], "bar": [2]})
    with pytest.raises(ValueError, match="Couldn't find a lat column"):
        resolve_lat_lon_columns(df, None, None)


def test_resolve_autodetect_raises_on_ambiguous_lat_candidates():
    """Deliberate divergence from st.map: st.map silently picks whichever
    candidate its internal set iteration hits first when more than one
    is present. That's an artifact of Python set ordering, not a
    considered design choice — we raise instead."""
    df = pd.DataFrame({"lat": [1.0], "latitude": [1.0], "lon": [2.0]})
    with pytest.raises(ValueError, match="Ambiguous lat column"):
        resolve_lat_lon_columns(df, None, None)


def test_resolve_autodetect_raises_on_ambiguous_lon_candidates():
    df = pd.DataFrame({"lat": [1.0], "lon": [2.0], "LON": [2.0]})
    with pytest.raises(ValueError, match="Ambiguous lon column"):
        resolve_lat_lon_columns(df, None, None)


def test_resolve_explicit_lat_bypasses_ambiguity_lon_still_autodetects():
    """Explicit lat= only disambiguates lat; lon resolution is independent."""
    df = pd.DataFrame({"lat": [1.0], "latitude": [9.0], "lon": [2.0]})
    assert resolve_lat_lon_columns(df, "latitude", None) == ("latitude", "lon")


# ---------------------------------------------------------------------------
# Plain DataFrame — normalize_input's pandas branch
# ---------------------------------------------------------------------------


def test_plain_dataframe_identity_preserved():
    """The returned DataFrame must be the exact same object — zero
    behaviour change to the data itself on the plain-DataFrame path."""
    df = pd.DataFrame({"lat": [1.0], "lon": [2.0]})
    out, lat_col, lon_col = normalize_input(df, "lat", "lon")
    assert out is df
    assert (lat_col, lon_col) == ("lat", "lon")


def test_plain_dataframe_autodetects_when_lat_lon_omitted():
    df = pd.DataFrame({"latitude": [1.0], "longitude": [2.0], "sales": [5]})
    out, lat_col, lon_col = normalize_input(df, None, None)
    assert out is df
    assert (lat_col, lon_col) == ("latitude", "longitude")


def test_plain_dataframe_ambiguous_columns_raises_via_normalize_input():
    df = pd.DataFrame({"lat": [1.0], "latitude": [1.0], "lon": [2.0]})
    with pytest.raises(ValueError, match="Ambiguous"):
        normalize_input(df, None, None)


def test_plain_dataframe_no_candidate_raises_via_normalize_input():
    df = pd.DataFrame({"foo": [1], "bar": [2]})
    with pytest.raises(ValueError, match="Couldn't find"):
        normalize_input(df, None, None)


# ---------------------------------------------------------------------------
# GeoDataFrame — happy path, custom names, custom geometry column
# ---------------------------------------------------------------------------


@geopandas_required
class TestGeoDataFrameHappyPath:
    def test_extracts_lat_lon_from_points_wgs84(self):
        gdf = gpd.GeoDataFrame(
            {"sales": [10, 20]},
            geometry=[Point(10.0, 53.5), Point(9.9, 53.6)],
            crs="EPSG:4326",
        )
        out, lat_col, lon_col = normalize_input(gdf, "lat", "lon")

        assert isinstance(out, pd.DataFrame)
        assert not isinstance(out, gpd.GeoDataFrame)  # geometry column is gone
        assert (lat_col, lon_col) == ("lat", "lon")
        assert list(out["lat"]) == [53.5, 53.6]
        assert list(out["lon"]) == [10.0, 9.9]
        assert "sales" in out.columns
        assert "geometry" not in out.columns

    def test_defaults_target_names_to_latitude_longitude_when_omitted(self):
        """New behaviour: lat=None/lon=None on a GeoDataFrame no longer
        means 'look for a lat/lon column' (there's nothing to
        auto-detect — geometry is the source of truth) — it means
        'write the extracted coordinates to columns named latitude/
        longitude'."""
        gdf = gpd.GeoDataFrame(
            {"sales": [1]}, geometry=[Point(10.0, 53.5)], crs="EPSG:4326"
        )
        out, lat_col, lon_col = normalize_input(gdf, None, None)
        assert (lat_col, lon_col) == ("latitude", "longitude")
        assert out["latitude"].iloc[0] == 53.5
        assert out["longitude"].iloc[0] == 10.0

    def test_respects_custom_lat_lon_param_names(self):
        gdf = gpd.GeoDataFrame(
            {"sales": [1]}, geometry=[Point(10.0, 53.5)], crs="EPSG:4326"
        )
        out, lat_col, lon_col = normalize_input(gdf, "latitude", "longitude")
        assert (lat_col, lon_col) == ("latitude", "longitude")
        assert out["latitude"].iloc[0] == 53.5
        assert out["longitude"].iloc[0] == 10.0

    def test_custom_geometry_column_name(self):
        """The active geometry column isn't always literally named
        'geometry'."""
        gdf = gpd.GeoDataFrame(
            {"sales": [1]}, geometry=[Point(10.0, 53.5)], crs="EPSG:4326"
        )
        gdf = gdf.rename_geometry("geom")
        out, lat_col, lon_col = normalize_input(gdf, "lat", "lon")
        assert "geom" not in out.columns
        assert out["lat"].iloc[0] == 53.5

    def test_geometry_wins_over_unrelated_lat_lon_shaped_columns(self):
        """A GeoDataFrame may carry stale lat/lon-looking columns under
        names that don't collide with the target names. Geometry must
        still be the source of truth for the target columns, and the
        stale columns must be left alone rather than consulted."""
        gdf = gpd.GeoDataFrame(
            {"lat": [999.0], "lon": [999.0]},  # stale, unrelated to geometry
            geometry=[Point(10.0, 53.5)],
            crs="EPSG:4326",
        )
        out, lat_col, lon_col = normalize_input(
            gdf, None, None
        )  # -> latitude/longitude
        assert out["latitude"].iloc[0] == 53.5
        assert out["longitude"].iloc[0] == 10.0
        # stale columns survive untouched, proving they were never read
        assert out["lat"].iloc[0] == 999.0
        assert out["lon"].iloc[0] == 999.0


# ---------------------------------------------------------------------------
# GeoDataFrame — column-name collision (new: fail loud, don't overwrite)
# ---------------------------------------------------------------------------


@geopandas_required
class TestGeoDataFrameCollision:
    def test_explicit_target_colliding_with_existing_column_raises(self):
        gdf = gpd.GeoDataFrame(
            {"lat": [999.0]},  # real, unrelated data under the target name
            geometry=[Point(10.0, 53.5)],
            crs="EPSG:4326",
        )
        with pytest.raises(ValueError, match="already has a column named 'lat'"):
            normalize_input(gdf, "lat", "lon")

    def test_default_target_colliding_with_existing_column_raises(self):
        """Collision detection must apply to the default target names
        too, not just explicitly-passed ones."""
        gdf = gpd.GeoDataFrame(
            {"latitude": [999.0]},
            geometry=[Point(10.0, 53.5)],
            crs="EPSG:4326",
        )
        with pytest.raises(ValueError, match="already has a column named 'latitude'"):
            normalize_input(gdf, None, "lon")

    def test_target_name_matching_geometry_column_itself_does_not_raise(self):
        """Edge case: if the target name happens to equal the geometry
        column's own name, that's not a collision — it's the column
        being replaced, which is exactly what this function does."""
        gdf = gpd.GeoDataFrame(
            {"sales": [1]}, geometry=[Point(10.0, 53.5)], crs="EPSG:4326"
        )
        gdf = gdf.rename_geometry("lat")
        out, lat_col, lon_col = normalize_input(gdf, "lat", "lon")
        assert out["lat"].iloc[0] == 53.5


# ---------------------------------------------------------------------------
# CRS handling
# ---------------------------------------------------------------------------


@geopandas_required
class TestCRSHandling:
    def test_missing_crs_warns_and_assumes_wgs84(self):
        gdf = gpd.GeoDataFrame({"x": [1]}, geometry=[Point(1.0, 2.0)])
        assert gdf.crs is None

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            out, lat_col, lon_col = normalize_input(gdf, "lat", "lon")

        assert any(issubclass(w.category, UserWarning) for w in caught)
        assert any("no CRS" in str(w.message) for w in caught)
        assert out["lon"].iloc[0] == 1.0
        assert out["lat"].iloc[0] == 2.0

    def test_non_wgs84_crs_is_reprojected(self):
        gdf = gpd.GeoDataFrame(
            {"x": [1]}, geometry=[Point(560000, 5930000)], crs="EPSG:32632"
        )
        out, lat_col, lon_col = normalize_input(gdf, "lat", "lon")
        assert out["lat"].iloc[0] == pytest.approx(53.5, abs=0.1)
        assert out["lon"].iloc[0] == pytest.approx(9.9, abs=0.1)

    def test_wgs84_crs_is_not_reprojected_or_warned(self):
        gdf = gpd.GeoDataFrame(
            {"x": [1]}, geometry=[Point(10.0, 53.5)], crs="EPSG:4326"
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            out, lat_col, lon_col = normalize_input(gdf, "lat", "lon")
        assert len(caught) == 0
        assert out["lon"].iloc[0] == 10.0
        assert out["lat"].iloc[0] == 53.5

    def test_missing_crs_warning_stacklevel_points_to_immediate_caller(self):
        """
        Regression test for the stacklevel=4 decision on the missing-CRS
        warning. Real usage is: user code -> h3_map/s2_map/a5_map ->
        normalize_input -> _normalize_geodataframe -> warn (4 frames).
        `_wrapper` below plays the role of h3_map/s2_map/a5_map (it
        calls normalize_input() directly, no extra indirection), and
        this test method plays the role of the end user's own code —
        so stacklevel=4 should attribute the warning to *this test
        method's own call site* (where it calls `_wrapper()`).

        The expected line number is obtained via runtime frame
        introspection (sys._getframe(1).f_lineno from inside `_wrapper`,
        at the moment it's called) rather than assumed from source
        layout. A previous version of this test tried to infer it from
        adjacent source lines and broke the first time a formatter
        reflowed the file — this version doesn't care how the file is
        laid out, only what the interpreter actually did.
        """
        gdf = gpd.GeoDataFrame({"x": [1]}, geometry=[Point(1.0, 2.0)])

        def _wrapper():
            # sys._getframe(1) is the caller of _wrapper (this test
            # method); its f_lineno at this instant is wherever that
            # caller's execution pointer currently sits — i.e. the
            # exact line of the `_wrapper()` call below, however the
            # surrounding code ends up formatted.
            caller_lineno = sys._getframe(1).f_lineno
            normalize_input(gdf, "lat", "lon")
            return caller_lineno

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            expected_lineno = _wrapper()

        assert len(caught) == 1
        w = caught[0]
        assert w.filename == __file__
        assert w.lineno == expected_lineno


# ---------------------------------------------------------------------------
# Points-only scope
# ---------------------------------------------------------------------------


@geopandas_required
class TestPointsOnlyScope:
    def test_polygon_geometry_raises_value_error(self):
        gdf = gpd.GeoDataFrame(
            {"x": [1]},
            geometry=[Polygon([(0, 0), (1, 0), (1, 1)])],
            crs="EPSG:4326",
        )
        with pytest.raises(ValueError, match="Point geometries"):
            normalize_input(gdf, "lat", "lon")

    def test_linestring_geometry_raises_value_error(self):
        gdf = gpd.GeoDataFrame(
            {"x": [1]},
            geometry=[LineString([(0, 0), (1, 1)])],
            crs="EPSG:4326",
        )
        with pytest.raises(ValueError, match="Point geometries"):
            normalize_input(gdf, "lat", "lon")

    def test_mixed_point_and_polygon_raises_value_error(self):
        """Even one non-Point row must reject the whole call — no
        silent partial handling."""
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


@geopandas_required
def test_none_geometry_does_not_raise_and_produces_nan():
    """A None geometry must not trip the points-only check (excluded via
    .dropna() before the type check), and must flow through as NaN
    lat/lon — matching whatever the plain-DataFrame path already does
    with a NaN coordinate. Deliberate non-decision: see the module
    docstring on normalize_input."""
    gdf = gpd.GeoDataFrame(
        {"x": [1, 2]}, geometry=[Point(1.0, 2.0), None], crs="EPSG:4326"
    )
    out, lat_col, lon_col = normalize_input(gdf, "lat", "lon")
    assert out["lat"].iloc[0] == 2.0
    assert pd.isna(out["lat"].iloc[1])
    assert pd.isna(out["lon"].iloc[1])


# ---------------------------------------------------------------------------
# Optional-dependency contract: geopandas branch is only entered when
# GEOPANDAS_AVAILABLE is True — otherwise treated as an opaque
# plain-DataFrame-shaped object
# ---------------------------------------------------------------------------


@geopandas_required
def test_geodataframe_branch_skipped_entirely_when_geopandas_marked_unavailable(
    monkeypatch,
):
    """If GEOPANDAS_AVAILABLE is False (e.g. geopandas isn't installed in
    some environment), normalize_input must not attempt the isinstance
    check at all — a GeoDataFrame-shaped object falls into the plain-
    DataFrame branch instead, geometry is never touched, and whatever
    lat/lon-named columns happen to exist are used as-is."""
    import streamlit_hexviz._geo_utils as geo_utils

    monkeypatch.setattr(geo_utils, "GEOPANDAS_AVAILABLE", False)

    gdf = gpd.GeoDataFrame(
        {"lat": [1.0], "lon": [2.0]},  # plain-DataFrame branch needs these
        geometry=[Point(999.0, 999.0)],  # would win if geometry were consulted
        crs="EPSG:4326",
    )
    out, lat_col, lon_col = geo_utils.normalize_input(gdf, "lat", "lon")
    assert out is gdf  # unchanged — not converted, not flattened
    assert (lat_col, lon_col) == ("lat", "lon")
    assert out["lat"].iloc[0] == 1.0  # not 999.0 — geometry was never consulted
