# Changelog

All notable changes to `streamlit-hexviz` are documented here. Format based
on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

- Documentation site scaffolded with MkDocs Material and published to
  GitHub Pages.

## [0.2.0] — current

Current version on PyPI ([release notes to be filled in](https://github.com/Robert-Ziegltrum/streamlit-hexviz/releases)).

- `h3_map`, `h3_heatmap`, `h3_choropleth` for H3 grids.
- `s2_map` for S2 grids (optional extra).
- `a5_map`, `a5_choropleth` for A5 pentagonal grids (optional extra).
- Automatic sidebar controls for resolution, colour scale, opacity, and
  3-D extrusion.


## [0.3.0] — to be released

### Added

- Optional GeoPandas input: `h3_map`, `h3_heatmap`, `s2_map`, and `a5_map`
  now accept a GeoDataFrame of Point geometries in place of a plain
  DataFrame + `lat`/`lon` columns. A missing CRS emits a warning and
  assumes EPSG:4326; any other CRS is reprojected automatically.
  Non-Point geometries (polygons, lines) raise a clear error rather than
  being silently reduced to a centroid — polygon-to-hex conversion isn't
  supported yet.
- `lat`/`lon` column auto-detection for plain DataFrame input: you no
  longer have to pass `lat=`/`lon=` explicitly. Omitting them looks for
  a column named `lat`, `latitude`, `LAT`, or `LATITUDE` (and the
  longitude equivalents) — the same convention `st.map` uses, so there's
  nothing new to learn if you're already using it there.
- GeoDataFrame input is protected against accidental data loss: if the
  target `lat`/`lon` column name already exists as a real (non-geometry)
  column, it now raises instead of silently overwriting it.

### Changed

- **Potentially breaking:** `lat`/`lon` default from the literal strings
  `"lat"`/`"lon"` to `None` (triggering auto-detection). If your
  DataFrame has exactly one match among the candidate names, nothing
  changes. But if it has more than one — e.g. both a `lat` and a
  `latitude` column — a call that used to silently use `lat` (because it
  was the hardcoded default) now raises an "ambiguous column" error
  instead. Pass `lat=`/`lon=` explicitly to disambiguate. Calls that
  already pass `lat=`/`lon=` explicitly are unaffected.
- Passing a Polars DataFrame now raises a clear `TypeError` pointing you
  to `.to_pandas()`, instead of failing later with a confusing error
  deeper in the pipeline.
