# streamlit-hexviz

Streamlit component package for H3, S2, and A5 grid map visualisations using PyDeck.
Zero-boilerplate: users plug in a DataFrame (or a Point GeoDataFrame) and get an
interactive map.

## Commands

```
# Install in editable mode
pip install -e ".[dev]"

# Run the demo app
streamlit run demo/app.py

# Lint and format
ruff check .
black .

# Run test suite
pytest

# Build for PyPI
python -m build
```

## Architecture

The package is a thin pipeline:

```
user DataFrame or Point GeoDataFrame
  → _geo_utils.py                   normalize_input(): GeoDataFrame → plain DataFrame
                                     with lat/lon columns; no-op for plain DataFrames
                                    automatically detect lat lon columns
  → _h3_utils.py / _a5_utils.py / _s2_utils.py
                                     bin points into cell indices, aggregate weights
  → _transforms.py                  normalise values (linear / log / quantile), map to RGB colour
  → _layers.py                      build pydeck.Layer objects
  → _components.py                  call st.pydeck_chart(), inject sidebar controls, render legend
```

Public API lives in `__init__.py` — the six component functions:
`h3_map`, `h3_heatmap`, `h3_choropleth`, `s2_map`, `a5_map`, `a5_choropleth`.

`normalize_input()` is only called by the four **raw-point** functions
(`h3_map`, `h3_heatmap`, `s2_map`, `a5_map`) — never by `h3_choropleth`/
`a5_choropleth`, which take data that's already aggregated to a cell-id +
value column and has no lat/lon concept for a Point geometry to map onto.


## Design principle
New API surface should require no new mental model — mirror the exact
conventions users already know from `st.plotly_chart`/`st.dataframe` (e.g.
selection access patterns). A custom wrapper type or vocabulary is a design
smell; prefer passing through native Streamlit/pydeck objects.

## Key conventions

- **H3 API is v4** — use `h3.latlng_to_cell`, `h3.cell_to_latlng`,
  `h3.cell_to_boundary`. The old v3 names (`geo_to_h3`, `h3_to_geo`,
  `h3_to_geo_boundary`) do not exist.
- **No geometry column needed for H3** — pydeck's `H3HexagonLayer` resolves hex
  boundaries from `h3_index` strings directly. Never build GeoJSON polygons for H3.
- **A5 renders via `PolygonLayer`, not pydeck's native `A5Layer`.** Streamlit
  bundles a fixed deck.gl build whose registered-layer whitelist doesn't include
  `A5Layer` yet (confirmed via browser console: "No registered class of type
  A5Layer"), even though the Python-side spec builds fine and works via pydeck's
  standalone `.to_html()`. Pentagon boundaries are computed in Python via
  `a5.cell_to_boundary()` and attached as a `polygon` column instead. See
  `_layers.a5_pentagon_layer()`.
- **S2 uses `GeoJsonLayer`** with a proper `FeatureCollection` dict — S2 has no
  native pydeck layer, and no Streamlit whitelist workaround is needed since
  `GeoJsonLayer` is already supported.
- **Basemaps are CARTO** (public style URLs) — no Mapbox token required.
- **Colour scales** live in `_transforms.COLOUR_SCALES` as `{name: [(R,G,B), ...]}`
  stop lists. Add new ones there.
- **Transforms** live in `_transforms.TRANSFORMS` as `{name: callable}`. Each
  callable takes a `pd.Series` and returns a normalised `pd.Series` in [0, 1].
- `_layers.py` has **no Streamlit imports** — keep it that way so layers are
  testable in isolation. `_geo_utils.py` has no Streamlit *or* pydeck imports
  either, for the same reason.
- Every public component function returns the aggregated DataFrame so users can
  inspect or export it.
- **Parameter naming is load-bearing, not cosmetic.** The raw-point functions
  (`h3_map`/`s2_map`/`a5_map`/`h3_heatmap`) take `weight` for the column to
  aggregate. The separate pre-indexed functions (`h3_choropleth`/
  `a5_choropleth`) take `value_col` instead. Any new input path (GeoDataFrame
  support was the first case of this) must reuse whichever of the two it's
  actually extending — inventing a third name (e.g. `value_column`) silently
  forks the API.

## GeoPandas input support (`_geo_utils.normalize_input`)

Point GeoDataFrames are accepted by the four raw-point functions in place of a
plain DataFrame + `lat`/`lon` column names. Scope and decisions, tested in
`tests/test_geo_utils.py`:

- **Points only.** Any other geometry type (or a mix including even one
  non-Point row) raises `ValueError` rather than silently falling back to a
  centroid. Polygon-to-hex conversion is a distinct, unbuilt feature — see
  Roadmap below.
- **Missing CRS** emits a `UserWarning` and assumes EPSG:4326 (WGS84).
- **Non-WGS84 CRS** is reprojected automatically via `.to_crs(epsg=4326)`.
- **Polars DataFrames are explicitly rejected** with a clear `TypeError`
  pointing at `.to_pandas()`, via a duck-typed module-name check (no polars
  import needed just to detect and reject it). This was a deliberate scope
  decision, not an oversight — Polars input support was considered and
  dropped: no concrete user demand, and it would have added a second input
  format to maintain for functions where the underlying binning logic gains
  nothing from Polars specifically (it's converted to pandas either way).
- **Null/missing geometry is deliberately NOT special-cased.** A `None`
  geometry flows through as `NaN` lat/lon, matching whatever the existing
  plain-DataFrame path already does with a `NaN` coordinate (no `dropna`
  today) — so both input paths fail or behave identically instead of one
  silently dropping rows and the other raising deep inside h3-py/a5/s2sphere.
  Revisit both together if/when the plain-DataFrame path gets explicit
  handling.
- `geopandas` is a **lazy, optional import** (`GEOPANDAS_AVAILABLE` flag),
  matching the existing pattern for the S2 and A5 backends — the rest of the
  package has no hard dependency on it.

## Dependencies

- `streamlit >= 1.28`
- `pydeck >= 0.9.2` — use `H3HexagonLayer` for H3, `HeatmapLayer` for density,
  `PolygonLayer` for A5, `GeoJsonLayer` for S2
- `h3 >= 4.0`
- `pandas`, `numpy`
- **Optional backends** (lazy-imported only inside their respective component
  functions or `_geo_utils.py`):
  * S2 backend (`s2sphere`)
  * A5 backend (`a5` / `pya5`)
  * GeoPandas input support (`geopandas`) — direction under discussion is to
    eventually make this a hard dependency rather than an extra, since the
    target user base is geospatial practitioners who likely have it installed
    already; not decided yet, currently lazy-imported like S2/A5.
- **Explicitly not supported**: Polars DataFrame input (see above).

## Technical decisions

- Aggregated data is returned by
`h3_map`, `h3_heatmap`, `h3_choropleth`, `s2_map`, `a5_map`, `a5_choropleth`. `st.download_button` as part of user customization.
- optional dependency on `geopandas` as feature enables existing `geopandas` for a simple easy to use streamlit integration.

## Roadmap / open TODOs

- s2_cloropleth to be build
- Vectorise the Python `for` loops in `_h3_utils.points_to_h3` and
  `_a5_utils.points_to_a5` (currently slow for >50k points)
- Multi-layer support (H3 / A5 + point overlay in one map)
- Time-slider animation over a datetime column
- Polygon-to-hex conversion for GeoDataFrame input (needs shapely geometry
  ops — containment/overlap/area-weighted aggregation; no Polars equivalent
  path, so this stays GeoDataFrame-only even if Polars input is reconsidered
  later)
- Revisit bidirectional map selection once the open questions above have
  answers
- Grid comparison feature (toggle-only, not side-by-side — combining a toggle map with a stats table: area uniformity, neighbor/edge behavior, indexing performance)
- Cell inspector / detail panel
- Colorblind-safe palette defaults
- Large-data/performance path for pre-aggregated binning
