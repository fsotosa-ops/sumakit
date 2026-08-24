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
    assert "cola pesada" in out.loc["sesgada", "reason"]
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
    pares = {frozenset([a, b]) for a, b in zip(out["feature_a"], out["feature_b"], strict=True)}
    assert frozenset(["normal", "copia_normal"]) in pares


def test_high_correlation_pairs_vacio_si_no_hay():
    d = pd.DataFrame({"a": [1, 2, 3, 4], "b": [4, 1, 3, 2]})
    assert stats.high_correlation_pairs(d, threshold=0.99).empty


def test_target_report_ordena_por_fuerza(df):
    out = stats.target_report(df, "objetivo")
    assert out.index[0] in ("normal", "copia_normal")
    assert out["abs_corr"].is_monotonic_decreasing


def test_target_report_incluye_informacion_mutua(df):
    """La información mutua es opcional: depende de scikit-learn."""
    pytest.importorskip("sklearn")
    out = stats.target_report(df, "objetivo")
    assert "mutual_info" in out.columns


def test_target_report_funciona_sin_sklearn(df, monkeypatch):
    """Sin scikit-learn debe seguir dando la correlación, no reventar."""
    import builtins
    real = builtins.__import__

    def sin_sklearn(nombre, *a, **k):
        if nombre.startswith("sklearn"):
            raise ImportError("simulado")
        return real(nombre, *a, **k)

    monkeypatch.setattr(builtins, "__import__", sin_sklearn)
    out = stats.target_report(df, "objetivo")
    assert "corr" in out.columns and "mutual_info" not in out.columns


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


# --- el consejo depende de la naturaleza de la variable, no solo de su forma --

@pytest.fixture
def df_mixto():
    """Composicionales, una acotada suelta, magnitudes y un identificador."""
    rng = np.random.default_rng(11)
    n = 400
    a = rng.dirichlet([2, 3, 5], n)
    return pd.DataFrame({
        "id": np.arange(n),
        "manana": a[:, 0], "tarde": a[:, 1], "noche": a[:, 2],
        "tasa_suelta": rng.uniform(0, 1, n),
        "monto": rng.exponential(5000, n),
        "edad": rng.integers(18, 80, n).astype(float),
    })


def test_no_sugiere_escalar_lo_composicional(df_mixto):
    out = stats.distribution_report(df_mixto)
    for col in ("manana", "tarde", "noche"):
        assert out.loc[col, "suggested_scaler"] == "ninguno"
        assert out.loc[col, "composicional"]
        assert "log-ratio" in out.loc[col, "reason"]


def test_no_sugiere_escalar_lo_ya_acotado(df_mixto):
    out = stats.distribution_report(df_mixto)
    assert out.loc["tasa_suelta", "acotada"]
    assert out.loc["tasa_suelta", "suggested_scaler"] == "ninguno"


def test_no_marca_como_acotada_una_variable_positiva_cualquiera(df_mixto):
    """Una edad entre 18 y 80 no es una proporción."""
    out = stats.distribution_report(df_mixto)
    assert not out.loc["edad", "acotada"]


def test_puede_pedirse_la_escala_0_100():
    d = pd.DataFrame({"pct": np.linspace(0, 100, 50), "otra": np.linspace(0, 100, 50)})
    suelto = stats.distribution_report(d, compositional=False)
    con100 = stats.distribution_report(d, compositional=False, bounded_ceilings=(1.0, 100.0))
    assert not suelto.loc["pct", "acotada"]
    assert con100.loc["pct", "acotada"]


def test_omite_los_identificadores(df_mixto):
    assert "id" not in stats.distribution_report(df_mixto).index


def test_las_magnitudes_siguen_recibiendo_consejo(df_mixto):
    out = stats.distribution_report(df_mixto)
    assert out.loc["monto", "suggested_scaler"] == "robust"
    assert "cola pesada" in out.loc["monto", "reason"]


def test_distingue_masa_en_cero_de_cola_pesada():
    """Escalar no arregla una masa de ceros; decirlo evita un consejo inútil."""
    rng = np.random.default_rng(3)
    x = rng.exponential(2, 1000) * 100
    x[: 700] = 0.0                      # 70% de ceros
    d = pd.DataFrame({"con_ceros": x})
    out = stats.distribution_report(d, compositional=False)
    assert "masa en cero" in out.loc["con_ceros", "reason"]
    assert out.loc["con_ceros", "pct_zeros"] >= 60
