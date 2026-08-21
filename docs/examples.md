# Examples

Runnable demo apps live in [`examples/`](https://github.com/Robert-Ziegltrum/streamlit-hexviz/tree/main/examples)
in the repo.

## Simple H3 map

[`examples/app_simple.py`](https://github.com/Robert-Ziegltrum/streamlit-hexviz/blob/main/examples/app_simple.py)
bins a few synthetic NYC-wide point clusters (Manhattan, Brooklyn, Queens,
Bronx, Staten Island) into H3 hexagons.

```bash
pip install streamlit h3 pydeck numpy pandas
streamlit run examples/app_simple.py
```

## Full interactive demo

[`examples/demo_app.py`](https://github.com/Robert-Ziegltrum/streamlit-hexviz/blob/main/examples/demo_app.py)
exercises the full sidebar control set (resolution, colour scale, opacity,
3-D extrusion) across grid types.

```bash
pip install "streamlit-hexviz[s2,a5]" h3 pydeck numpy pandas
streamlit run examples/demo_app.py
```

## Earthquakes — A5 grid

[`examples/earthquakes.py`](https://github.com/Robert-Ziegltrum/streamlit-hexviz/blob/main/examples/earthquakes.py)
maps California earthquake data using `a5_map` on raw lat/lon points:

```python
import streamlit_hexviz as shv
import pandas as pd
import streamlit as st

st.write('## Earthquakes in California')

data = pd.read_csv('data/earthquakes.csv')
data = data[data["place"].str.contains("CA", na=False)]

shv.a5_map(df=data, lat='latitude', lon='longitude', use_sidebar_controls=True)
```

## Japan container movements — pre-indexed H3

[`examples/japan_movements.py`](https://github.com/Robert-Ziegltrum/streamlit-hexviz/blob/main/examples/japan_movements.py)
shows `h3_choropleth` with data that's already H3-indexed, rather than raw
coordinates:

```python
import streamlit_hexviz as shv
import pandas as pd
import streamlit as st

data = pd.read_csv('data/japan_movements.csv')
shv.h3_choropleth(data, h3_col='point_res_7',
                   value_col='count', h3_index_type='int')
```

!!! tip
    For this dataset, the `heat` colour scale with a `log` transform brings
    out the distribution best — counts are heavily skewed.
