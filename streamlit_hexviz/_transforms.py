"""
Value transforms and colour-scale mapping for grid data.

Each transform returns a new Series of the same length, scaled to [0, 1]
(or close to it) suitable for feeding into a colour scale.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Value normalisation
# ---------------------------------------------------------------------------


def normalise(values: pd.Series) -> pd.Series:
    """Linear min-max normalisation to [0, 1]."""
    lo, hi = values.min(), values.max()
    if hi == lo:
        return pd.Series(np.ones(len(values)), index=values.index)
    return (values - lo) / (hi - lo)


def log_normalise(values: pd.Series, base: float = 10) -> pd.Series:
    """Log-scale normalisation. Useful for heavy-tailed count distributions."""
    shifted = values - values.min() + 1  # ensure positive
    log_vals = np.log(shifted) / np.log(base)
    return normalise(pd.Series(log_vals, index=values.index))


def quantile_normalise(values: pd.Series, n_quantiles: int = 10) -> pd.Series:
    """Quantile-bin normalisation — each bin gets equal rank weight."""
    ranks = values.rank(method="average", pct=True)
    bins = np.floor(ranks * n_quantiles) / n_quantiles
    return pd.Series(bins, index=values.index)


TRANSFORMS = {
    "linear": normalise,
    "log": log_normalise,
    "quantile": quantile_normalise,
}


def apply_transform(values: pd.Series, transform: str = "linear") -> pd.Series:
    if transform not in TRANSFORMS:
        raise ValueError(f"transform must be one of {list(TRANSFORMS)}, got {transform!r}")
    return TRANSFORMS[transform](values)


# ---------------------------------------------------------------------------
# Colour scales
# ---------------------------------------------------------------------------


# Each colour scale is a list of (R, G, B) stops from low → high value.
COLOUR_SCALES: dict[str, list[tuple[int, int, int]]] = {
    "viridis": [
        (68, 1, 84),
        (59, 82, 139),
        (33, 145, 140),
        (94, 201, 98),
        (253, 231, 37),
    ],
    "plasma": [
        (13, 8, 135),
        (126, 3, 168),
        (204, 71, 120),
        (248, 149, 64),
        (240, 249, 33),
    ],
    "heat": [
        (0, 0, 255),
        (0, 255, 255),
        (0, 255, 0),
        (255, 255, 0),
        (255, 0, 0),
    ],
    "blues": [
        (237, 248, 255),
        (198, 219, 239),
        (107, 174, 214),
        (33, 113, 181),
        (8, 48, 107),
    ],
    "reds": [
        (255, 245, 240),
        (252, 187, 161),
        (252, 113, 69),
        (203, 24, 29),
        (103, 0, 13),
    ],
    "greens": [
        (247, 252, 245),
        (199, 233, 192),
        (116, 196, 118),
        (35, 139, 69),
        (0, 68, 27),
    ],
}


def value_to_colour(
    norm_value: float,
    scale: str = "viridis",
    alpha: int = 200,
) -> list[int]:
    """
    Map a normalised value in [0, 1] to an [R, G, B, A] list using a colour scale.
    """
    stops = COLOUR_SCALES.get(scale, COLOUR_SCALES["viridis"])
    n = len(stops) - 1
    pos = norm_value * n
    lo = int(pos)
    hi = min(lo + 1, n)
    t = pos - lo

    r = int(stops[lo][0] + t * (stops[hi][0] - stops[lo][0]))
    g = int(stops[lo][1] + t * (stops[hi][1] - stops[lo][1]))
    b = int(stops[lo][2] + t * (stops[hi][2] - stops[lo][2]))
    return [r, g, b, alpha]


def add_colour_column(
    df: pd.DataFrame,
    value_col: str = "value",
    transform: str = "linear",
    colour_scale: str = "viridis",
    alpha: int = 200,
) -> pd.DataFrame:
    """
    Add a 'fill_color' column (list of [R,G,B,A]) to a grid DataFrame.
    """
    norm = apply_transform(df[value_col], transform)
    df = df.copy()
    df["fill_color"] = [value_to_colour(v, colour_scale, alpha) for v in norm]
    return df

