"""Diagnóstico estadístico: asimetría, outliers, correlación, colinealidad.

Estas funciones convierten en cálculo lo que normalmente se decide a ojo.
`distribution_report` es el caso claro: en vez de elegir a mano qué columnas
escalar con RobustScaler mirando los KDE, las ordena por asimetría y peso de
outliers y propone el escalador.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "distribution_report",
    "outliers",
    "correlations",
    "high_correlation_pairs",
    "target_report",
]

_IQR_MULTIPLIER = 1.5


def _numeric(df: pd.DataFrame) -> pd.DataFrame:
    return df.select_dtypes(include=np.number)


def outliers(df: pd.DataFrame, *, method: str = "iqr", threshold: float = 3.0) -> pd.DataFrame:
    """Outliers por columna, con los límites que los definen.

    - `iqr`: regla de Tukey, robusta y la que corresponde a distribuciones sesgadas.
    - `zscore`: |z| > threshold. Supone normalidad; la media y la desviación ya
      vienen contaminadas por los propios outliers.
    - `modified_zscore`: basado en mediana y MAD. Resiste la contaminación.
    """
    num = _numeric(df)
    if num.empty:
        return pd.DataFrame(columns=["n_outliers", "pct_outliers", "lower", "upper", "method"])

    rows = []
    for col in num.columns:
        s = num[col].dropna()
        if s.empty:
            rows.append({"n_outliers": 0, "pct_outliers": 0.0, "lower": np.nan,
                         "upper": np.nan, "method": method})
            continue

        if method == "iqr":
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            lower, upper = q1 - _IQR_MULTIPLIER * iqr, q3 + _IQR_MULTIPLIER * iqr
        elif method == "zscore":
            mu, sigma = s.mean(), s.std()
            if sigma == 0 or np.isnan(sigma):
                lower, upper = -np.inf, np.inf
            else:
                lower, upper = mu - threshold * sigma, mu + threshold * sigma
        elif method == "modified_zscore":
            med = s.median()
            mad = (s - med).abs().median()
            if mad == 0:
                lower, upper = -np.inf, np.inf
            else:
                delta = threshold * mad / 0.6745
                lower, upper = med - delta, med + delta
        else:
            raise ValueError(
                f"método '{method}' desconocido: usa 'iqr', 'zscore' o 'modified_zscore'"
            )

        mask = (s < lower) | (s > upper)
        n_out = int(mask.sum())
        rows.append({
            "n_outliers": n_out,
            "pct_outliers": round(100 * n_out / len(s), 2),
            "lower": float(lower),
            "upper": float(upper),
            "method": method,
        })
    return pd.DataFrame(rows, index=pd.Index(num.columns, name="column"))


def distribution_report(
    df: pd.DataFrame,
    *,
    skew_threshold: float = 1.0,
    outlier_threshold: float = 5.0,
) -> pd.DataFrame:
    """Forma de cada variable numérica, con el escalador que le corresponde.

    La sugerencia sigue una regla explícita, no una corazonada:

    - `robust`   — |asimetría| > umbral, o más de `outlier_threshold`% de outliers.
                   Mediana e IQR no se dejan arrastrar por las colas.
    - `standard` — el resto.

    Es una recomendación, no un veredicto: mira la columna `reason` y decide.
    """
    num = _numeric(df)
    if num.empty:
        return pd.DataFrame(columns=["skew", "kurtosis", "cv", "pct_outliers",
                                     "suggested_scaler", "reason"])

    out = outliers(num, method="iqr")
    rows = []
    for col in num.columns:
        s = num[col].dropna()
        skew = float(s.skew()) if len(s) > 2 else 0.0
        kurt = float(s.kurtosis()) if len(s) > 3 else 0.0
        mean = float(s.mean()) if len(s) else 0.0
        std = float(s.std()) if len(s) > 1 else 0.0
        cv = float(std / abs(mean)) if mean else np.nan
        pct_out = float(out.loc[col, "pct_outliers"])

        reasons = []
        if abs(skew) > skew_threshold:
            reasons.append(f"asimetría {skew:.2f}")
        if pct_out > outlier_threshold:
            reasons.append(f"{pct_out:.1f}% outliers")
        scaler = "robust" if reasons else "standard"

        rows.append({
            "skew": round(skew, 3),
            "kurtosis": round(kurt, 3),
            "cv": round(cv, 3) if not np.isnan(cv) else np.nan,
            "pct_outliers": pct_out,
            "suggested_scaler": scaler,
            "reason": "; ".join(reasons) if reasons else "distribución contenida",
        })
    return (
        pd.DataFrame(rows, index=pd.Index(num.columns, name="column"))
        .sort_values("skew", key=lambda s: s.abs(), ascending=False)
    )


def correlations(df: pd.DataFrame, *, method: str = "pearson") -> pd.DataFrame:
    """Matriz de correlación de las columnas numéricas.

    `spearman` cuando hay monotonía no lineal o colas pesadas, que es
    justamente cuando `pearson` engaña.
    """
    num = _numeric(df)
    if num.shape[1] < 2:
        return pd.DataFrame()
    return num.corr(method=method)


def high_correlation_pairs(
    df: pd.DataFrame, *, threshold: float = 0.9, method: str = "pearson"
) -> pd.DataFrame:
    """Pares de variables casi redundantes, ordenados por |r|.

    Es el chequeo de colinealidad que normalmente se hace mirando el heatmap y
    entrecerrando los ojos. Cada par es un candidato a que sobre una de las dos.
    """
    corr = correlations(df, method=method)
    if corr.empty:
        return pd.DataFrame(columns=["feature_a", "feature_b", "r", "abs_r"])

    mask = np.triu(np.ones(corr.shape, dtype=bool), k=1)
    pairs = (
        corr.where(mask)
        .stack()
        .reset_index()
        .rename(columns={"level_0": "feature_a", "level_1": "feature_b", 0: "r"})
    )
    pairs["abs_r"] = pairs["r"].abs()
    return (
        pairs[pairs["abs_r"] >= threshold]
        .sort_values("abs_r", ascending=False)
        .reset_index(drop=True)
    )


def target_report(df: pd.DataFrame, target: str, *, method: str = "pearson") -> pd.DataFrame:
    """Relación de cada variable numérica con el objetivo, ordenada por fuerza.

    Con `scikit-learn` instalado (`pip install minta[ml]`) agrega información
    mutua, que captura relaciones no lineales que la correlación no ve.

    Las columnas constantes quedan fuera: no aportan señal y solo ensucian la
    tabla con NaN.
    """
    if target not in df.columns:
        raise KeyError(f"la columna objetivo '{target}' no está en el DataFrame")

    num = _numeric(df)
    if target not in num.columns:
        raise TypeError(f"'{target}' no es numérica; target_report espera un objetivo numérico")

    # Una variable sin varianza no tiene relación con nada: su correlación es
    # NaN y numpy avisa por división por cero. Se excluye, igual que la
    # excluiría cualquier modelo.
    features = [
        c for c in num.columns
        if c != target and num[c].nunique(dropna=True) > 1
    ]
    if not features:
        return pd.DataFrame(columns=["corr", "abs_corr"])

    corr = num[features].corrwith(num[target], method=method)
    out = pd.DataFrame({"corr": corr.round(4), "abs_corr": corr.abs().round(4)})
    out.index.name = "feature"

    try:
        from sklearn.feature_selection import mutual_info_regression
    except ImportError:
        pass
    else:
        subset = num[features + [target]].dropna()
        if len(subset) > 3:
            mi = mutual_info_regression(
                subset[features], subset[target], random_state=0
            )
            out["mutual_info"] = pd.Series(mi, index=features).round(4)

    return out.sort_values("abs_corr", ascending=False)
