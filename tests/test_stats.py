"""El diagnóstico convierte en cálculo lo que se decidía a ojo."""

import numpy as np
import pandas as pd
import pytest

from sumakit import stats


def test_distribution_report_sugiere_robust_para_lo_sesgado(df):
    out = stats.distribution_report(df)
    assert out.loc["sesgada", "suggested_scaler"] == "robust"
    assert out.loc["normal", "suggested_scaler"] == "standard"


def test_la_razon_de_la_sugerencia_es_explicita(df):
    out = stats.distribution_report(df)
    assert "asimetría" in out.loc["sesgada", "reason"]
    assert out.loc["normal", "reason"] == "distribución contenida"


def test_report_ordenado_por_asimetria_absoluta(df):
    out = stats.distribution_report(df)
    assert out.index[0] == "sesgada", "la más sesgada debe encabezar"


def test_outliers_iqr_encuentra_el_extremo():
    d = pd.DataFrame({"x": [1, 2, 3, 4, 5, 1000]})
    out = stats.outliers(d, method="iqr")
    assert out.loc["x", "n_outliers"] == 1


def test_mediana_absoluta_resiste_contaminacion():
    """z-score clásico se deja arrastrar por el propio outlier; MAD no."""
    d = pd.DataFrame({"x": [1, 2, 3, 4, 5, 1000]})
    z = stats.outliers(d, method="zscore").loc["x", "n_outliers"]
    mz = stats.outliers(d, method="modified_zscore").loc["x", "n_outliers"]
    assert mz >= z


def test_metodo_desconocido_falla():
    with pytest.raises(ValueError, match="desconocido"):
        stats.outliers(pd.DataFrame({"x": [1, 2]}), method="inventado")


def test_high_correlation_pairs_encuentra_la_redundancia(df):
    out = stats.high_correlation_pairs(df, threshold=0.95)
    pares = {frozenset([a, b]) for a, b in zip(out["feature_a"], out["feature_b"])}
    assert frozenset(["normal", "copia_normal"]) in pares


def test_high_correlation_pairs_vacio_si_no_hay():
    d = pd.DataFrame({"a": [1, 2, 3, 4], "b": [4, 1, 3, 2]})
    assert stats.high_correlation_pairs(d, threshold=0.99).empty


def test_target_report_ordena_por_fuerza(df):
    out = stats.target_report(df, "objetivo")
    assert out.index[0] in ("normal", "copia_normal")
    assert out["abs_corr"].is_monotonic_decreasing


def test_target_report_incluye_informacion_mutua(df):
    out = stats.target_report(df, "objetivo")
    assert "mutual_info" in out.columns, "sklearn instalado: debe calcularla"


def test_target_report_objetivo_ausente(df):
    with pytest.raises(KeyError, match="no está"):
        stats.target_report(df, "inexistente")


def test_target_report_objetivo_no_numerico(df):
    with pytest.raises(TypeError, match="no es numérica"):
        stats.target_report(df, "categoria")


def test_correlations_spearman_vs_pearson():
    """En una relación monótona no lineal, spearman es 1 y pearson no."""
    x = np.arange(1, 30)
    d = pd.DataFrame({"x": x, "y": x ** 4})
    assert stats.correlations(d, method="spearman").loc["x", "y"] == pytest.approx(1.0)
    assert stats.correlations(d, method="pearson").loc["x", "y"] < 0.99


def test_target_report_excluye_constantes(df):
    """Sin varianza no hay relación: la columna no debe aparecer con NaN."""
    out = stats.target_report(df, "objetivo")
    assert "constante" not in out.index
    assert out["abs_corr"].notna().all()


# --- datos composicionales --------------------------------------------------

@pytest.fixture
def df_composicional():
    """Dos grupos que suman 1, más ruido que no forma parte de ninguno."""
    rng = np.random.default_rng(7)
    n = 400
    a = rng.dirichlet([2, 3, 5], n)          # tres partes que suman 1
    b = rng.dirichlet([1, 1], n)             # dos partes que suman 1
    return pd.DataFrame({
        "manana": a[:, 0], "tarde": a[:, 1], "noche": a[:, 2],
        "nacional": b[:, 0], "internacional": b[:, 1],
        "monto": rng.exponential(500, n),
        "n_trx": rng.integers(1, 90, n),
    })


def test_encuentra_los_grupos_que_suman_uno(df_composicional):
    g = stats.sum_constant_groups(df_composicional)
    grupos = {frozenset(c.strip() for c in fila.split(",")) for fila in g["columns"]}
    assert frozenset(["manana", "tarde", "noche"]) in grupos
    assert frozenset(["nacional", "internacional"]) in grupos


def test_no_arrastra_columnas_ajenas(df_composicional):
    g = stats.sum_constant_groups(df_composicional)
    todas = {c.strip() for fila in g["columns"] for c in fila.split(",")}
    assert "monto" not in todas and "n_trx" not in todas


def test_los_grupos_son_disjuntos(df_composicional):
    g = stats.sum_constant_groups(df_composicional)
    vistas = []
    for fila in g["columns"]:
        vistas += [c.strip() for c in fila.split(",")]
    assert len(vistas) == len(set(vistas)), "una columna no puede estar en dos grupos"


def test_detecta_composiciones_en_porcentaje():
    """El mismo caso pero en escala 0-100 en vez de 0-1."""
    rng = np.random.default_rng(3)
    a = rng.dirichlet([2, 2, 2], 200) * 100
    d = pd.DataFrame({"x": a[:, 0], "y": a[:, 1], "z": a[:, 2]})
    g = stats.sum_constant_groups(d)
    assert len(g) == 1
    assert g.loc[0, "constant"] == 100.0


def test_sin_composicion_no_inventa_grupos():
    rng = np.random.default_rng(1)
    d = pd.DataFrame(rng.exponential(3, (200, 5)), columns=list("abcde"))
    assert stats.sum_constant_groups(d).empty


def test_una_sola_columna_no_es_grupo():
    d = pd.DataFrame({"x": [1.0] * 10})
    assert stats.sum_constant_groups(d).empty
