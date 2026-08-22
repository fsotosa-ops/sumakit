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
