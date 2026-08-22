"""Tema visual parametrizable.

La paleta por defecto está validada contra los seis chequeos de color
(banda de luminosidad, piso de croma, separación para daltonismo, piso de
visión normal, contraste). Si trabajas para un cliente con marca propia,
sustituye los valores construyendo otra `Palette` — el resto de la librería
no cambia.

Regla que la librería hace cumplir, no solo documenta: las formas que
comparan *todos los pares* de series a la vez (scatter, pairplot, small
multiples) solo admiten 3 colores categóricos. Con más, ningún orden pasa
los pisos de separación: hay que agrupar en "Otros" o facetar.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field, replace

import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap

__all__ = [
    "Palette",
    "LIGHT",
    "DARK",
    "active",
    "use",
    "using",
    "categorical",
    "sequential_cmap",
    "diverging_cmap",
    "MAX_ALL_PAIRS_SERIES",
    "MAX_SERIES",
]

#: Series máximas en formas que comparan todos los pares (scatter, pairplot).
MAX_ALL_PAIRS_SERIES = 3
#: Series máximas en formas de pares adyacentes (barras, líneas, apilados).
MAX_SERIES = 8


@dataclass(frozen=True)
class Palette:
    """Parámetros de color. Sustituye los valores para re-skinear por cliente."""

    name: str
    categorical: tuple[str, ...]
    sequential: tuple[str, ...]  # de claro a oscuro
    diverging_low: str
    diverging_high: str
    neutral: str
    surface: str
    text_primary: str
    text_secondary: str
    grid: str
    max_all_pairs: int = MAX_ALL_PAIRS_SERIES
    font_family: tuple[str, ...] = field(default=("DejaVu Sans",))

    def rc_params(self) -> dict:
        """Traduce la paleta a rcParams de matplotlib."""
        return {
            "figure.facecolor": self.surface,
            "figure.edgecolor": self.surface,
            "figure.dpi": 110,
            "savefig.facecolor": self.surface,
            "savefig.bbox": "tight",
            "savefig.dpi": 200,
            "axes.facecolor": self.surface,
            "axes.edgecolor": self.grid,
            "axes.labelcolor": self.text_secondary,
            "axes.titlecolor": self.text_primary,
            "axes.titlesize": 12,
            "axes.titleweight": "normal",
            "axes.titlelocation": "left",
            "axes.titlepad": 12,
            "axes.labelsize": 10,
            "axes.linewidth": 0.8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "axes.prop_cycle": mpl.cycler(color=list(self.categorical)),
            "grid.color": self.grid,
            "grid.linewidth": 0.6,
            "grid.alpha": 0.5,
            "xtick.color": self.text_secondary,
            "ytick.color": self.text_secondary,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "legend.frameon": False,
            "legend.fontsize": 9,
            "lines.linewidth": 2.0,
            "lines.markersize": 8,
            "patch.linewidth": 0.0,
            "font.family": "sans-serif",
            "font.sans-serif": list(self.font_family),
            "text.color": self.text_primary,
        }


LIGHT = Palette(
    name="minta-light",
    categorical=(
        "#2a78d6",  # azul
        "#eb6834",  # naranja
        "#1baf7a",  # aqua
        "#eda100",  # amarillo
        "#e87ba4",  # magenta
        "#008300",  # verde
        "#4a3aa7",  # violeta
        "#e34948",  # rojo
    ),
    sequential=(
        "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5",
        "#2a78d6", "#256abf", "#1c5cab", "#104281",
    ),
    diverging_low="#2a78d6",
    diverging_high="#e34948",
    neutral="#f0efec",
    surface="#fcfcfb",
    text_primary="#0b0b0b",
    text_secondary="#52514e",
    grid="#d9d8d4",
)

DARK = replace(
    LIGHT,
    name="minta-dark",
    categorical=(
        "#3987e5", "#d95926", "#199e70", "#c98500",
        "#d55181", "#008300", "#9085e9", "#e66767",
    ),
    neutral="#383835",
    surface="#1a1a19",
    text_primary="#ffffff",
    text_secondary="#c3c2b7",
    grid="#3d3d3a",
)

_active: Palette = LIGHT


def active() -> Palette:
    """Paleta en uso."""
    return _active


def use(palette: Palette = LIGHT) -> Palette:
    """Aplica la paleta a matplotlib de forma global. Devuelve la anterior."""
    global _active
    previous = _active
    mpl.rcParams.update(palette.rc_params())
    _active = palette
    return previous


@contextlib.contextmanager
def using(palette: Palette):
    """Aplica la paleta solo dentro del bloque, sin dejar estado global sucio."""
    previous_rc = mpl.rcParams.copy()
    previous = use(palette)
    try:
        yield palette
    finally:
        mpl.rcParams.update(previous_rc)
        global _active
        _active = previous


def categorical(n: int, *, all_pairs: bool = False, palette: Palette | None = None) -> list[str]:
    """Devuelve `n` colores categóricos en orden fijo, nunca ciclado.

    El orden de los slots es el mecanismo de seguridad para daltonismo, no
    decoración: se asignan siempre desde el primero.

    `all_pairs=True` para formas donde todas las series se comparan entre sí
    (scatter, pairplot, small multiples). Ahí el límite es 3.
    """
    pal = palette or _active
    limit = pal.max_all_pairs if all_pairs else min(MAX_SERIES, len(pal.categorical))
    if n > limit:
        forma = "que compara todos los pares (scatter/pairplot)" if all_pairs else "categórica"
        raise ValueError(
            f"{n} series en una forma {forma}: el máximo validado es {limit}. "
            "Agrupa el resto en 'Otros' o separa en facetas — generar más hues "
            "rompe la separación para daltonismo."
        )
    return list(pal.categorical[:n])


def sequential_cmap(palette: Palette | None = None, *, reverse: bool = False):
    """Rampa de un solo tono para magnitud continua (heatmaps)."""
    pal = palette or _active
    steps = list(pal.sequential)
    if reverse:
        steps = steps[::-1]
    return LinearSegmentedColormap.from_list(f"{pal.name}-seq", steps)


def diverging_cmap(palette: Palette | None = None):
    """Dos tonos con gris neutro al medio, para polaridad (correlaciones).

    El punto medio es gris a propósito: un tono al centro haría leer "cero"
    como si fuera una categoría más.
    """
    pal = palette or _active
    return LinearSegmentedColormap.from_list(
        f"{pal.name}-div",
        [pal.diverging_low, pal.neutral, pal.diverging_high],
    )
