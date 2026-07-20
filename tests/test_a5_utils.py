import pandas as pd
import pytest


a5 = pytest.importorskip("a5")


def test_points_to_a5_basic_columns_and_rowcount():
    from streamlit_hexviz._a5_utils import points_to_a5

    df = pd.DataFrame(
        {
            "lat": [40.7128, 40.7129, 40.7130],
            "lon": [-74.0060, -74.0061, -74.0062],
        }
    )

    out = points_to_a5(df, "lat", "lon", resolution=11, weight=None, agg="sum")

    assert {"a5_index", "value", "lat", "lon"}.issubset(out.columns)
    assert len(out) >= 1
    assert out["value"].sum() == pytest.approx(3.0)
    # a5_index is stored as a hex string, not a raw 64-bit int (which
    # exceeds JS's safe integer range and risks precision loss in pydeck's
    # JSON serialisation to the browser).
    assert isinstance(out.loc[0, "a5_index"], str)


def test_a5_df_to_aggregated_accepts_hex_tokens():
    from streamlit_hexviz._a5_utils import a5_df_to_aggregated

    cell = a5.lonlat_to_cell((-74.0, 40.7), 11)
    token = a5.u64_to_hex(cell)
    df = pd.DataFrame({"a5_index": [token, token], "metric": [1, 2]})

    out = a5_df_to_aggregated(df, "a5_index", "metric",
                              agg="sum", a5_index_type="hex")

    assert out.loc[0, "a5_index"] == token
    assert out.loc[0, "value"] == 3
    lon, lat = a5.cell_to_lonlat(cell)
    assert out.loc[0, "lon"] == pytest.approx(lon)
    assert out.loc[0, "lat"] == pytest.approx(lat)


def test_a5_df_to_aggregated_accepts_int_ids_and_coerces_to_hex():
    from streamlit_hexviz._a5_utils import a5_df_to_aggregated

    cell = a5.lonlat_to_cell((-74.0, 40.7), 11)
    token = a5.u64_to_hex(cell)
    df = pd.DataFrame({"a5_bigint": [cell, cell], "metric": [1, 2]})

    out = a5_df_to_aggregated(
        df, "a5_bigint", "metric", agg="sum", a5_index_type="int")

    assert out.loc[0, "a5_index"] == token
    assert out.loc[0, "value"] == 3


def test_validate_resolution_rejects_out_of_range():
    from streamlit_hexviz._a5_utils import validate_resolution

    with pytest.raises(ValueError):
        validate_resolution(-1)
    with pytest.raises(ValueError):
        validate_resolution(31)
    validate_resolution(0)
    validate_resolution(30)
