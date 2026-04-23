"""
Streamlit component wrappers — the user-facing API.

Each function:
  1. Validates inputs
  2. Bins / aggregates data
  3. Applies colour transform
  4. Builds a pydeck layer
  5. Renders via st.pydeck_chart()
  6. Optionally renders sidebar controls

All functions return the aggregated DataFrame so users can inspect it.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st
from typing import Literal

from streamlit_hexviz._h3_utils import (
    h3_df_to_aggregated,
    points_to_h3,
    validate_resolution,
)
from streamlit_hexviz._layers import (
    build_deck,
    h3_hexagon_layer,
    h3_heatmap_layer,
    s2_polygon_layer,
)
from streamlit_hexviz._transforms import COLOUR_SCALES, add_colour_column


# ---------------------------------------------------------------------------
# h3_map  —  points → H3 choropleth
# ---------------------------------------------------------------------------


def h3_map(
    df: pd.DataFrame,
    *,
    lat: str = "lat",
    lon: str = "lon",
    resolution: int = 7,
    weight: str | None = None,
    agg: str = "sum",
    transform: str = "linear",
    colour_scale: str = "viridis",
    alpha: int = 200,
    extruded: bool = False,
    elevation_scale: float = 100.0,
    map_style: str = "dark",
    auto_zoom: bool = True,
    tooltip: str | None = None,
    use_sidebar_controls: bool = True,
    key: str | None = None,
) -> pd.DataFrame:
    """
    Bin lat/lon points into H3 cells and render as a choropleth map.

    Parameters
    ----------
    df                  : DataFrame with coordinate columns
    lat, lon            : coordinate column names
    resolution          : H3 resolution (0-15, default 7 ≈ city-block scale)
    weight              : column to aggregate; None = count points
    agg                 : "sum" | "mean" | "count" | "max" | "min"
    transform           : "linear" | "log" | "quantile"
    colour_scale        : one of viridis, plasma, heat, blues, reds, greens
    alpha               : fill opacity 0-255
    extruded            : 3-D bar chart mode
    elevation_scale     : vertical exaggeration when extruded=True
    map_style           : "dark" | "light" | "road" | "satellite"
    tooltip             : HTML tooltip; placeholders: {value}, {h3_index}
    use_sidebar_controls: inject resolution / colour controls into sidebar
    key                 : Streamlit widget key prefix

    Returns
    -------
    Aggregated DataFrame: h3_index, value, lat, lon, fill_color, geometry
    """
    validate_resolution(resolution)

    if use_sidebar_controls:
        resolution, colour_scale, transform, alpha, extruded = _sidebar_controls(
            resolution=resolution,
            colour_scale=colour_scale,
            transform=transform,
            alpha=alpha,
            extruded=extruded,
            key=key,
        )

    with st.spinner("Binning to H3…"):
        agg_df = points_to_h3(df, lat, lon, resolution, weight, agg)
        agg_df = add_colour_column(agg_df, "value", transform, colour_scale, alpha)

    layer = h3_hexagon_layer(
        agg_df,
        extruded=extruded,
        elevation_scale=elevation_scale if extruded else 1.0,
        elevation_col="value" if extruded else None,
    )

    default_tooltip = tooltip or "<b>H3:</b> {h3_index}<br/><b>Value:</b> {value}"
    deck = build_deck(
        [layer],
        agg_df,
        map_style=map_style,
        auto_zoom=auto_zoom,
        tooltip_html=default_tooltip,
    )
    st.pydeck_chart(deck, key=key)
    _colour_legend(agg_df["value"], colour_scale, transform)
    return agg_df


# ---------------------------------------------------------------------------
# h3_heatmap  —  points → heatmap (continuous density)
# ---------------------------------------------------------------------------


def h3_heatmap(
    df: pd.DataFrame,
    *,
    lat: str = "lat",
    lon: str = "lon",
    resolution: int = 7,
    weight: str | None = None,
    radius_pixels: int = 40,
    map_style: str = "dark",
    auto_zoom: bool = True,
    use_sidebar_controls: bool = True,
    key: str | None = None,
) -> pd.DataFrame:
    """
    Render a continuous heatmap layer binned to H3 centroids.

    Binning to H3 first removes duplicate points and reduces draw calls,
    making this much faster than rendering raw lat/lon clouds.

    Returns
    -------
    Aggregated H3 DataFrame used as heatmap input.
    """
    if use_sidebar_controls:
        resolution = st.sidebar.slider(
            "H3 resolution",
            min_value=3,
            max_value=12,
            value=resolution,
            key=f"{key}_res" if key else None,
        )
        radius_pixels = st.sidebar.slider(
            "Heatmap radius (px)",
            min_value=10,
            max_value=120,
            value=radius_pixels,
            step=5,
            key=f"{key}_rad" if key else None,
        )

    with st.spinner("Building heatmap…"):
        agg_df = points_to_h3(df, lat, lon, resolution, weight, agg="sum")

    layer = h3_heatmap_layer(agg_df, radius_pixels=radius_pixels)
    deck = build_deck([layer], agg_df, map_style=map_style, auto_zoom=auto_zoom)
    st.pydeck_chart(deck, key=key)
    return agg_df


# ---------------------------------------------------------------------------
# h3_choropleth  —  pre-indexed H3 DataFrame → choropleth
# ---------------------------------------------------------------------------


def h3_choropleth(
    df: pd.DataFrame,
    *,
    h3_col: str = "h3_index",
    h3_index_type: Literal["str", "int"] = "str",
    value_col: str = "value",
    agg: str = "sum",
    transform: str = "linear",
    colour_scale: str = "viridis",
    alpha: int = 200,
    extruded: bool = False,
    elevation_scale: float = 100.0,
    map_style: str = "dark",
    auto_zoom: bool = True,
    tooltip: str | None = None,
    use_sidebar_controls: bool = True,
    key: str | None = None,
) -> pd.DataFrame:
    """
    Render a choropleth map from a DataFrame that already has H3 indices.

    Use this when your data is already indexed (e.g. came from a database
    pre-aggregated at H3 resolution).
    """
    if use_sidebar_controls:
        _, colour_scale, transform, alpha, extruded = _sidebar_controls(
            resolution=None,  # no resolution slider — data is pre-indexed
            colour_scale=colour_scale,
            transform=transform,
            alpha=alpha,
            extruded=extruded,
            key=key,
        )

    with st.spinner("Rendering H3 choropleth…"):
        agg_df = h3_df_to_aggregated(
            df, h3_col, value_col, agg, h3_index_type=h3_index_type
        )
        agg_df = add_colour_column(agg_df, "value", transform, colour_scale, alpha)

    default_tooltip = tooltip or f"<b>H3:</b> {{h3_index}}<br/><b>{value_col}:</b> {{value}}"
    layer = h3_hexagon_layer(
        agg_df,
        extruded=extruded,
        elevation_scale=elevation_scale if extruded else 1.0,
        elevation_col="value" if extruded else None,
    )
    deck = build_deck(
        [layer],
        agg_df,
        map_style=map_style,
        auto_zoom=auto_zoom,
        tooltip_html=default_tooltip,
    )
    st.pydeck_chart(deck, key=key)
    _colour_legend(agg_df["value"], colour_scale, transform)
    return agg_df


# ---------------------------------------------------------------------------
# s2_map  —  points → S2 choropleth
# ---------------------------------------------------------------------------


def s2_map(
    df: pd.DataFrame,
    *,
    lat: str = "lat",
    lon: str = "lon",
    level: int = 12,
    weight: str | None = None,
    agg: str = "sum",
    transform: str = "linear",
    colour_scale: str = "plasma",
    alpha: int = 200,
    map_style: str = "dark",
    auto_zoom: bool = True,
    use_sidebar_controls: bool = True,
    key: str | None = None,
) -> pd.DataFrame:
    """
    Bin lat/lon points into S2 cells and render as a choropleth map.

    Requires the optional dependency extra: `pip install "streamlit-hexviz[s2]"`
    """
    from streamlit_hexviz._s2_utils import points_to_s2  # lazy import

    if use_sidebar_controls:
        level = st.sidebar.slider(
            "S2 level",
            min_value=5,
            max_value=18,
            value=level,
            key=f"{key}_s2lvl" if key else None,
        )
        colour_scale = st.sidebar.selectbox(
            "Colour scale",
            list(COLOUR_SCALES),
            index=list(COLOUR_SCALES).index(colour_scale),
            key=f"{key}_cs" if key else None,
        )
        transform = st.sidebar.selectbox(
            "Value transform",
            ["linear", "log", "quantile"],
            key=f"{key}_tr" if key else None,
        )

    with st.spinner("Binning to S2…"):
        agg_df = points_to_s2(df, lat, lon, level, weight, agg)
        agg_df = add_colour_column(agg_df, "value", transform, colour_scale, alpha)

    layer = s2_polygon_layer(agg_df)
    deck = build_deck([layer], agg_df, map_style=map_style, auto_zoom=auto_zoom)
    st.pydeck_chart(deck, key=key)
    _colour_legend(agg_df["value"], colour_scale, transform)
    return agg_df


# ---------------------------------------------------------------------------
# Shared sidebar controls
# ---------------------------------------------------------------------------


def _sidebar_controls(
    *,
    resolution: int | None,
    colour_scale: str,
    transform: str,
    alpha: int,
    extruded: bool,
    key: str | None,
) -> tuple:
    """Render sidebar widgets and return updated values."""
    k = lambda name: f"{key}_{name}" if key else None  # noqa: E731

    if resolution is not None:
        resolution = st.sidebar.slider(
            "H3 resolution",
            min_value=3,
            max_value=12,
            value=resolution,
            help="Higher = smaller cells, more detail, slower rendering",
            key=k("res"),
        )

    colour_scale = st.sidebar.selectbox(
        "Colour scale",
        list(COLOUR_SCALES),
        index=list(COLOUR_SCALES).index(colour_scale),
        key=k("cs"),
    )
    transform = st.sidebar.selectbox(
        "Value transform",
        ["linear", "log", "quantile"],
        index=["linear", "log", "quantile"].index(transform),
        help="log is useful for heavy-tailed distributions",
        key=k("tr"),
    )
    alpha = st.sidebar.slider(
        "Opacity",
        min_value=50,
        max_value=255,
        value=alpha,
        key=k("alpha"),
    )
    extruded = st.sidebar.checkbox(
        "3-D extrusion",
        value=extruded,
        key=k("ext"),
    )
    return resolution, colour_scale, transform, alpha, extruded


# ---------------------------------------------------------------------------
# Inline colour legend
# ---------------------------------------------------------------------------


def _colour_legend(values: pd.Series, colour_scale: str, transform: str) -> None:
    """Render a compact colour-legend below the map."""
    from streamlit_hexviz._transforms import COLOUR_SCALES, apply_transform

    stops = COLOUR_SCALES.get(colour_scale, COLOUR_SCALES["viridis"])
    grad_css = ", ".join(f"rgb{tuple(s)}" for s in stops)
    lo = float(values.min())
    hi = float(values.max())

    st.markdown(
        f"""
<div style="display:flex;align-items:center;gap:10px;font-size:12px;margin-top:4px">
  <span style="white-space:nowrap">{lo:,.1f}</span>
  <div style="flex:1;height:10px;border-radius:4px;
              background:linear-gradient(to right, {grad_css})"></div>
  <span style="white-space:nowrap">{hi:,.1f}</span>
  <span style="color:#888;white-space:nowrap">({transform})</span>
</div>
        """,
        unsafe_allow_html=True,
    )

