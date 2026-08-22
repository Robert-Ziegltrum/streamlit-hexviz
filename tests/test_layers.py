import pandas as pd


def test_h3_hexagon_layer_elevation_disabled_when_not_extruded():
    from streamlit_hexviz._layers import h3_hexagon_layer

    df = pd.DataFrame(
        {
            "h3_index": ["872a1072dffffff"],
            "fill_color": [[255, 0, 0, 200]],
            "value": [123],
        }
    )

    layer = h3_hexagon_layer(df, extruded=False, elevation_col="value")
    # When not extruded, we force elevation to 0.
    assert layer.get_elevation == 0


def test_build_deck_auto_zoom_produces_reasonable_zoom():
    import pydeck as pdk

    from streamlit_hexviz._layers import build_deck

    # NYC-ish bounding box
    df = pd.DataFrame(
        {
            "lat": [40.55, 40.92],
            "lon": [-74.25, -73.70],
        }
    )

    deck = build_deck(
        [pdk.Layer("ScatterplotLayer", df, get_position=["lon", "lat"])],
        df,
        auto_zoom=True,
    )

    zoom = float(deck.initial_view_state.zoom)
    assert 0.0 <= zoom <= 16.0
    # NYC span should land in a city-ish zoom range.
    assert zoom >= 7.0
