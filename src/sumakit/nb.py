"""Arranque de notebook: una llamada en vez de doce líneas copiadas."""

from __future__ import annotations

import random

import numpy as np

from . import theme

__all__ = ["setup"]


def setup(*, seed: int | None = 42, palette: theme.Palette = theme.LIGHT,
          max_rows: int = 60, max_columns: int = 40) -> None:
    """Fija semillas, aplica el tema y ajusta la impresión de pandas.

    La semilla es lo que separa "me dio 0.83" de "da 0.83". Si `seed` es None
    no se toca el estado aleatorio.
    """
    import pandas as pd

    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    theme.use(palette)

    pd.set_option("display.max_rows", max_rows)
    pd.set_option("display.max_columns", max_columns)
    pd.set_option("display.width", 120)
    pd.set_option("display.float_format", lambda v: f"{v:,.4g}")
