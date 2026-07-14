import pandas as pd
import pytest


a5 = pytest.importorskip("a5")

# Guard against the PyPI name collision: a bare `import a5` can succeed
# against the unrelated package of the same name, which lacks the
# geospatial API this module needs. Skip cleanly rather than failing with
# a confusing AttributeError.
if not hasattr(a5, "lonlat_to_cell"):
    pytest.skip(
        "Installed `a5` package does not expose the A5 geospatial API "
        "(lonlat_to_cell) — this is likely the unrelated PyPI package of "
        "the same name, not https://a5geo.org's library.",
        allow_module_level=True,
    )


def test_points_to_a5_basic_columns_and_rowcount():
    from streamlit_hexviz._a5_utils import points_to_a5

    df = pd.DataFrame(
        {
            "lat": [40.7128, 40.7129, 40.7130],
            "lon": [-74.0060, -74.0061, -74.0062],
        }
    )

    out = points_to_a5(df, "lat", "lon", resolution=10, weight=None, agg="sum")

    assert {"a5_index", "value", "lat", "lon"}.issubset(out.columns)
    assert len(out) >= 1
    assert out["value"].sum() == pytest.approx(3.0)


def test_a5_df_to_aggregated_accepts_precomputed_index():
    from streamlit_hexviz._a5_utils import a5_df_to_aggregated

    cell = a5.lonlat_to_cell(-74.0, 40.7, 10)
    df = pd.DataFrame({"a5_index": [cell, cell], "metric": [1, 2]})

    out = a5_df_to_aggregated(df, "a5_index", "metric", agg="sum")

    assert out.loc[0, "a5_index"] == cell
    assert out.loc[0, "value"] == 3
    lon, lat = a5.cell_to_lonlat(cell)
    assert out.loc[0, "lon"] == pytest.approx(lon)
    assert out.loc[0, "lat"] == pytest.approx(lat)


def test_validate_resolution_rejects_out_of_range():
    from streamlit_hexviz._a5_utils import validate_resolution

    with pytest.raises(ValueError):
        validate_resolution(-1)
    with pytest.raises(ValueError):
        validate_resolution(31)
    validate_resolution(0)
    validate_resolution(30)
