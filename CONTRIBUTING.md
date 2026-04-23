# Contributing to streamlit-hexviz

Thanks for your interest! Here's how to get started.

## Setup

```bash
git clone https://github.com/yourname/streamlit-hexviz
cd streamlit-hexviz
pip install -e ".[dev]"
```

## Running the demo locally

```bash
streamlit run demo/app.py
```

## Project structure

```
streamlit_h3viz/
├── _h3_utils.py     # H3 binning and aggregation
├── _s2_utils.py     # S2 binning and aggregation
├── _transforms.py   # Normalisation and colour scales
├── _layers.py       # PyDeck layer builders
├── _components.py   # Streamlit-facing API
└── __init__.py      # Public exports
demo/
└── app.py           # Demo Streamlit app
```

## Ways to contribute

- **Bug fixes** — open an issue first if it's non-trivial
- **New colour scales** — add to `COLOUR_SCALES` in `_transforms.py`
- **New transforms** — add to `TRANSFORMS` dict in `_transforms.py`
- **New layer types** — add a builder in `_layers.py`, wire it up in `_components.py`
- **S2 improvements** — the S2 backend is minimal; better geometry helpers welcome
- **Performance** — the inner loops in `_h3_utils.py` are pure Python; vectorised replacements welcome

## Code style

```bash
ruff check .
black .
```

## Submitting a PR

1. Fork the repo and create a branch: `git checkout -b my-feature`
2. Make your changes
3. Run `ruff` and `black` to lint/format
4. Open a PR with a short description of what changed and why

## Reporting bugs

Please include your Python version, `h3` version, `pydeck` version, and a minimal reproducible example.