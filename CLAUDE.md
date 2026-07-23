# streamlit-hexviz

Streamlit component package for H3, S2, and A5 grid map visualisations using PyDeck.
Zero-boilerplate: users plug in a DataFrame and get an interactive map.

## Commands

```bash
# Install in editable mode
pip install -e ".[dev]"

# Run the demo app
streamlit run demo/app.py

# Lint and format
ruff check .
black .

# Run test suite
poetry run pytest

# Build for PyPI
python -m build
```

## Architecture

The package is a thin pipeline:

```
user DataFrame
  → _h3_utils.py / _a5_utils.py   bin points into cell indices, aggregate weights
  → _transforms.py                 normalise values (linear / log / quantile), map to RGB colour
  → _layers.py                     build pydeck.Layer objects (H3HexagonLayer, GeoJsonLayer, HeatmapLayer)
  → _components.py                 call st.pydeck_chart(), inject sidebar controls, render legend
```

Public API lives in `__init__.py` — exported symbols include:
`h3_map`, `h3_heatmap`, `h3_choropleth`, `s2_map`, and `a5_map`.

## Key conventions

- **H3 API is v4** — use `h3.latlng_to_cell`, `h3.cell_to_latlng`, `h3.cell_to_boundary`. The old v3 names (`geo_to_h3`, `h3_to_geo`, `h3_to_geo_boundary`) do not exist.
- **No geometry column needed for H3** — pydeck's `H3HexagonLayer` resolves hex boundaries from `h3_index` strings directly. Never build GeoJSON polygons for H3.
- **S2 and A5 use GeoJsonLayer** with a proper `FeatureCollection` dict — convert cell geometries to GeoJSON features.
- **Basemaps are CARTO** (public style URLs) — no Mapbox token required.
- **Colour scales** live in `_transforms.COLOUR_SCALES` as `{name: [(R,G,B), ...]}` stop lists. Add new ones there.
- **Transforms** live in `_transforms.TRANSFORMS` as `{name: callable}`. Each callable takes a `pd.Series` and returns a normalised `pd.Series` in [0, 1].
- `_layers.py` has **no Streamlit imports** — keep it that way so layers are testable in isolation.
- Every public component function returns the aggregated DataFrame so users can inspect or export it.

## Dependencies

- `streamlit >= 1.28`
- `pydeck >= 0.9.2` — use `H3HexagonLayer` for H3, `HeatmapLayer` for density, `GeoJsonLayer` for S2 & A5
- `h3 >= 4.0`
- `pandas`, `numpy`
- **Optional backends** (lazy-imported only inside their respective component functions):
  - S2 backend (`s2geometry`)
  - A5 backend (`a5`)

## Roadmap / open TODOs

- Vectorise the Python `for` loops in `_h3_utils.points_to_h3` and `_a5_utils` (currently slow for >50k points)
- Multi-layer support (H3 / A5 + point overlay in one map)
- Time-slider animation over a datetime column
- GeoDataFrame input support
- `st.download_button` for aggregated data export
