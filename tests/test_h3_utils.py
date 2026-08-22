import pandas as pd
import pytest


pytest.importorskip("h3")


def test_points_to_h3_basic_columns_and_rowcount():
    from streamlit_hexviz._h3_utils import points_to_h3

    df = pd.DataFrame(
        {
            "lat": [40.7128, 40.7129, 40.7130],
            "lon": [-74.0060, -74.0061, -74.0062],
        }
    )

    out = points_to_h3(df, "lat", "lon", resolution=7, weight=None, agg="sum")

    assert {"h3_index", "value", "lat", "lon"}.issubset(out.columns)
    assert len(out) >= 1
    assert out["value"].sum() == pytest.approx(3.0)


def test_h3_df_to_aggregated_accepts_string_tokens():
    import h3

    from streamlit_hexviz._h3_utils import h3_df_to_aggregated

    token = h3.latlng_to_cell(40.7, -74.0, 7)
    df = pd.DataFrame({"h3_index": [token, token], "metric": [1, 2]})

    out = h3_df_to_aggregated(df, "h3_index", "metric", agg="sum", h3_index_type="str")

    assert out.loc[0, "h3_index"] == token
    assert out.loc[0, "value"] == 3
    assert out.loc[0, "lat"] == pytest.approx(h3.cell_to_latlng(token)[0])
    assert out.loc[0, "lon"] == pytest.approx(h3.cell_to_latlng(token)[1])


def test_h3_df_to_aggregated_accepts_int_ids_and_coerces_to_string_token():
    import h3

    from streamlit_hexviz._h3_utils import h3_df_to_aggregated

    token = h3.latlng_to_cell(40.7, -74.0, 7)
    cell_int = h3.str_to_int(token)
    df = pd.DataFrame({"h3_bigint": [cell_int, cell_int], "metric": [1, 2]})

    out = h3_df_to_aggregated(df, "h3_bigint", "metric", agg="sum", h3_index_type="int")

    assert out.loc[0, "h3_index"] == token
    assert out.loc[0, "value"] == 3
