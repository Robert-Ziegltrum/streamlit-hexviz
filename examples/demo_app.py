"""
streamlit_hexviz  ·  demo app
=============================
Run with:  streamlit run demo/app.py
"""

import numpy as np
import pandas as pd
import streamlit as st

import streamlit_hexviz as shv

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="streamlit-hexviz demo",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ streamlit-hexviz")
st.caption("Dead-simple H3, S2 and A5 map visualisations for Streamlit.")

# ── Sidebar: dataset chooser ──────────────────────────────────────────────────
st.sidebar.header("Dataset")
dataset = st.sidebar.selectbox(
    "Sample dataset",
    ["NYC taxi pickups", "London bike hires", "Random global points"],
)
n_points = st.sidebar.slider("Number of points", 500, 50_000, 5_000, step=500)

st.sidebar.divider()
st.sidebar.header("Visualisation")
viz_type = st.sidebar.radio(
    "Map type",
    ["H3 choropleth", "H3 heatmap", "H3 3-D extrusion",
        "Pre-indexed H3", "S2 choropleth", "A5 map"],
)

st.sidebar.divider()
# (remaining controls injected by the component itself)


# ── Synthetic data generators ─────────────────────────────────────────────────
@st.cache_data
def make_nyc(n: int) -> pd.DataFrame:
    """Simulate NYC taxi pickup density (Manhattan / Brooklyn cluster)."""
    rng = np.random.default_rng(42)
    lats = rng.normal(40.73, 0.06, n)
    lons = rng.normal(-73.99, 0.07, n)
    fare = rng.exponential(12, n) + rng.uniform(3, 8, n)
    return pd.DataFrame({"lat": lats, "lon": lons, "fare": fare})


@st.cache_data
def make_london(n: int) -> pd.DataFrame:
    """Simulate London bike hire density."""
    rng = np.random.default_rng(7)
    lats = rng.normal(51.505, 0.04, n)
    lons = rng.normal(-0.12, 0.05, n)
    duration = rng.exponential(1200, n)
    return pd.DataFrame({"lat": lats, "lon": lons, "duration_s": duration})


@st.cache_data
def make_global(n: int) -> pd.DataFrame:
    """Random global points weighted by rough population density."""
    rng = np.random.default_rng(99)
    clusters = [
        dict(lat=40.7, lon=-74.0, std=2.0, w=1.0),   # North America
        dict(lat=51.5, lon=-0.1,  std=1.5, w=0.8),   # Europe
        dict(lat=35.7, lon=139.7, std=1.5, w=1.2),   # East Asia
        dict(lat=28.6, lon=77.2,  std=2.0, w=1.1),   # South Asia
        dict(lat=-23.5, lon=-46.6, std=1.5, w=0.7),  # South America
    ]
    dfs = []
    for c in clusters:
        ni = int(n * c["w"] / sum(x["w"] for x in clusters))
        dfs.append(pd.DataFrame({
            "lat": rng.normal(c["lat"], c["std"], ni),
            "lon": rng.normal(c["lon"], c["std"], ni),
            "weight": rng.exponential(c["w"], ni),
        }))
    return pd.concat(dfs, ignore_index=True)


DATASETS = {
    "NYC taxi pickups": (make_nyc, "fare"),
    "London bike hires": (make_london, "duration_s"),
    "Random global points": (make_global, "weight"),
}

factory, weight_col = DATASETS[dataset]
df = factory(n_points)

# ── Dataset preview ───────────────────────────────────────────────────────────
with st.expander("Preview raw data", expanded=False):
    st.dataframe(df.head(200), use_container_width=True)
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", f"{len(df):,}")
    c2.metric("Lat range", f"{df['lat'].min():.2f} → {df['lat'].max():.2f}")
    c3.metric(f"Weight ({weight_col}) mean", f"{df[weight_col].mean():.2f}")

st.divider()

# ── Map ───────────────────────────────────────────────────────────────────────
if viz_type == "H3 choropleth":
    st.subheader("H3 choropleth")
    st.caption(
        "Points binned into H3 hexagons. Cell colour encodes aggregated weight."
    )
    agg = shv.h3_map(
        df,
        lat="lat",
        lon="lon",
        weight=weight_col,
        agg="sum",
        key="h3map",
    )

elif viz_type == "H3 heatmap":
    st.subheader("H3 heatmap")
    st.caption(
        "Continuous density heatmap. H3 binning pre-aggregates the point cloud "
        "for fast rendering — even at 50k points."
    )
    shv.h3_heatmap(
        df,
        lat="lat",
        lon="lon",
        weight=weight_col,
        key="h3heat",
    )

elif viz_type == "H3 3-D extrusion":
    st.subheader("H3 3-D extrusion")
    st.caption("Hexagonal prisms — height encodes value. Drag to tilt.")
    shv.h3_map(
        df,
        lat="lat",
        lon="lon",
        weight=weight_col,
        agg="sum",
        extruded=True,
        elevation_scale=200.0,
        map_style="dark",
        key="h3ext",
    )

elif viz_type == "Pre-indexed H3":
    st.subheader("Pre-indexed H3 choropleth")
    st.caption(
        "Use `shv.h3_choropleth()` when your DataFrame already has an H3 index "
        "column (e.g. from a database query)."
    )
    # Simulate pre-indexed data
    import h3 as _h3
    resolution = 7
    df["h3_index"] = [_h3.latlng_to_cell(
        r.lat, r.lon, resolution) for r in df.itertuples()]
    pre_indexed = (
        df.groupby("h3_index")[weight_col]
        .sum()
        .reset_index()
        .rename(columns={weight_col: "metric"})
    )
    st.caption(
        f"Pre-indexed DataFrame: {len(pre_indexed):,} H3 cells at resolution {resolution}")
    shv.h3_choropleth(
        pre_indexed,
        h3_col="h3_index",
        value_col="metric",
        key="h3choro",
    )

elif viz_type == "S2 choropleth":
    st.subheader("S2 choropleth")
    try:
        shv.s2_map(
            df,
            lat="lat",
            lon="lon",
            weight=weight_col,
            key="s2map",
        )
    except ImportError as e:
        st.warning(
            f"S2 support not installed: {e}\n\n"
            "Install with: `pip install \"streamlit-hexviz[s2]\"`"
        )
elif viz_type == "A5 map":
    st.subheader("A5 map")
    shv.a5_map(
        df,
        lat="lat",
        lon="lon",
        weight=weight_col,
        key='A5 map'
    )


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "**streamlit-hexviz** · "
    "[GitHub](https://github.com/Robert-Ziegltrum/streamlit-hexviz) · "
    "[Streamlit Components Gallery](https://streamlit.io/components)"
)
