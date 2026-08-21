# API Reference

All functions are available from the top-level namespace:

```python
import streamlit_hexviz as shv
```

---

## `shv.h3_map(df, ...)`

Choropleth from raw lat/lon points, binned into H3 hexagons.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `df` | DataFrame | required | Input data with coordinate columns |
| `lat`, `lon` | str | `"lat"`, `"lon"` | Coordinate column names |
| `resolution` | int | 7 | H3 resolution (0-15) |
| `weight` | str \| None | None | Column to aggregate; `None` = count points |
| `agg` | str | `"sum"` | `"sum"`, `"mean"`, `"count"`, `"max"`, `"min"` |
| `transform` | str | `"linear"` | `"linear"`, `"log"`, `"quantile"` |
| `colour_scale` | str | `"viridis"` | `viridis`, `plasma`, `heat`, `blues`, `reds`, `greens` |
| `alpha` | int | 200 | Fill opacity 0-255 |
| `extruded` | bool | False | 3-D bar chart mode |
| `elevation_scale` | float | 100 | Vertical exaggeration (extruded only) |
| `map_style` | str | `"dark"` | `"dark"`, `"light"`, `"road"`, `"satellite"` |
| `tooltip` | str \| None | None | HTML tooltip; use `{value}`, `{h3_index}` |
| `use_sidebar_controls` | bool | True | Inject resolution/colour controls into sidebar |
| `key` | str \| None | None | Streamlit widget key prefix |

**Returns:** aggregated DataFrame with columns `h3_index`, `value`, `lat`, `lon`, `fill_color`, `geometry`.

!!! warning "Known issue"
    Using two `h3_map()` calls on the same page can hit a widget key
    collision. Pass an explicit, unique `key` to each call until this is
    resolved (tracked as [Issue #1](https://github.com/Robert-Ziegltrum/streamlit-hexviz/issues/1)).

---

## `shv.h3_heatmap(df, ...)`

Continuous density heatmap. Accepts the same coordinate params as `h3_map`,
plus:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `radius_pixels` | int | 40 | Heatmap point radius in pixels |

---

## `shv.h3_choropleth(df, ...)`

For data that's already H3-indexed (e.g. from a warehouse query).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `h3_col` | str | `"h3_index"` | Column containing H3 cell tokens |
| `value_col` | str | `"value"` | Column to visualise |

---

## `shv.s2_map(df, ...)`

*Requires the optional extra: `pip install "streamlit-hexviz[s2]"`*

Same interface as `h3_map`, but uses `level` (0-30) instead of `resolution`.

---

## `shv.a5_map(df, ...)`

*Requires the optional extra: `pip install "streamlit-hexviz[a5]"`*

Bins points into pentagonal [A5](https://a5geo.org) cells.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `df` | DataFrame | required | Input data with coordinate columns |
| `lat`, `lon` | str | `"lat"`, `"lon"` | Coordinate column names |
| `resolution` | int | 11 | A5 resolution (0-30) |
| `weight` | str \| None | None | Column to aggregate; `None` = count points |
| `agg` | str | `"sum"` | `"sum"`, `"mean"`, `"count"`, `"max"`, `"min"` |
| `transform` | str | `"linear"` | `"linear"`, `"log"`, `"quantile"` |
| `colour_scale` | str | `"viridis"` | `viridis`, `plasma`, `heat`, `blues`, `reds`, `greens` |
| `alpha` | int | 200 | Fill opacity 0-255 |
| `extruded` | bool | False | 3-D bar chart mode |
| `elevation_scale` | float | 100 | Vertical exaggeration (extruded only) |
| `map_style` | str | `"dark"` | `"dark"`, `"light"`, `"road"`, `"satellite"` |
| `tooltip` | str \| None | None | HTML tooltip; use `{value}`, `{a5_index}` |
| `use_sidebar_controls` | bool | True | Inject resolution/colour controls into sidebar |
| `key` | str \| None | None | Streamlit widget key prefix |

**Returns:** aggregated DataFrame with columns `a5_index`, `value`, `lat`, `lon`, `fill_color`.

---

## `shv.a5_choropleth(df, ...)`

For pre-indexed A5 data.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `a5_col` | str | `"a5_index"` | Column containing A5 cell IDs |
| `a5_index_type` | str | `"hex"` | `"hex"` (hex string tokens) or `"int"` (raw 64-bit ints) |
| `value_col` | str | `"value"` | Column to visualise |

!!! note
    A5 cell IDs are 64-bit integers, which exceed JavaScript's safe integer
    range. `a5_map` / `a5_choropleth` always store and pass `a5_index` as a
    hex string internally (via `a5.u64_to_hex`) to avoid precision loss when
    pydeck serialises the DataFrame to JSON for the browser. Pass
    `a5_index_type="int"` if your source column holds raw ints — they'll be
    converted automatically.

---

## Transforms

| Name | Best for |
|---|---|
| `linear` | Uniformly distributed values |
| `log` | Heavy-tailed count distributions |
| `quantile` | Any distribution; highlights relative rank |

---

## H3 resolution guide

| Resolution | Avg area | Typical use |
|---|---|---|
| 5 | ~252 km² | Country-level |
| 7 | ~5.2 km² | City-level |
| 9 | ~0.1 km² | Neighbourhood |
| 11 | ~0.001 km² | Block-level |

## A5 resolution guide

A5 pentagons roughly quarter in area per resolution step (vs. H3's ~7x
factor), so equivalent detail sits at a higher resolution number.

| Resolution | Avg area | Typical use |
|---|---|---|
| 3 | ~531,000 km² | Subcontinent-level |
| 8 | ~519 km² | Country/region-level |
| 11 | ~8 km² | City-level (`a5_map` default) |
| 15 | ~0.03 km² | Neighbourhood |
| 20 | ~31 m² | Parcel/building-level |
