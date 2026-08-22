"""Arranque de notebook: una llamada en vez de doce líneas copiadas."""

from __future__ import annotations

import random

import numpy as np

from . import theme

__all__ = ["setup", "adaptive_float"]


def adaptive_float(v: float) -> str:
    """Formato que sobrevive a datasets con escalas mezcladas.

    Un formato fijo obliga a elegir: con `.2f` los montos se leen bien pero las
    proporciones de milésimas se aplastan a 0.00; con `.4g` los montos grandes
    saltan a notación científica. Este ajusta la precisión a la magnitud.
    """
    if v != v or v in (float("inf"), float("-inf")):  # NaN / infinitos
        return str(v)
    if v == 0:
        return "0"
    magnitud = abs(v)
    if magnitud >= 1000:
        return f"{v:,.0f}"
    if magnitud >= 1:
        return f"{v:,.2f}"
    return f"{v:.4g}"


def setup(*, seed: int | None = 42, palette: theme.Palette = theme.LIGHT,
          max_rows: int = 60, max_columns: int = 40,
          float_format=adaptive_float) -> None:
    """Fija semillas, aplica el tema y ajusta la impresión de pandas.

    La semilla es lo que separa "me dio 0.83" de "da 0.83". Si `seed` es None
    no se toca el estado aleatorio.

    `float_format` controla cómo se imprimen los flotantes. Por defecto usa
    `adaptive_float`, que ajusta la precisión a la magnitud. Pasa None para
    dejar el comportamiento nativo de pandas, o tu propia función.
    """
    import pandas as pd

    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    theme.use(palette)

    pd.set_option("display.max_rows", max_rows)
    pd.set_option("display.max_columns", max_columns)
    pd.set_option("display.width", 120)
    if float_format is not None:
        pd.set_option("display.float_format", float_format)
