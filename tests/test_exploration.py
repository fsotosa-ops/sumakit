"""explore(): una llamada, guiada por las alertas."""

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure

import sumakit
from sumakit import plots


def test_explore_devuelve_tablas_y_figuras(df):
    r = sumakit.explore(df)
    assert isinstance(r, sumakit.Exploration)
    assert isinstance(r.alerts, pd.DataFrame)
    assert isinstance(r.overview, pd.DataFrame)
    assert r.figures, "debería producir al menos una figura"
    assert all(isinstance(f, Figure) for f in r.figures.values())


def test_solo_grafica_lo_señalado(df):
    """La promesa central: no grafica las 26 columnas, solo las marcadas."""
    r = sumakit.explore(df)
    fig = r.figures.get("distribuciones señaladas")
    assert fig is not None
    n_sesgadas = len(r.alerts[r.alerts["chequeo"] == "asimetría"].iloc[0]["columnas"].split(","))
    n_numericas = df.select_dtypes("number").shape[1]
    assert len(fig.axes) == n_sesgadas
    assert len(fig.axes) < n_numericas, "debe ser un subconjunto, no todo"


def test_sin_nulos_no_dibuja_el_mapa_de_faltantes():
    d = pd.DataFrame({"a": np.arange(100.0), "b": np.random.default_rng(0).normal(size=100)})
    r = sumakit.explore(d)
    assert "datos faltantes" not in r.figures


def test_con_nulos_si_lo_dibuja(df):
    r = sumakit.explore(df)
    assert "datos faltantes" in r.figures


def test_repr_html_incluye_las_figuras(df):
    html = sumakit.explore(df)._repr_html_()
    assert html.count("<img") == len(sumakit.explore(df).figures)
    assert "data:image/png;base64," in html


def test_repr_texto_es_informativo(df):
    assert "alertas" in repr(sumakit.explore(df))


def test_puede_saltarse_la_busqueda_composicional(df):
    r = sumakit.explore(df, compositional=False)
    assert r.compositional.empty


def test_no_deja_estado_global_sucio(df):
    import matplotlib.pyplot as plt
    from sumakit import theme
    theme.use(theme.LIGHT)
    antes = dict(plt.rcParams)
    sumakit.explore(df)
    plt.close("all")
    assert not {k for k in antes if plt.rcParams[k] != antes[k]}


# --- ranking ----------------------------------------------------------------

def test_ranking_ordena_de_mayor_a_menor():
    s = pd.Series({"a": 1.0, "b": 9.0, "c": 5.0})
    fig = plots.ranking(s)
    etiquetas = [t.get_text() for t in fig.axes[0].get_yticklabels()]
    assert etiquetas == ["a", "c", "b"], "matplotlib apila de abajo hacia arriba"


def test_ranking_recorta_al_top():
    s = pd.Series(range(40), index=[f"v{i}" for i in range(40)], dtype=float)
    assert len(plots.ranking(s, top=5).axes[0].patches) == 5


def test_ranking_con_serie_vacia():
    assert isinstance(plots.ranking(pd.Series(dtype=float)), Figure)


def test_ranking_dibuja_la_referencia():
    s = pd.Series({"a": 1.0, "b": 2.0})
    fig = plots.ranking(s, highlight=1.5)
    assert len(fig.axes[0].lines) >= 1


def test_la_grilla_queda_detras_de_las_marcas():
    """Una grilla encima de las barras las corta visualmente."""
    from sumakit import theme
    theme.use(theme.LIGHT)
    fig = plots.ranking(pd.Series({"a": 1.0, "b": 2.0}))
    assert fig.axes[0].get_axisbelow() is True


def test_no_deja_figuras_en_el_registro_de_pyplot(df):
    """Si quedan abiertas, el backend inline de Jupyter las dibuja de nuevo
    y el usuario ve cada figura dos veces: una incrustada en el HTML y otra
    volcada al final de la celda."""
    import matplotlib.pyplot as plt
    plt.close("all")
    r = sumakit.explore(df)
    assert r.figures, "el caso solo tiene sentido si se generaron figuras"
    assert plt.get_fignums() == [], "quedaron figuras abiertas: se verán duplicadas"


def test_las_figuras_siguen_siendo_usables_tras_cerrarlas(df):
    import io
    r = sumakit.explore(df)
    fig = next(iter(r.figures.values()))
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    assert buf.getbuffer().nbytes > 0, "cerrarla no debe inutilizarla"


def test_el_html_incrusta_cada_figura_una_sola_vez(df):
    r = sumakit.explore(df)
    assert r._repr_html_().count("<img") == len(r.figures)
