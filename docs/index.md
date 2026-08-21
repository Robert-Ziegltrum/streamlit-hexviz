# streamlit-hexviz 🗺️

Simple H3, S2, and A5 map visualisations for Streamlit.

[![Demo](https://img.shields.io/badge/demo-live-blue)](https://app-hexviz-example-app.streamlit.app/)
[![PyPI version](https://img.shields.io/pypi/v/streamlit-hexviz)](https://pypi.org/project/streamlit-hexviz/)

```python
import streamlit_hexviz as shv

# One line: bin points → hexagons → colour-coded choropleth
shv.h3_map(df, lat="lat", lon="lon", weight="sales")

# Continuous heatmap
shv.h3_heatmap(df, lat="lat", lon="lon")

# Pre-indexed data (from a DB query)
shv.h3_choropleth(df, h3_col="h3_index", value_col="count")

# S2 grid
shv.s2_map(df, lat="lat", lon="lon", level=12)

# A5 grid (pentagonal cells, optional extra)
shv.a5_map(df, lat="lat", lon="lon", weight="sales")
```

Sidebar controls for resolution, colour scale, opacity, and 3-D extrusion are
injected automatically — no boilerplate required.

## Where to go next

- **[Getting Started](getting-started.md)** — install the package and render your first map.
- **[API Reference](api-reference.md)** — every function, parameter, and default.
- **[Examples](examples.md)** — runnable demo apps shipped in the repo.
- **[Changelog](changelog.md)** — what changed between releases.

## Screenshots

### H3 hexagon choropleth

![H3 hexagon choropleth](https://raw.githubusercontent.com/Robert-Ziegltrum/streamlit-hexviz/main/assets/streamlit-hexexplore-simple-map.png)

### S2 choropleth

![S2 choropleth](https://raw.githubusercontent.com/Robert-Ziegltrum/streamlit-hexviz/main/assets/streamlit-hexexplore-s2-example.png)

### A5 map

![A5 map](https://raw.githubusercontent.com/Robert-Ziegltrum/streamlit-hexviz/main/assets/A5_map.png)
