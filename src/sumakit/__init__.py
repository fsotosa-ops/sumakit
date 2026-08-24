"""sumakit — el SDK de Suma Studio, con las utilidades de EDA que lo rodean.

El núcleo es el puente al proyecto y solo necesita `pandas`:

    from sumakit import studio

    client = studio.StudioClient("sk_...")
    client.publish(alerts, "alertas")

Sirve igual en una celda de Colab, en un script, en un DAG o en un contenedor.

Lo demás son **capas opcionales**, y hay que pedirlas al instalar:

    pip install sumakit            # solo el SDK
    pip install "sumakit[eda]"     # profile, stats, plots, exploration
    pip install "sumakit[all]"     # todo

    from sumakit import nb, profile, stats, plots
    nb.setup(seed=42)

    profile.overview(df)                 # tabla: tipos, nulos, únicos, ceros
    stats.distribution_report(df)        # asimetría, outliers, escalador sugerido
    fig = plots.correlation_heatmap(df)  # Figure, no un plt.show()

Las funciones de `profile` y `stats` devuelven DataFrames; las de `plots`
devuelven `Figure`. Nada dibuja por su cuenta ni muta estado global.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

# Los submódulos se cargan al pedirlos, no al importar el paquete.
#
# `import sumakit` con carga ansiosa arrastraba matplotlib, seaborn, altair y
# python-pptx incluso para publicar una tabla. Con PEP 562 el SDK se puede
# instalar y usar solo, que es lo que lo hace servir en un contenedor.
_LAZY = {
    "studio": "El puente al proyecto. Solo necesita pandas.",
    "color": "Aritmética de color. Necesita el extra `eda`.",
    "theme": "Paletas y estilo de matplotlib. Necesita el extra `eda`.",
    "nb": "Ajustes de notebook. Necesita el extra `eda`.",
    "profile": "Perfilado de columnas. Necesita el extra `eda`.",
    "stats": "Diagnóstico estadístico. Necesita el extra `eda`.",
    "plots": "Gráficos estáticos. Necesita el extra `eda`.",
    "exploration": "El EDA de una pasada. Necesita el extra `eda`.",
    "interactive": "Gráficos interactivos. Necesita el extra `interactive`.",
    "deck": "El `.pptx`. Necesita el extra `report`.",
}

if TYPE_CHECKING:  # pragma: no cover - solo para los verificadores de tipos
    from . import (
        color,
        deck,
        exploration,
        interactive,
        nb,
        plots,
        profile,
        stats,
        studio,
        theme,
    )
    from .exploration import Exploration, explore


def __getattr__(name: str) -> Any:
    """Carga un submódulo la primera vez que se lo pide.

    Args:
        name: El atributo que se buscó en el paquete.

    Returns:
        El submódulo, o lo que `exploration` exporta.

    Raises:
        AttributeError: Si el nombre no es de este paquete.
        ModuleNotFoundError: Si falta el extra que trae sus dependencias. El
            mensaje dice cuál pedir en vez de nombrar la librería que falta.
    """
    if name in {"explore", "Exploration"}:
        return getattr(importlib.import_module(".exploration", __name__), name)

    if name not in _LAZY:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    try:
        return importlib.import_module(f".{name}", __name__)
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            f"sumakit.{name} necesita dependencias que no están instaladas. "
            f"{_LAZY[name]} Instálalo con: pip install 'sumakit[all]'"
        ) from error


def __dir__() -> list[str]:
    """Para que el autocompletado del notebook siga viendo los submódulos."""
    return sorted([*_LAZY, "explore", "Exploration", "__version__"])


__all__ = [
    "Exploration",
    "__version__",
    "color",
    "deck",
    "explore",
    "exploration",
    "interactive",
    "nb",
    "plots",
    "profile",
    "stats",
    "studio",
    "theme",
]
