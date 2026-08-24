"""Perfilado de un DataFrame: tablas, no gráficos.

La separación es deliberada. Un número atrapado dentro de un PNG no se puede
comparar, ordenar, ni afirmar en un test. Estas funciones devuelven DataFrames
para que puedas encadenarlos, incrustarlos en un informe o escribir
`assert overview(df)["pct_missing"].max() == 0` en una tubería.
"""

from __future__ import annotations

import pandas as pd

__all__ = [
    "alerts",
    "styled",
    "as_markdown",
    "overview",
    "missing",
    "cardinality",
    "duplicates",
    "duplicated_rows",
    "constant_columns",
]

_ORDEN = ["crítica", "alta", "media"]


def overview(df: pd.DataFrame) -> pd.DataFrame:
    """Los primeros treinta segundos con un dataset, en una tabla.

    Por columna: tipo, nulos, únicos, ceros, memoria y si es constante.
    """
    if df.shape[1] == 0:
        return pd.DataFrame(
            columns=[
                "dtype",
                "n_missing",
                "pct_missing",
                "n_unique",
                "pct_unique",
                "n_zeros",
                "pct_zeros",
                "memory_kb",
                "is_constant",
            ]
        )

    n = len(df)
    rows = []
    for col in df.columns:
        s = df[col]
        n_missing = int(s.isna().sum())
        n_unique = int(s.nunique(dropna=True))
        if pd.api.types.is_numeric_dtype(s):
            n_zeros = int((s == 0).sum())
        else:
            n_zeros = 0
        rows.append(
            {
                "dtype": str(s.dtype),
                "n_missing": n_missing,
                "pct_missing": round(100 * n_missing / n, 2) if n else 0.0,
                "n_unique": n_unique,
                "pct_unique": round(100 * n_unique / n, 2) if n else 0.0,
                "n_zeros": n_zeros,
                "pct_zeros": round(100 * n_zeros / n, 2) if n else 0.0,
                "memory_kb": round(s.memory_usage(deep=True) / 1024, 1),
                "is_constant": n_unique <= 1,
            }
        )
    return pd.DataFrame(rows, index=pd.Index(df.columns, name="column"))


def missing(df: pd.DataFrame, *, only_missing: bool = True) -> pd.DataFrame:
    """Nulos por columna, con porcentaje y ordenados de mayor a menor.

    Sustituye a `nan_checking`, que devolvía solo el conteo: sin el porcentaje
    no se puede decidir entre imputar y descartar.
    """
    n = len(df)
    counts = df.isna().sum()
    out = pd.DataFrame(
        {
            "n_missing": counts.astype(int),
            "pct_missing": (100 * counts / n).round(2) if n else 0.0,
        }
    )
    out.index.name = "column"
    if only_missing:
        out = out[out["n_missing"] > 0]
    return out.sort_values("n_missing", ascending=False)


def cardinality(df: pd.DataFrame, *, rare_threshold: float = 1.0) -> pd.DataFrame:
    """Perfil de las columnas no numéricas.

    `rare_threshold` es el porcentaje bajo el cual un nivel se considera raro:
    son los que revientan un one-hot encoding o desaparecen en el split.
    """
    cat_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    if not cat_cols:
        return pd.DataFrame(columns=["n_levels", "top_level", "pct_top", "n_rare_levels"])

    n = len(df)
    rows = []
    for col in cat_cols:
        vc = df[col].value_counts(dropna=True)
        pct = 100 * vc / n if n else vc
        rows.append(
            {
                "n_levels": int(vc.size),
                "top_level": vc.index[0] if vc.size else None,
                "pct_top": round(float(pct.iloc[0]), 2) if vc.size else 0.0,
                "n_rare_levels": int((pct < rare_threshold).sum()),
            }
        )
    return pd.DataFrame(rows, index=pd.Index(cat_cols, name="column"))


def duplicates(
    df: pd.DataFrame,
    subset: list[str] | None = None,
    *,
    label: str | None = None,
) -> pd.DataFrame:
    """Resumen de filas repetidas, como tabla de una fila.

    Devuelve un DataFrame —no un diccionario— para que se pueda concatenar,
    ordenar y afirmar igual que el resto de la librería. Con `label` puedes
    nombrar cada corte y compararlos de una sola vez:

        pd.concat([
            profile.duplicates(df, label="todo"),
            profile.duplicates(df, ["CLIENTE"], label="llave"),
            profile.duplicates(df, comportamiento, label="comportamiento"),
        ])

    Las columnas responden preguntas distintas, y dos se confunden con
    facilidad. Con seis filas donde 1,2,3 son iguales entre sí y 4,5 también:

        filas_con_gemelo       5   las que tienen al menos un igual (la 6 no)
        grupos                 2   {1,2,3} y {4,5}
        mayor_grupo            3
        sobrantes              3   dos del primer grupo, una del segundo
        filas_tras_deduplicar  3   un representante de cada grupo, más la 6

    O sea: cinco filas *están involucradas*, pero solo tres *sobran*, porque
    de cada grupo se conserva una.
    """
    cols = list(subset) if subset is not None else list(df.columns)
    faltan = [c for c in cols if c not in df.columns]
    if faltan:
        raise KeyError(f"columnas ausentes en el DataFrame: {faltan}")

    n = len(df)
    todas = df.duplicated(subset=cols, keep=False)
    extras = df.duplicated(subset=cols, keep="first")
    n_dup = int(todas.sum())
    n_extra = int(extras.sum())
    # Un grupo de tamaño k aporta k filas con keep=False y k-1 con keep="first":
    # la diferencia es exactamente la cantidad de grupos.
    n_grupos = n_dup - n_extra

    if n_dup:
        tamaños = df.loc[todas].groupby(cols, observed=True, dropna=False).size()
        mayor = int(tamaños.max())
    else:
        mayor = 0

    fila = {
        "filas": n,
        "columnas_comparadas": len(cols),
        "filas_con_gemelo": n_dup,
        "pct_con_gemelo": round(100 * n_dup / n, 2) if n else 0.0,
        "grupos": n_grupos,
        "mayor_grupo": mayor,
        "sobrantes": n_extra,
        "filas_tras_deduplicar": n - n_extra,
    }
    nombre = label or ("todas las columnas" if subset is None else f"{len(cols)} columnas")
    return pd.DataFrame([fila], index=pd.Index([nombre], name="subconjunto"))


def duplicated_rows(
    df: pd.DataFrame,
    subset: list[str] | None = None,
    *,
    max_groups: int | None = 20,
) -> pd.DataFrame:
    """Las filas repetidas, agrupadas y etiquetadas para poder mirarlas.

    Ordenar por las columnas del subconjunto deja las filas idénticas
    adyacentes, pero no dice dónde termina un grupo y empieza el siguiente.
    Aquí cada fila lleva `_grupo` y `_tamaño`, y los grupos más grandes van
    primero, que son los que suelen delatar el origen del problema.

    `max_groups` recorta la cantidad de grupos, no de filas: así nunca se
    muestra un grupo partido por la mitad.
    """
    cols = list(subset) if subset is not None else list(df.columns)
    faltan = [c for c in cols if c not in df.columns]
    if faltan:
        raise KeyError(f"columnas ausentes en el DataFrame: {faltan}")

    mascara = df.duplicated(subset=cols, keep=False)
    if not mascara.any():
        vacio = df.head(0).copy()
        vacio.insert(0, "_tamaño", pd.Series(dtype=int))
        vacio.insert(0, "_grupo", pd.Series(dtype=int))
        return vacio

    filas = df.loc[mascara].copy()
    grupos = filas.groupby(cols, observed=True, dropna=False, sort=False)
    filas.insert(0, "_grupo", grupos.ngroup() + 1)
    filas.insert(1, "_tamaño", filas.groupby("_grupo")["_grupo"].transform("size"))

    filas = filas.sort_values(["_tamaño", "_grupo"], ascending=[False, True])
    if max_groups is not None:
        conservar = filas["_grupo"].drop_duplicates().head(max_groups)
        filas = filas[filas["_grupo"].isin(conservar)]
    return filas


def constant_columns(df: pd.DataFrame) -> list[str]:
    """Columnas con un solo valor: no aportan señal y ensucian el modelo."""
    return [c for c in df.columns if df[c].nunique(dropna=True) <= 1]


def alerts(
    df: pd.DataFrame,
    *,
    missing_pct: float = 20.0,
    zeros_pct: float = 40.0,
    skew: float = 1.0,
    corr: float = 0.95,
    max_levels: int = 50,
    compositional: bool = True,
) -> pd.DataFrame:
    """Qué revisar antes de modelar, ordenado por gravedad.

    Las tablas describen; esto señala. Devuelve una fila por hallazgo, con las
    columnas involucradas y qué hacer al respecto, de lo crítico a lo menor.

    Es lo primero que conviene mirar de un dataset nuevo: `overview` te da 200
    números sin jerarquía, esto te dice dónde están los tres que importan.
    """
    from . import stats as _stats

    n = len(df)
    hallazgos: list[dict] = []

    def añadir(severidad, chequeo, columnas, mensaje):
        hallazgos.append(
            {
                "severidad": severidad,
                "chequeo": chequeo,
                "columnas": ", ".join(columnas)
                if isinstance(columnas, (list, tuple))
                else columnas,
                "mensaje": mensaje,
            }
        )

    # --- dependencia lineal exacta: rompe clustering, PCA y regresión --------
    if compositional:
        grupos = _stats.sum_constant_groups(df)
        for _, g in grupos.iterrows():
            añadir(
                "crítica",
                "composicional",
                g["columns"],
                f"{g['n_columns']} columnas que suman siempre {g['constant']:g}: "
                "una queda determinada por las otras. Elimina una categoría del "
                "grupo o aplica una transformación log-ratio antes de modelar.",
            )

    ov = overview(df)

    # --- identificadores ----------------------------------------------------
    ids = [
        c
        for c in df.columns
        if ov.loc[c, "n_unique"] == n and n > 0 and not pd.api.types.is_float_dtype(df[c])
    ]
    if ids:
        añadir(
            "alta",
            "identificador",
            ids,
            "un valor distinto por fila: es una llave, no una variable. Excluir del modelo.",
        )

    # --- duplicados ---------------------------------------------------------
    dup = duplicates(df).iloc[0]
    if dup["filas_con_gemelo"]:
        añadir(
            "alta",
            "duplicados",
            "(filas)",
            f"{dup['filas_con_gemelo']} filas repetidas en {dup['grupos']} grupos "
            f"({dup['pct_con_gemelo']}%): revisa si el dataset viene de un join.",
        )

    # --- colinealidad -------------------------------------------------------
    pares = _stats.high_correlation_pairs(df, threshold=corr)
    if not pares.empty:
        detalle = "; ".join(
            f"{a}~{b} (r={r:.2f})"
            for a, b, r in zip(pares["feature_a"], pares["feature_b"], pares["r"], strict=True)
        )
        añadir(
            "alta",
            "colinealidad",
            sorted(set(pares["feature_a"]) | set(pares["feature_b"])),
            f"pares casi redundantes: {detalle}. Considera dejar una de cada par.",
        )

    # --- nulos --------------------------------------------------------------
    graves = ov.index[ov["pct_missing"] > 50].tolist()
    medios = ov.index[(ov["pct_missing"] > missing_pct) & (ov["pct_missing"] <= 50)].tolist()
    if graves:
        añadir(
            "alta",
            "nulos",
            graves,
            "más de la mitad de los valores ausentes: imputar aquí inventa datos.",
        )
    if medios:
        añadir(
            "media",
            "nulos",
            medios,
            f"entre {missing_pct:g}% y 50% de nulos: decide imputación o descarte.",
        )

    # --- ceros: importan porque el logaritmo de cero no existe --------------
    muchos_ceros = ov.index[ov["pct_zeros"] > zeros_pct].tolist()
    if muchos_ceros:
        añadir(
            "media",
            "ceros",
            muchos_ceros,
            f"más de {zeros_pct:g}% de ceros: bloquea transformaciones "
            "logarítmicas y log-ratio, que no admiten cero.",
        )

    # --- constantes ---------------------------------------------------------
    constantes = constant_columns(df)
    if constantes:
        añadir("media", "constante", constantes, "un solo valor: sin señal, se puede descartar.")

    # --- asimetría ----------------------------------------------------------
    forma = _stats.distribution_report(df, skew_threshold=skew)
    sesgadas = forma.index[forma["suggested_scaler"] == "robust"].tolist()
    if sesgadas:
        añadir(
            "media",
            "asimetría",
            sesgadas,
            "distribuciones sesgadas o con muchos outliers: escalado robusto en vez de estándar.",
        )

    # --- cardinalidad -------------------------------------------------------
    card = cardinality(df)
    if not card.empty:
        altas = card.index[card["n_levels"] > max_levels].tolist()
        if altas:
            añadir(
                "media",
                "cardinalidad",
                altas,
                f"más de {max_levels} niveles: un one-hot generaría cientos de "
                "columnas. Agrupa niveles o úsala solo para perfilar.",
            )

    if not hallazgos:
        return pd.DataFrame(columns=["severidad", "chequeo", "columnas", "mensaje"])

    out = pd.DataFrame(hallazgos)
    out["severidad"] = pd.Categorical(out["severidad"], categories=_ORDEN, ordered=True)
    return out.sort_values("severidad").reset_index(drop=True)


# Columnas conocidas y cómo se leen mejor.
_BARRAS = ("pct_missing", "pct_zeros", "pct_unique", "pct_outliers", "pct_top")
_DIVERGENTES = ("skew", "kurtosis", "corr", "r", "abs_corr")


def styled(tabla: pd.DataFrame, *, hide: tuple[str, ...] = ("memory_kb",)):
    """Da formato visual a una tabla de esta librería. Devuelve un `Styler`.

    Va aparte a propósito: las funciones de perfilado siguen devolviendo
    DataFrames, que se pueden ordenar, filtrar y afirmar en un test. El estilo
    es una capa de presentación encima, no un reemplazo.

    Requiere `jinja2` (viene con la instalación).
    """
    from . import theme

    pal = theme.active()
    st = tabla.style

    ocultar = [c for c in hide if c in tabla.columns]
    if ocultar:
        st = st.hide(ocultar, axis="columns")

    barras = [c for c in _BARRAS if c in tabla.columns]
    if barras:
        st = st.bar(subset=barras, color=pal.categorical[0] + "55", vmin=0, vmax=100)
        st = st.format({c: "{:.1f}%" for c in barras})

    divergentes = [c for c in _DIVERGENTES if c in tabla.columns]
    if divergentes:
        st = st.background_gradient(
            subset=divergentes, cmap=theme.diverging_cmap(), vmin=-3, vmax=3
        )
        st = st.format({c: "{:.2f}" for c in divergentes})

    if "is_constant" in tabla.columns:
        st = st.map(
            lambda v: f"color: {pal.diverging_high}; font-weight: 600" if v else "",
            subset=["is_constant"],
        )

    if "severidad" in tabla.columns:
        colores = {
            "crítica": pal.diverging_high,
            "alta": pal.categorical[3],
            "media": pal.text_secondary,
        }
        st = st.map(
            lambda v: f"color: {colores.get(v, '')}; font-weight: 600",
            subset=["severidad"],
        )

    return st.set_properties(**{"font-size": "90%"})


def as_markdown(tabla: pd.DataFrame, *, index: bool = True, floatfmt: str = ",.10g"):
    """Convierte una tabla a markdown, para que sobreviva a PDF y a Word.

    Existe por una diferencia que no es obvia: un DataFrame se muestra como
    **HTML**, y Pandoc traduce ese HTML a un `tabular` de LaTeX con columnas
    rígidas. Si una celda trae una lista larga, la tabla se sale del margen y
    `tbl-colwidths` no puede hacer nada, porque esa opción solo aplica a tablas
    markdown.

    Emitida como markdown, la misma tabla respeta los anchos y parte el texto
    en varias líneas:

        #| tbl-colwidths: [12, 12, 76]
        profile.as_markdown(stats.sum_constant_groups(df))

    En el notebook se ve igual de bien; la diferencia aparece al renderizar.

    `floatfmt` usa diez cifras significativas y no cuatro: con cuatro, un monto
    de siete dígitos salta a notación científica. Es el mismo motivo por el que
    `nb.adaptive_float` existe.
    """
    from IPython.display import Markdown

    return Markdown(tabla.to_markdown(index=index, floatfmt=floatfmt))
