"""sumakit — utilidades para talleres de ciencia de datos y machine learning.

El ciclo de un taller, de los datos al entregable:

    from sumakit import nb, profile, stats, plots
    nb.setup(seed=42)

    profile.overview(df)                 # tabla: tipos, nulos, únicos, ceros
    stats.distribution_report(df)        # asimetría, outliers, escalador sugerido
    fig = plots.correlation_heatmap(df)  # Figure, no un plt.show()

Dos contratos gobiernan todo el paquete, y son lo que hace que una tabla del
notebook llegue al PDF y a la lámina sin volver a maquetarla:

- **Las funciones de perfilado y diagnóstico devuelven `DataFrame`.** Por eso
  `profile.styled` y `profile.as_markdown` sirven sobre cualquiera de ellas.
- **Las de dibujo devuelven `Figure`, y ninguna llama a `plt.show()`.** La misma
  función sirve en el notebook, en el informe de Quarto, en el deck y en un test.

Nada muta estado global y ninguna función trae paleta propia: todo sale del tema
activo (`theme`).

**sumakit diagnostica; no transforma ni ajusta.** El preprocesamiento es de
scikit-learn, porque un transformador ajustado hay que reusarlo sobre test. El
modelo lo ajustas tú, a la vista, y sumakit describe el resultado.
"""

from __future__ import annotations

import importlib
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

try:
    __version__ = version("sumakit")
except PackageNotFoundError:  # pragma: no cover - checkout sin instalar
    # Una sola fuente de verdad: la versión vive en `pyproject.toml`. Escribirla
    # también aquí es cómo las dos se desincronizan sin que nadie lo note.
    __version__ = "0.0.0.dev0"

# Los submódulos se cargan al pedirlos, no al importar el paquete.
#
# No es por las dependencias —el EDA y el entregable son el núcleo—, es por el
# arranque: `import sumakit` con carga ansiosa levanta matplotlib, seaborn y
# python-pptx aunque solo vayas a mirar una tabla. Con PEP 562 cada módulo se
# paga cuando se usa.
_LAZY = {
    "color": "Aritmética de color.",
    "theme": "Paletas y estilo de matplotlib.",
    "nb": "Ajustes de notebook.",
    "profile": "Perfilado de columnas.",
    "stats": "Diagnóstico estadístico.",
    "cluster": "Diagnóstico de segmentación. Necesita el extra `ml`.",
    "plots": "Gráficos estáticos.",
    "exploration": "El EDA de una pasada.",
    "deck": "El `.pptx` del entregable.",
    "interactive": "Gráficos interactivos. Necesita el extra `interactive`.",
    "studio": "El puente a Suma Studio. En stand-by.",
    "destinations": "Suma Studio como `destination` de dlt. Necesita el extra `extract`.",
}

if TYPE_CHECKING:  # pragma: no cover - solo para los verificadores de tipos
    from . import (
        cluster,
        color,
        deck,
        destinations,
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
    """Todo lo que el paquete ofrece: lo ya cargado y lo que espera perezoso.

    Sin esto `dir(sumakit)` perdía `__doc__` y `__version__`, porque con PEP 562
    nada es atributo real hasta que se lo pide. Y con `globals()` a secas se iba
    al otro extremo: `importlib`, `Any` y `TYPE_CHECKING` ensuciando el
    autocompletado del notebook, que es donde esto se mira.
    """
    dunders = {n for n in globals() if n.startswith("__")}
    return sorted(set(__all__) | set(_LAZY) | dunders)


__all__ = [
    "Exploration",
    "__version__",
    "cluster",
    "color",
    "deck",
    "destinations",
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
