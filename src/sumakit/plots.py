"""Gráficos de EDA.

Tres reglas que gobiernan todo este módulo:

1. **Toda función devuelve `Figure`. Ninguna llama a `plt.show()`.** Esa sola
   decisión es la que hace que la misma función sirva en el notebook, en el PDF
   del informe, en una lámina exportada a SVG y dentro de un test.
2. **Ninguna muta estado global.** Nada de `sns.set_theme` ni
   `sns.reset_defaults` por dentro: el tema se aplica una vez, o por bloque con
   `theme.using(...)`.
3. **Ninguna trae paleta propia.** Los colores salen del tema activo, para que
   todos los gráficos se lean como un sistema y se re-skineen de una sola vez.
"""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

from . import theme
from .profile import missing as _missing

__all__ = [
    "ranking",
    "distributions",
    "boxes",
    "correlation_heatmap",
    "scaling_comparison",
    "missing_matrix",
    "pairs",
]

#: Sobre esta cantidad de columnas, un pairplot deja de ser legible.
_PAIRS_SOFT_LIMIT = 8


def _numeric_columns(df: pd.DataFrame, columns: list[str] | None = None) -> list[str]:
    if columns is not None:
        missing_cols = [c for c in columns if c not in df.columns]
        if missing_cols:
            raise KeyError(f"columnas ausentes en el DataFrame: {missing_cols}")
        return list(columns)
    return df.select_dtypes(include=np.number).columns.tolist()


def _is_discrete(serie: pd.Series, *, max_levels: int = 12) -> bool:
    """¿Conviene contar en vez de estimar densidad?

    Verdadero para enteros con pocos niveles distintos: escalas Likert, conteos
    pequeños, calificaciones. Sobre ellos un KDE dibuja masa donde no hay datos.
    """
    if not pd.api.types.is_numeric_dtype(serie):
        return False
    valores = serie.dropna()
    if valores.empty or valores.nunique() > max_levels:
        return False
    return bool(np.allclose(valores, valores.round()))


def _grid(n: int, num_rows: int | None, num_cols: int | None) -> tuple[int, int]:
    """Calcula una grilla que siempre contiene los n paneles."""
    if num_rows and num_cols:
        if num_rows * num_cols < n:
            raise ValueError(f"la grilla {num_rows}x{num_cols} no cabe {n} paneles")
        return num_rows, num_cols
    cols = num_cols or max(1, int(math.ceil(math.sqrt(n))))
    rows = num_rows or max(1, int(math.ceil(n / cols)))
    return rows, cols


def _subplots(n: int, num_rows, num_cols, panel=(4.2, 3.2)) -> tuple[Figure, np.ndarray]:
    """subplots() que SIEMPRE devuelve un arreglo plano de ejes.

    Este helper existe por un bug concreto: `plt.subplots(1, 1)` devuelve un
    `Axes` suelto, no un arreglo, y llamarle `.flatten()` revienta. El código
    original fallaba con datasets de una sola columna numérica.
    """
    rows, cols = _grid(n, num_rows, num_cols)
    fig, axes = plt.subplots(
        rows, cols, figsize=(panel[0] * cols, panel[1] * rows), squeeze=False
    )
    return fig, axes.flatten()


def _hide_unused(fig: Figure, axes: np.ndarray, used: int) -> None:
    for ax in axes[used:]:
        fig.delaxes(ax)


def _empty_figure(message: str) -> Figure:
    """Figura con un mensaje, para el caso sin datos que graficar.

    Devolver una figura vacía y honesta es mejor que lanzar una excepción a
    mitad de un notebook: el análisis sigue y el vacío queda a la vista.
    """
    fig, ax = plt.subplots(figsize=(6, 1.6))
    ax.text(0.5, 0.5, message, ha="center", va="center",
            color=theme.active().text_secondary, fontsize=10)
    ax.set_axis_off()
    return fig


def distributions(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    *,
    num_rows: int | None = None,
    num_cols: int | None = None,
    title: str | None = None,
) -> Figure:
    """Densidad (KDE) de cada variable numérica."""
    cols = _numeric_columns(df, columns)
    if not cols:
        return _empty_figure("Sin columnas numéricas que graficar")

    color = theme.categorical(1)[0]
    fig, axes = _subplots(len(cols), num_rows, num_cols)
    # `strict=False` a propósito: la rejilla se redondea hacia arriba, así
    # que `axes` puede ser más largo que `cols`. `_hide_unused` borra los
    # sobrantes; truncar acá es lo correcto, no un descuido.
    for ax, col in zip(axes, cols, strict=False):
        serie = df[col].dropna()
        # Una columna constante no tiene densidad que estimar: seaborn avisa y
        # dibuja un panel vacío. Es más honesto decirlo.
        if serie.nunique() <= 1:
            ax.text(0.5, 0.5, "constante", transform=ax.transAxes, ha="center",
                    va="center", color=theme.active().text_secondary, fontsize=9)
            ax.set_xticks([])
            ax.set_yticks([])
        elif _is_discrete(serie):
            # Un KDE sobre una variable discreta inventa una curva continua
            # entre valores que no existen. La forma correcta es el conteo.
            counts = serie.value_counts().sort_index()
            ax.bar(counts.index, counts.to_numpy(), color=color, width=0.65)
            ax.set_xticks(list(counts.index))
        else:
            sns.kdeplot(data=serie, ax=ax, fill=True, color=color, alpha=0.35, linewidth=2)
        ax.set_title(col)
        ax.set_xlabel("")
        ax.set_ylabel("")
    _hide_unused(fig, axes, len(cols))
    if title:
        fig.suptitle(title, x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    return fig


def boxes(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    *,
    by: str | None = None,
    num_rows: int | None = None,
    num_cols: int | None = None,
    title: str | None = None,
) -> Figure:
    """Cajas por variable, opcionalmente segmentadas por una categórica (`by`)."""
    cols = _numeric_columns(df, columns)
    if by is not None and by in cols:
        cols = [c for c in cols if c != by]
    if not cols:
        return _empty_figure("Sin columnas numéricas que graficar")

    if by is not None:
        n_levels = df[by].nunique(dropna=True)
        colors = theme.categorical(min(n_levels, theme.MAX_SERIES))
        palette = colors if n_levels <= theme.MAX_SERIES else None
    else:
        palette = None

    single = theme.categorical(1)[0]
    fig, axes = _subplots(len(cols), num_rows, num_cols)
    # `strict=False` a propósito: la rejilla se redondea hacia arriba, así
    # que `axes` puede ser más largo que `cols`. `_hide_unused` borra los
    # sobrantes; truncar acá es lo correcto, no un descuido.
    for ax, col in zip(axes, cols, strict=False):
        if by is None:
            sns.boxplot(data=df, y=col, ax=ax, color=single, width=0.4, fliersize=3)
        else:
            sns.boxplot(data=df, x=by, y=col, hue=by, ax=ax, palette=palette,
                        width=0.6, fliersize=3, legend=False)
        ax.set_title(col)
        ax.set_ylabel("")
    _hide_unused(fig, axes, len(cols))
    if title:
        fig.suptitle(title, x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    return fig


def correlation_heatmap(
    df: pd.DataFrame,
    *,
    method: str = "pearson",
    annot: bool | None = None,
    title: str = "Matriz de correlación",
) -> Figure:
    """Correlaciones, con escala divergente y triángulo superior oculto.

    La escala es divergente con gris al centro porque la correlación tiene
    polaridad: -1 y +1 son opuestos y 0 es "nada". Una rampa tipo arcoíris
    inventa categorías donde hay un continuo.

    `annot` se decide solo: sobre 15 variables, los números no se leen y se
    apagan. Puedes forzarlo.
    """
    num = df.select_dtypes(include=np.number)
    if num.shape[1] < 2:
        return _empty_figure("Se necesitan al menos 2 columnas numéricas")

    corr = num.corr(method=method)
    # La máscara se calcula sobre la matriz completa y se recorta junto con
    # ella: recalcularla después del recorte tapa el triángulo equivocado.
    mask = np.triu(np.ones_like(corr, dtype=bool))
    if corr.shape[0] > 2:
        corr, mask = corr.iloc[1:, :-1], mask[1:, :-1]
    n = corr.shape[0]
    if annot is None:
        annot = n <= 15

    size = max(5.0, 0.55 * n + 2.0)
    fig, ax = plt.subplots(figsize=(size, size * 0.85))
    sns.heatmap(
        corr,
        mask=mask,
        cmap=theme.diverging_cmap(),
        vmin=-1, vmax=1, center=0,
        annot=annot, fmt=".2f",
        annot_kws={"size": 8},
        linewidths=2, linecolor=theme.active().surface,
        square=True, cbar_kws={"shrink": 0.6, "label": f"r ({method})"},
        ax=ax,
    )
    ax.set_title(title)
    ax.grid(False)  # la grilla del tema se cuela por las celdas enmascaradas
    fig.tight_layout()
    return fig


def scaling_comparison(
    original: pd.DataFrame,
    scaled: pd.DataFrame | np.ndarray,
    features: list[str],
    *,
    num_rows: int | None = None,
    num_cols: int | None = None,
    title: str = "Distribución antes y después de escalar",
) -> Figure:
    """Compara la densidad de cada variable antes y después del escalado.

    Sirve para verificar que el escalador hizo lo que esperabas: `robust` debe
    dejar las colas donde estaban y `standard` centrar en cero.
    """
    if not features:
        return _empty_figure("Sin variables que comparar")
    if isinstance(scaled, np.ndarray):
        scaled = pd.DataFrame(scaled, columns=features, index=original.index)

    missing_cols = [c for c in features if c not in original.columns or c not in scaled.columns]
    if missing_cols:
        raise KeyError(f"columnas ausentes en original o scaled: {missing_cols}")

    c_before, c_after = theme.categorical(2)
    fig, axes = _subplots(len(features), num_rows, num_cols)
    # Misma razón que arriba: sobran ejes y se borran después.
    for ax, feat in zip(axes, features, strict=False):
        sns.kdeplot(data=original[feat].dropna(), ax=ax, fill=True, alpha=0.3,
                    color=c_before, linewidth=2, label="Original")
        sns.kdeplot(data=scaled[feat].dropna(), ax=ax, fill=True, alpha=0.3,
                    color=c_after, linewidth=2, label="Escalado")
        ax.set_title(feat)
        ax.set_xlabel("")
        ax.set_ylabel("")
    _hide_unused(fig, axes, len(features))
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncols=2)
    fig.suptitle(title, x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    return fig


def missing_matrix(df: pd.DataFrame, *, title: str = "Patrón de datos faltantes") -> Figure:
    """Dónde están los nulos, fila por fila.

    El conteo por columna no distingue entre nulos dispersos y un bloque
    contiguo — y esa diferencia decide si imputas o descartas el tramo.
    """
    miss = _missing(df, only_missing=True)
    if miss.empty:
        return _empty_figure("Sin datos faltantes")

    cols = miss.index.tolist()
    fig, ax = plt.subplots(figsize=(max(6.0, 0.6 * len(cols) + 3), 4.5))
    ax.imshow(
        df[cols].isna().to_numpy(dtype=float),
        aspect="auto", interpolation="nearest",
        cmap=theme.sequential_cmap(),
    )
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right")
    ax.set_ylabel("fila")
    ax.set_title(title)
    ax.grid(False)
    fig.tight_layout()
    return fig


def pairs(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    *,
    hue: str | None = None,
    title: str | None = None,
) -> Figure:
    """Dispersión cruzada de variables.

    Forma que compara todos los pares a la vez: `hue` admite como máximo 3
    niveles. Es el límite en que los colores siguen siendo distinguibles para
    daltonismo en todas las combinaciones — con más, el gráfico miente.
    """
    cols = _numeric_columns(df, columns)
    if hue is not None and hue in cols:
        cols = [c for c in cols if c != hue]
    if len(cols) < 2:
        return _empty_figure("Se necesitan al menos 2 columnas numéricas")
    if len(cols) > _PAIRS_SOFT_LIMIT:
        raise ValueError(
            f"{len(cols)} variables generan {len(cols) ** 2} paneles ilegibles. "
            f"Pasa `columns` con las {_PAIRS_SOFT_LIMIT} más relevantes — "
            "`stats.target_report` te dice cuáles."
        )

    if hue is not None:
        n_levels = df[hue].nunique(dropna=True)
        palette = theme.categorical(n_levels, all_pairs=True)
    else:
        palette = None

    grid = sns.pairplot(
        df[cols + ([hue] if hue else [])],
        hue=hue,
        palette=palette,
        plot_kws={"s": 18, "alpha": 0.6, "edgecolor": "none"},
        diag_kws={"fill": True, "alpha": 0.35},
        corner=True,
    )
    if hue is None:
        color = theme.categorical(1)[0]
        for ax in grid.figure.axes:
            for coll in ax.collections:
                coll.set_facecolor(color)
    if title:
        grid.figure.suptitle(title, x=0.01, ha="left", fontsize=13)
    grid.figure.tight_layout()
    return grid.figure


def ranking(
    valores: pd.Series,
    *,
    title: str = "",
    xlabel: str = "",
    top: int | None = 15,
    highlight: float | None = None,
) -> Figure:
    """Barras horizontales ordenadas de mayor a menor.

    La forma correcta cuando comparas una magnitud entre categorías con
    nombres largos: horizontal deja leer las etiquetas sin rotarlas, y el
    orden hace el trabajo que un gráfico de torta le deja al lector.

    `highlight` dibuja una línea de referencia (un umbral, un promedio).
    """
    serie = valores.dropna().sort_values(ascending=False)
    if serie.empty:
        return _empty_figure("Sin valores que ordenar")
    if top is not None:
        serie = serie.head(top)
    serie = serie.iloc[::-1]  # matplotlib dibuja de abajo hacia arriba

    color = theme.categorical(1)[0]
    alto = max(2.2, 0.32 * len(serie) + 1.2)
    fig, ax = plt.subplots(figsize=(7.5, alto))
    ax.barh(serie.index.astype(str), serie.to_numpy(), color=color, height=0.65)
    if highlight is not None:
        ax.axvline(highlight, color=theme.active().text_secondary,
                   linewidth=1, linestyle="--", zorder=0)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", visible=True)
    fig.tight_layout()
    return fig
