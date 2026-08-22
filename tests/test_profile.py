"""Las tablas de perfilado devuelven DataFrames sobre los que se puede afirmar."""

import pandas as pd

from sumakit import profile


def test_overview_cuenta_nulos_y_porcentajes(df):
    out = profile.overview(df)
    assert out.loc["con_nulos", "n_missing"] == 50
    assert out.loc["con_nulos", "pct_missing"] == round(100 * 50 / len(df), 2)
    assert out.loc["normal", "n_missing"] == 0


def test_overview_marca_las_constantes(df):
    out = profile.overview(df)
    assert bool(out.loc["constante", "is_constant"])
    assert not bool(out.loc["normal", "is_constant"])


def test_overview_con_dataframe_vacio():
    out = profile.overview(pd.DataFrame())
    assert out.empty
    assert "pct_missing" in out.columns


def test_missing_solo_lista_lo_que_falta(df):
    out = profile.missing(df)
    assert list(out.index) == ["con_nulos"]
    assert out.loc["con_nulos", "pct_missing"] > 0


def test_missing_puede_listar_todo(df):
    out = profile.missing(df, only_missing=False)
    assert len(out) == df.shape[1]


def test_cardinality_detecta_niveles_raros(df):
    out = profile.cardinality(df, rare_threshold=10.0)
    assert out.loc["categoria", "n_levels"] == 3
    assert out.loc["categoria", "top_level"] == "a"
    assert out.loc["categoria", "n_rare_levels"] == 1  # 'c' está en 5%


def test_cardinality_sin_categoricas():
    out = profile.cardinality(pd.DataFrame({"x": [1, 2, 3]}))
    assert out.empty


def test_duplicates_por_subconjunto():
    d = pd.DataFrame({"id": [1, 1, 2], "v": ["a", "b", "c"]})
    assert profile.duplicates(d)["n_duplicated_rows"] == 0
    assert profile.duplicates(d, subset=["id"])["n_duplicated_rows"] == 2


def test_constant_columns(df):
    assert profile.constant_columns(df) == ["constante"]


# --- alertas ----------------------------------------------------------------

def test_alerts_ordena_por_gravedad(df):
    out = profile.alerts(df)
    severidades = list(out["severidad"])
    assert severidades == sorted(severidades, key=["crítica", "alta", "media"].index)


def test_alerts_detecta_identificador():
    d = pd.DataFrame({"id": range(50), "v": [1.0] * 25 + [2.0] * 25})
    out = profile.alerts(d)
    assert "identificador" in set(out["chequeo"])


def test_alerts_detecta_constante(df):
    out = profile.alerts(df)
    fila = out[out["chequeo"] == "constante"]
    assert not fila.empty and "constante" in fila.iloc[0]["columnas"]


def test_alerts_detecta_colinealidad(df):
    out = profile.alerts(df)
    assert "colinealidad" in set(out["chequeo"])


def test_alerts_marca_composicional_como_critica():
    import numpy as np
    rng = np.random.default_rng(5)
    a = rng.dirichlet([2, 2, 2], 200)
    d = pd.DataFrame({"m": a[:, 0], "t": a[:, 1], "n": a[:, 2]})
    out = profile.alerts(d)
    fila = out[out["chequeo"] == "composicional"]
    assert not fila.empty
    assert fila.iloc[0]["severidad"] == "crítica", "es lo que rompe el modelo: va primero"


def test_alerts_sobre_datos_limpios_no_alarma():
    import numpy as np
    rng = np.random.default_rng(2)
    d = pd.DataFrame({"a": rng.normal(0, 1, 200), "b": rng.normal(5, 2, 200)})
    out = profile.alerts(d)
    assert out.empty or "crítica" not in set(out["severidad"])


def test_alerts_puede_saltarse_la_busqueda_composicional(df):
    out = profile.alerts(df, compositional=False)
    assert "composicional" not in set(out["chequeo"])


# --- estilo -----------------------------------------------------------------

def test_styled_devuelve_un_styler_no_un_dataframe(df):
    from pandas.io.formats.style import Styler
    st = profile.styled(profile.overview(df))
    assert isinstance(st, Styler)


def test_styled_oculta_la_columna_de_memoria(df):
    st = profile.styled(profile.overview(df))
    assert "memory_kb" not in st.to_html()


def test_las_funciones_siguen_devolviendo_dataframes(df):
    """El estilo es una capa aparte: no debe contaminar el valor de retorno."""
    assert isinstance(profile.overview(df), pd.DataFrame)
    assert isinstance(profile.alerts(df), pd.DataFrame)
