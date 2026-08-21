# Getting Started

## Installation

```bash
pip install streamlit-hexviz

# S2 grid support (optional)
pip install "streamlit-hexviz[s2]"

# A5 grid support (optional)
pip install "streamlit-hexviz[a5]"

# Both optional extras
pip install "streamlit-hexviz[s2,a5]"
```

Requires Python 3.10+ and Streamlit 1.40+.

## Your first map

```python
import streamlit as st
import streamlit_hexviz as shv
import pandas as pd

st.title("H3 Viz")

df = pd.DataFrame({
    "lat": [40.7128, 40.7328, 40.6928],
    "lon": [-74.0060, -74.0260, -73.9860],
    "sales": [120, 80, 45],
})

shv.h3_map(df, lat="lat", lon="lon", weight="sales")
```

Run it with:

```bash
streamlit run app.py
```

A resolution slider, colour scale picker, opacity control, and 3-D extrusion
toggle are added to the sidebar automatically (set `use_sidebar_controls=False`
to disable this).

## Choosing a grid system

| Grid | Function | When to use |
|---|---|---|
| H3 | `h3_map`, `h3_heatmap`, `h3_choropleth` | Default choice — hexagonal cells, mature tooling ecosystem |
| S2 | `s2_map` | Google's S2 cell hierarchy, quad-tree based |
| A5 | `a5_map`, `a5_choropleth` | Pentagonal cells with more uniform area across the globe |

See the [API Reference](api-reference.md) for full parameter details on each.

## Next steps

- Browse the [Examples](examples.md) for runnable demo apps included in the repo.
- Check the [API Reference](api-reference.md) for every parameter and default.
