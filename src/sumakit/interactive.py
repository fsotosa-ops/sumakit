"""Gráficos interactivos sobre datos agregados, con Altair.

Por qué un segundo motor de dibujo y no todo aquí: **Altair incrusta los datos
dentro de la especificación**. Con decenas de miles de filas el JSON se vuelve
inmanejable para el navegador —por eso Altair corta en 5.000 filas por
defecto—, mientras que matplotlib rasteriza y no depende del tamaño.

De ahí el reparto:

- `plots` (matplotlib): datos crudos, muchas filas, y todo lo que va al PDF.
- `interactive` (Altair): datos ya agregados, pocas filas, y lo que vive en HTML.

Los dos beben de la misma paleta de `theme`, así que se ven como un sistema.
"""

from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd

from . import theme

__all__ = ["apply_theme", "concentration_curve", "concentration_table"]

_OTROS = "Otros"


def apply_theme(palette: theme.Palette | None = None) -> None:
    """Registra y activa el tema de la librería en Altair."""
    pal = palette or theme.active()

    @alt.theme.register("sumakit", enable=True)
    def _tema() -> alt.theme.ThemeConfig:
        return {
            "config": {
                "background": pal.surface,
                "view": {"stroke": "transparent", "continuousWidth": 480, "continuousHeight": 300},
                "font": "Helvetica Neue, Helvetica, Arial, sans-serif",
                "title": {
                    "anchor": "start",
                    "fontSize": 14,
                    "fontWeight": "normal",
                    "color": pal.text_primary,
                    "subtitleColor": pal.text_secondary,
                },
                "axis": {
                    "grid": False,
                    "domainColor": pal.grid,
                    "tickColor": pal.grid,
                    "labelColor": pal.text_secondary,
                    "titleColor": pal.text_secondary,
                    "labelFontSize": 11,
                    "titleFontSize": 11,
                    "titleFontWeight": "normal",
                },
                "axisY": {
                    "grid": True,
                    "gridColor": pal.grid,
                    "gridOpacity": 0.5,
                    "domain": False,
                    "ticks": False,
                },
                "legend": {
                    "labelColor": pal.text_secondary,
                    "titleColor": pal.text_secondary,
                    "labelFontSize": 11,
                    "titleFontSize": 11,
                    "titleFontWeight": "normal",
                    "symbolType": "stroke",
                    "symbolStrokeWidth": 3,
                },
                "range": {"category": list(pal.categorical)},
                "line": {"strokeWidth": 2.5},
                "point": {"size": 60, "filled": True},
            }
        }


def _agrupar_raros(serie: pd.Series, max_levels: int) -> pd.Series:
    """Deja los niveles más frecuentes y manda el resto a 'Otros'.

    Un desplegable con cincuenta opciones no es interactividad, es un problema
    de navegación.
    """
    texto = serie.astype("object").fillna("(sin dato)").astype(str)
    top = texto.value_counts().head(max_levels).index
    return texto.where(texto.isin(top), _OTROS)


def concentration_table(
    df: pd.DataFrame,
    columns: list[str],
    *,
    by: str | None = None,
    filter_by: str | None = None,
    max_levels: int = 8,
) -> pd.DataFrame:
    """Los datos detrás de la curva de concentración, ya agregados.

    Para cada fila se ordenan sus proporciones de mayor a menor y se acumulan:
    el rango 1 es la parte más grande, el rango 2 las dos más grandes juntas, y
    así. Un cliente concentrado llega a 1 en el primer paso; uno repartido sube
    de a poco.

    Devuelve el promedio por rango, opcionalmente abierto por `by` y
    `filter_by`. Se expone aparte del gráfico porque la tabla también sirve:
    para una afirmación en el informe, para un test, o para otro gráfico.
    """
    faltan = [c for c in columns if c not in df.columns]
    if faltan:
        raise KeyError(f"columnas ausentes en el DataFrame: {faltan}")
    if len(columns) < 2:
        raise ValueError("una curva de concentración necesita al menos 2 columnas")

    datos = df[columns].to_numpy(dtype=float)
    total = datos.sum(axis=1, keepdims=True)
    validas = (total.ravel() > 0) & ~np.isnan(datos).any(axis=1)
    if not validas.any():
        return pd.DataFrame(columns=["rango", "acumulado", "n"])

    # Cada fila se normaliza a 1: así la curva compara forma, no magnitud.
    proporciones = datos[validas] / total[validas]
    ordenadas = -np.sort(-proporciones, axis=1)
    acumuladas = ordenadas.cumsum(axis=1)

    largo = pd.DataFrame(acumuladas, columns=range(1, len(columns) + 1))
    largo.index = df.index[validas]

    claves = []
    for col, nombre in ((by, "by"), (filter_by, "filter")):
        if col is None:
            continue
        if col not in df.columns:
            raise KeyError(f"columna ausente en el DataFrame: {col}")
        largo[nombre] = _agrupar_raros(df.loc[validas, col], max_levels).to_numpy()
        claves.append(nombre)

    largo = largo.melt(id_vars=claves, var_name="rango", value_name="acumulado")
    agregado = (
        largo.groupby(claves + ["rango"], observed=True, dropna=False)
        .agg(acumulado=("acumulado", "mean"), n=("acumulado", "size"))
        .reset_index()
    )
    renombres = {"by": by, "filter": filter_by}
    return agregado.rename(columns={k: v for k, v in renombres.items() if v})


def concentration_curve(
    df: pd.DataFrame,
    columns: list[str],
    *,
    by: str | None = None,
    filter_by: str | None = None,
    max_levels: int = 8,
    title: str = "",
    subtitle: str = "",
) -> alt.Chart:
    """Curva de concentración interactiva de un grupo composicional.

    Responde cuán concentrado está el consumo: ¿un cliente reparte su gasto
    entre los siete días, o lo hace todo en uno?

    - `by` abre una línea por categoría, con leyenda seleccionable.
    - `filter_by` agrega un desplegable para filtrar por otra variable.

    Va sobre datos agregados —unas decenas de filas—, que es donde Altair
    rinde. Para distribuciones sobre datos crudos, usa `plots`.
    """
    tabla = concentration_table(df, columns, by=by, filter_by=filter_by, max_levels=max_levels)
    if tabla.empty:
        raise ValueError("no hay filas con suma positiva para construir la curva")

    apply_theme()

    codificacion = {
        "x": alt.X("rango:O", title=f"partes acumuladas (de {len(columns)})"),
        "y": alt.Y(
            "acumulado:Q",
            title="proporción acumulada del consumo",
            scale=alt.Scale(domain=[0, 1]),
            axis=alt.Axis(format="%"),
        ),
        "tooltip": [
            alt.Tooltip("rango:O", title="parte"),
            alt.Tooltip("acumulado:Q", title="acumulado", format=".1%"),
            alt.Tooltip("n:Q", title="clientes", format=","),
        ],
    }

    capas = alt.Chart(tabla)

    if by is not None:
        seleccion = alt.selection_point(fields=[by], bind="legend")
        codificacion["color"] = alt.Color(f"{by}:N", title=by.replace("_", " "))
        codificacion["opacity"] = alt.condition(seleccion, alt.value(1.0), alt.value(0.15))
        codificacion["tooltip"].insert(0, alt.Tooltip(f"{by}:N", title=by.replace("_", " ")))
        capas = capas.add_params(seleccion)

    if filter_by is not None:
        opciones = sorted(tabla[filter_by].dropna().unique().tolist())
        desplegable = alt.binding_select(options=opciones, name=f"{filter_by}:  ")
        corte = alt.selection_point(fields=[filter_by], bind=desplegable, value=opciones[0])
        capas = capas.add_params(corte).transform_filter(corte)

    grafico = (
        capas.mark_line(point=True)
        .encode(**codificacion)
        .properties(
            width="container",
            height=320,
            title=alt.TitleParams(
                title or "Concentración del consumo",
                subtitle=subtitle
                or "Cada parte es la mayor restante: si la curva salta a 100% "
                "en la primera, el consumo ocurre en una sola.",
            ),
        )
    )
    return grafico
