import streamlit as st
import streamlit_hexviz as shv
import pandas as pd
import numpy as np
import h3

st.title("H3 Viz")

st.write("This is a simple H3 viz app.")

rng = np.random.default_rng(42)

# A few NYC-wide clusters (Manhattan, Brooklyn, Queens, Bronx, Staten Island)
clusters = [
    (40.7831, -73.9712, 0.030, 0.030, 0.30),  # Manhattan
    (40.6782, -73.9442, 0.040, 0.040, 0.30),  # Brooklyn
    (40.7282, -73.7949, 0.045, 0.045, 0.20),  # Queens
    (40.8448, -73.8648, 0.040, 0.040, 0.12),  # Bronx
    (40.5795, -74.1502, 0.030, 0.030, 0.08),  # Staten Island
]

n = 3000
parts: list[pd.DataFrame] = []
for lat0, lon0, lat_std, lon_std, w in clusters:
    ni = int(n * w)
    parts.append(
        pd.DataFrame(
            {
                "lat": rng.normal(lat0, lat_std, ni),
                "lon": rng.normal(lon0, lon_std, ni),
            }
        )
    )

df = pd.concat(parts, ignore_index=True)

shv.h3_map(df, lat="lat", lon="lon", resolution=7, use_sidebar_controls=True)
# shv.h3_heatmap(df, lat="lat", lon="lon", resolution=7, use_sidebar_controls=True)


shv.s2_map(df, lat="lat", lon="lon", level=12, use_sidebar_controls=True)
# shv.s2_heatmap(df, lat="lat", lon="lon", level=12, use_sidebar_controls=True)


np.random.seed(42)

hexes = list(h3.grid_disk(h3.latlng_to_cell(40.7128, -74.0060, 8), 15))
lats, lngs = zip(*[h3.cell_to_latlng(h) for h in hexes])

df = pd.DataFrame(
    {
        "h3_index": hexes,
        "lat": lats,
        "lng": lngs,
        "weight": np.random.exponential(50, len(hexes)),
    }
)

# shv.h3_choropleth(df, h3_col="h3_index", value_col="weight", use_sidebar_controls=True)


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "**streamlit-hexviz** · "
    "[GitHub](https://github.com/Robert-Ziegltrum/streamlit-hexviz) · "
    "[Streamlit Components Gallery](https://streamlit.io/components)"
)
