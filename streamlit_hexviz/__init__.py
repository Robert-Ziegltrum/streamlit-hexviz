"""
streamlit_hexviz
================
Public API for streamlit-hexviz.

This module is the preferred import path:

>>> import streamlit_hexviz as shv

Backwards compatibility:
`streamlit_h3viz` remains available as a shim.
"""

from streamlit_hexviz._components import h3_choropleth, h3_heatmap, h3_map, s2_map

__all__ = ["h3_map", "h3_heatmap", "h3_choropleth", "s2_map"]
