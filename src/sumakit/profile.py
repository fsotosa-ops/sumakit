"""Perfilado de un DataFrame: tablas, no gráficos.

La separación es deliberada. Un número atrapado dentro de un PNG no se puede
comparar, ordenar, ni afirmar en un test. Estas funciones devuelven DataFrames
para que puedas encadenarlos, incrustarlos en un informe o escribir
`assert overview(df)["pct_missing"].max() == 0` en una tubería.
"""

from __future__ import annotations

import pandas as pd

__all__ = ["overview", "missing", "cardinality", "duplicates", "constant_columns"]


def overview(df: pd.DataFrame) -> pd.DataFrame:
    """Los primeros treinta segundos con un dataset, en una tabla.

    Por columna: tipo, nulos, únicos, ceros, memoria y si es constante.
    """
    if df.shape[1] == 0:
        return pd.DataFrame(
            columns=["dtype", "n_missing", "pct_missing", "n_unique", "pct_unique",
                     "n_zeros", "pct_zeros", "memory_kb", "is_constant"]
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
        rows.append({
            "dtype": str(s.dtype),
            "n_missing": n_missing,
            "pct_missing": round(100 * n_missing / n, 2) if n else 0.0,
            "n_unique": n_unique,
            "pct_unique": round(100 * n_unique / n, 2) if n else 0.0,
            "n_zeros": n_zeros,
            "pct_zeros": round(100 * n_zeros / n, 2) if n else 0.0,
            "memory_kb": round(s.memory_usage(deep=True) / 1024, 1),
            "is_constant": n_unique <= 1,
        })
    return pd.DataFrame(rows, index=pd.Index(df.columns, name="column"))


def missing(df: pd.DataFrame, *, only_missing: bool = True) -> pd.DataFrame:
    """Nulos por columna, con porcentaje y ordenados de mayor a menor.

    Sustituye a `nan_checking`, que devolvía solo el conteo: sin el porcentaje
    no se puede decidir entre imputar y descartar.
    """
    n = len(df)
    counts = df.isna().sum()
    out = pd.DataFrame({
        "n_missing": counts.astype(int),
        "pct_missing": (100 * counts / n).round(2) if n else 0.0,
    })
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
        rows.append({
            "n_levels": int(vc.size),
            "top_level": vc.index[0] if vc.size else None,
            "pct_top": round(float(pct.iloc[0]), 2) if vc.size else 0.0,
            "n_rare_levels": int((pct < rare_threshold).sum()),
        })
    return pd.DataFrame(rows, index=pd.Index(cat_cols, name="column"))


def duplicates(df: pd.DataFrame, subset: list[str] | None = None) -> dict:
    """Filas duplicadas, completas o según un subconjunto de llaves.

    Con `subset` responde la pregunta que importa antes de un join: ¿esta
    llave es única de verdad?
    """
    dup_mask = df.duplicated(subset=subset, keep=False)
    n_dup = int(dup_mask.sum())
    n = len(df)
    return {
        "n_duplicated_rows": n_dup,
        "pct_duplicated": round(100 * n_dup / n, 2) if n else 0.0,
        "n_unique_rows": int(n - df.duplicated(subset=subset, keep="first").sum()),
        "subset": subset,
    }


def constant_columns(df: pd.DataFrame) -> list[str]:
    """Columnas con un solo valor: no aportan señal y ensucian el modelo."""
    return [c for c in df.columns if df[c].nunique(dropna=True) <= 1]
