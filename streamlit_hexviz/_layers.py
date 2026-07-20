"""
PyDeck layer builders.

Each function returns a pydeck.Layer ready to add to a pydeck.Deck.
"""
from __future__ import annotations

import math

import pandas as pd
import pydeck as pdk


def h3_hexagon_layer(
    df: pd.DataFrame,
    *,
    elevation_col: str | None = "value",
    elevation_scale: float = 1.0,
    pickable: bool = True,
    extruded: bool = False,
    opacity: float = 0.8,
) -> pdk.Layer:
    """
    Render H3 cells using pydeck's native H3HexagonLayer.
    Expects columns: h3_index (str), fill_color ([R,G,B,A]), value (number).
    No geometry conversion needed — pydeck resolves h3_index internally.
    """
    return pdk.Layer(
        "H3HexagonLayer",
        df,
        get_hexagon="h3_index",
        get_fill_color="fill_color",
        # If not extruded (or caller explicitly disables elevation), keep elevations flat.
        get_elevation=elevation_col if (extruded and elevation_col) else 0,
        elevation_scale=elevation_scale,
        extruded=extruded,
        pickable=pickable,
        opacity=opacity,
        stroked=True,
        filled=True,
        auto_highlight=True,
        coverage=1,
    )


def a5_pentagon_layer(
    df: pd.DataFrame,
    *,
    elevation_col: str | None = "value",
    elevation_scale: float = 1.0,
    pickable: bool = True,
    extruded: bool = False,
    opacity: float = 0.8,
) -> pdk.Layer:
    """
    Render A5 cells using pydeck's native A5Layer.
    Expects columns: a5_index, fill_color ([R,G,B,A]), value (number).
    No geometry conversion needed — pydeck resolves a5_index internally,
    mirroring h3_hexagon_layer's use of H3HexagonLayer.

    Requires pydeck>=0.9.2 (first version confirmed to document A5Layer).
    """
    return pdk.Layer(
        "A5Layer",
        df,
        get_pentagon="a5_index",
        get_fill_color="fill_color",
        get_elevation=elevation_col if (extruded and elevation_col) else 0,
        elevation_scale=elevation_scale,
        extruded=extruded,
        pickable=pickable,
        opacity=opacity,
        stroked=True,
        filled=True,
        auto_highlight=True,
    )


def h3_heatmap_layer(
    df: pd.DataFrame,
    *,
    weight_col: str = "value",
    radius_pixels: int = 40,
    opacity: float = 0.8,
    color_range: list[list[int]] | None = None,
) -> pdk.Layer:
    """
    Render a HeatmapLayer using H3 cell centroids as point cloud.
    Expects columns: lon, lat, value.
    """
    if color_range is None:
        color_range = [
            [1, 152, 189],
            [73, 227, 206],
            [216, 254, 181],
            [254, 237, 177],
            [254, 173, 84],
            [209, 55, 78],
        ]
    return pdk.Layer(
        "HeatmapLayer",
        df,
        get_position=["lon", "lat"],
        get_weight=weight_col,
        radius_pixels=radius_pixels,
        opacity=opacity,
        color_range=color_range,
        aggregation="SUM",
    )


def s2_polygon_layer(
    df: pd.DataFrame,
    *,
    pickable: bool = True,
    extruded: bool = False,
    opacity: float = 0.8,
) -> pdk.Layer:
    """
    Render S2 cells as a GeoJsonLayer (S2 has no native pydeck layer).
    Converts DataFrame rows to a proper GeoJSON FeatureCollection.
    """
    features = [
        {
            "type": "Feature",
            "geometry": row["geometry"],
            "properties": {
                "value": row["value"],
                "fill_color": row["fill_color"],
            },
        }
        for _, row in df.iterrows()
    ]
    geojson = {"type": "FeatureCollection", "features": features}
    return pdk.Layer(
        "GeoJsonLayer",
        geojson,
        get_fill_color="properties.fill_color",
        get_line_color=[60, 60, 60, 80],
        line_width_min_pixels=1,
        pickable=pickable,
        opacity=opacity,
        extruded=extruded,
        stroked=True,
        filled=True,
        auto_highlight=True,
    )


def build_deck(
    layers: list[pdk.Layer],
    df: pd.DataFrame,
    *,
    map_style: str = "dark",
    initial_zoom: int = 4,
    auto_zoom: bool = True,
    tooltip_html: str | None = None,
) -> pdk.Deck:
    """
    Assemble a pydeck.Deck centred on the data's centroid.
    Uses CARTO basemaps — free, no Mapbox token required.
    """
    lat_center = float(df["lat"].mean())
    lon_center = float(df["lon"].mean())

    is_extruded = any(getattr(l, "extruded", False) for l in layers)

    zoom = float(initial_zoom)
    if auto_zoom:
        lat_span = float(df["lat"].max() - df["lat"].min())
        lon_span = float(df["lon"].max() - df["lon"].min())

        # Heuristic "fit bounds" for WebMercator zoom.
        # Avoid extreme zoom for tiny spans and handle degenerate cases.
        eps = 1e-9
        lat_span = max(lat_span, eps)
        lon_span = max(lon_span, eps)

        # Add a bit of padding so points aren't glued to the edges.
        pad = 1.25
        zoom_lon = math.log2(360.0 / (lon_span * pad))
        # ~lat range for mercator
        zoom_lat = math.log2(170.0 / (lat_span * pad))
        zoom = min(zoom_lon, zoom_lat)
        zoom = float(max(0.0, min(16.0, zoom)))

    view_state = pdk.ViewState(
        latitude=lat_center,
        longitude=lon_center,
        zoom=zoom,
        pitch=45 if is_extruded else 0,
        bearing=0,
    )

    tooltip = {"html": tooltip_html, "style": {
        "color": "white"}} if tooltip_html else None

    return pdk.Deck(
        layers=layers,
        initial_view_state=view_state,
        # Use public CARTO basemap styles (no Mapbox token needed).
        # Providing a full style URL avoids relying on pydeck's provider aliases,
        # which can vary by pydeck/version.
        map_style={
            "dark": "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
            "light": "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
            "road": "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
            "satellite": "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
        }.get(map_style, map_style),
        tooltip=tooltip,
    )
