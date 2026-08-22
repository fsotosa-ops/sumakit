"""Las tablas de perfilado devuelven DataFrames sobre los que se puede afirmar."""

import pandas as pd
import pytest

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
    assert profile.duplicates(d).iloc[0]["filas_con_gemelo"] == 0
    assert profile.duplicates(d, subset=["id"]).iloc[0]["filas_con_gemelo"] == 2


def test_duplicates_devuelve_dataframe_de_una_fila():
    """Como el resto de la librería: concatenable, ordenable, afirmable."""
    d = pd.DataFrame({"id": [1, 1, 2], "v": ["a", "b", "c"]})
    out = profile.duplicates(d, subset=["id"])
    assert isinstance(out, pd.DataFrame) and len(out) == 1


def test_duplicates_se_puede_concatenar_por_corte():
    d = pd.DataFrame({"id": [1, 1, 2], "v": ["a", "b", "c"]})
    tabla = pd.concat([
        profile.duplicates(d, label="todo"),
        profile.duplicates(d, ["id"], label="llave"),
    ])
    assert list(tabla.index) == ["todo", "llave"]
    assert tabla.loc["llave", "grupos"] == 1


def test_duplicates_cuenta_grupos_y_el_mayor():
    d = pd.DataFrame({"k": ["a", "a", "a", "b", "b", "c"]})
    out = profile.duplicates(d, ["k"]).iloc[0]
    assert out["grupos"] == 2          # a y b
    assert out["mayor_grupo"] == 3       # a aparece tres veces
    assert out["sobrantes"] == 3      # dos de 'a' y una de 'b'
    assert out["filas_tras_deduplicar"] == 3


def test_duplicates_columna_inexistente():
    with pytest.raises(KeyError, match="ausentes"):
        profile.duplicates(pd.DataFrame({"a": [1]}), ["no_existe"])


# --- ver los duplicados -----------------------------------------------------

def test_duplicated_rows_etiqueta_grupo_y_tamaño():
    d = pd.DataFrame({"k": ["a", "a", "b", "b", "b", "c"], "v": range(6)})
    out = profile.duplicated_rows(d, ["k"])
    assert list(out.columns[:2]) == ["_grupo", "_tamaño"]
    assert len(out) == 5                      # 'c' no se repite
    assert out.iloc[0]["_tamaño"] == 3        # el grupo mayor va primero


def test_duplicated_rows_mantiene_los_grupos_juntos():
    d = pd.DataFrame({"k": ["a", "b", "a", "b"], "v": range(4)})
    out = profile.duplicated_rows(d, ["k"])
    grupos = list(out["_grupo"])
    assert grupos == sorted(grupos, key=grupos.index), "un grupo no puede quedar partido"


def test_duplicated_rows_recorta_grupos_no_filas():
    d = pd.DataFrame({"k": [c for c in "aabbccdd"]})
    out = profile.duplicated_rows(d, ["k"], max_groups=2)
    assert out["_grupo"].nunique() == 2
    assert len(out) == 4, "recorta grupos completos, nunca los parte"


def test_duplicated_rows_sin_duplicados_devuelve_vacio():
    d = pd.DataFrame({"k": ["a", "b", "c"]})
    out = profile.duplicated_rows(d, ["k"])
    assert out.empty and "_grupo" in out.columns


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


# --- formato de flotantes ---------------------------------------------------

def test_formato_adaptativo_no_usa_notacion_cientifica():
    from sumakit.nb import adaptive_float
    assert adaptive_float(1234567.0) == "1,234,567"
    assert adaptive_float(45678.9) == "45,679"


def test_formato_adaptativo_conserva_las_proporciones_chicas():
    from sumakit.nb import adaptive_float
    assert adaptive_float(0.000123) == "0.000123"
    assert adaptive_float(0.4567) == "0.4567"


def test_formato_adaptativo_casos_limite():
    import numpy as np
    from sumakit.nb import adaptive_float
    assert adaptive_float(0.0) == "0"
    assert adaptive_float(12.5) == "12.50"
    assert adaptive_float(float("nan")) == "nan"
