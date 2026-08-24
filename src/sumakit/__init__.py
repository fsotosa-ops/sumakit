"""sumakit — utilidades de EDA y analítica reutilizables.

    from sumakit import nb, profile, stats, plots
    nb.setup(seed=42)

    profile.overview(df)                 # tabla: tipos, nulos, únicos, ceros
    stats.distribution_report(df)        # asimetría, outliers, escalador sugerido
    fig = plots.correlation_heatmap(df)  # Figure, no un plt.show()

Las funciones de `profile` y `stats` devuelven DataFrames; las de `plots`
devuelven `Figure`. Nada dibuja por su cuenta ni muta estado global.

`studio` es el puente al proyecto: publica una de esas tablas y desde ahí
alimenta el deck y el informe, sin exportar un CSV a mano.
"""

from . import deck, interactive, nb, plots, profile, stats, studio, theme
from .exploration import Exploration, explore

__version__ = "0.1.0"
__all__ = [
    "explore",
    "Exploration",
    "deck",
    "interactive",
    "nb",
    "plots",
    "profile",
    "stats",
    "studio",
    "theme",
    "__version__",
]
