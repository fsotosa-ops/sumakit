"""Una sola llamada que revisa el dataset y muestra lo que importa.

La comodidad de `ProfileReport(df)` sin su defecto: en vez de graficar las 26
columnas y dejarte a ti encontrar cuál es el problema, grafica **solo lo que
las alertas señalaron**. Cinco figuras que importan en vez de veintiséis que no.

    resultado = sumakit.explore(df)      # en un notebook se dibuja solo
    resultado.alerts                     # y sigue siendo composable
    resultado.figures["distribuciones"].savefig("fig.svg")
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field

import pandas as pd
from matplotlib.figure import Figure

from . import plots, profile, stats

__all__ = ["Exploration", "explore"]

_MAX_PANELES = 12


@dataclass
class Exploration:
    """Resultado de `explore`: tablas, figuras y un render para el notebook."""

    alerts: pd.DataFrame
    overview: pd.DataFrame
    distributions: pd.DataFrame
    compositional: pd.DataFrame
    figures: dict[str, Figure] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"Exploration({len(self.alerts)} alertas, "
            f"{len(self.overview)} columnas, {len(self.figures)} figuras)"
        )

    @staticmethod
    def _img(fig: Figure) -> str:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f'<img src="data:image/png;base64,{b64}" style="max-width:100%;height:auto">'

    def _repr_html_(self) -> str:
        """Jupyter llama esto solo. No hay `plt.show()` ni efectos globales."""
        partes = ["<h3 style='margin:0.6em 0 0.3em'>Qué revisar</h3>"]
        if self.alerts.empty:
            partes.append("<p>Sin hallazgos.</p>")
        else:
            partes.append(profile.styled(self.alerts).to_html())

        if not self.compositional.empty:
            partes.append("<h3 style='margin:1.2em 0 0.3em'>Grupos composicionales</h3>")
            partes.append(self.compositional.to_html(index=False))

        for nombre, fig in self.figures.items():
            partes.append(f"<h3 style='margin:1.2em 0 0.3em'>{nombre.capitalize()}</h3>")
            partes.append(self._img(fig))
        return "\n".join(partes)


def explore(
    df: pd.DataFrame,
    *,
    sample: int | None = 10_000,
    random_state: int = 0,
    compositional: bool = True,
) -> Exploration:
    """Revisa un DataFrame y devuelve tablas y figuras guiadas por las alertas.

    Las figuras se dibujan sobre una muestra (`sample`) para que la llamada sea
    rápida en datasets grandes; las tablas y las alertas siempre se calculan
    sobre los datos completos, porque ahí sí importa el conteo exacto.
    """
    alertas = profile.alerts(df, compositional=compositional)
    resumen = profile.overview(df)
    forma = stats.distribution_report(df)
    grupos = (
        stats.sum_constant_groups(df) if compositional
        else pd.DataFrame(columns=["constant", "n_columns", "columns"])
    )

    muestra = (
        df.sample(sample, random_state=random_state)
        if sample is not None and len(df) > sample else df
    )

    def señaladas(chequeo: str) -> list[str]:
        fila = alertas[alertas["chequeo"] == chequeo]
        if fila.empty:
            return []
        cols = [c.strip() for c in fila.iloc[0]["columnas"].split(",")]
        return [c for c in cols if c in df.columns]

    figuras: dict[str, Figure] = {}

    # Solo las columnas cuya forma pide atención, no las 26.
    sesgadas = señaladas("asimetría")[:_MAX_PANELES]
    if sesgadas:
        figuras["distribuciones señaladas"] = plots.distributions(
            muestra, columns=sesgadas,
            title="Variables con asimetría o exceso de outliers",
        )

    ceros = señaladas("ceros")
    if ceros:
        figuras["exceso de ceros"] = plots.ranking(
            resumen.loc[ceros, "pct_zeros"],
            title="Ceros por columna",
            xlabel="% de filas en cero",
        )

    if resumen["n_missing"].sum() > 0:
        figuras["datos faltantes"] = plots.missing_matrix(muestra)

    if df.select_dtypes("number").shape[1] >= 2:
        figuras["correlación"] = plots.correlation_heatmap(muestra)

    return Exploration(
        alerts=alertas, overview=resumen, distributions=forma,
        compositional=grupos, figures=figuras,
    )
