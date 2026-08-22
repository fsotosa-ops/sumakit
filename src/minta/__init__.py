"""minta — utilidades de EDA y analítica reutilizables.

    from minta import nb, profile, stats, plots
    nb.setup(seed=42)

    profile.overview(df)                 # tabla: tipos, nulos, únicos, ceros
    stats.distribution_report(df)        # asimetría, outliers, escalador sugerido
    fig = plots.correlation_heatmap(df)  # Figure, no un plt.show()

Las funciones de `profile` y `stats` devuelven DataFrames; las de `plots`
devuelven `Figure`. Nada dibuja por su cuenta ni muta estado global.
"""

from . import nb, plots, profile, stats, theme

__version__ = "0.1.0"
__all__ = ["nb", "plots", "profile", "stats", "theme", "__version__"]
