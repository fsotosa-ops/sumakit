"""Gráficos interactivos: van sobre agregados, no sobre datos crudos."""

import altair as alt
import numpy as np
import pandas as pd
import pytest

from sumakit import interactive


@pytest.fixture
def comp():
    """Tres composiciones: una concentrada, una repartida, una intermedia."""
    return pd.DataFrame(
        {
            "a": [1.0, 0.34, 0.5],
            "b": [0.0, 0.33, 0.3],
            "c": [0.0, 0.33, 0.2],
            "grupo": ["x", "y", "x"],
            "sitio": ["s1", "s2", "s1"],
        }
    )


def test_la_curva_siempre_cierra_en_uno(comp):
    t = interactive.concentration_table(comp, ["a", "b", "c"])
    assert t.loc[t["rango"] == 3, "acumulado"].iloc[0] == pytest.approx(1.0)


def test_es_creciente(comp):
    t = interactive.concentration_table(comp, ["a", "b", "c"]).sort_values("rango")
    assert t["acumulado"].is_monotonic_increasing


def test_una_fila_concentrada_llega_a_uno_en_el_primer_rango():
    d = pd.DataFrame({"a": [1.0], "b": [0.0], "c": [0.0]})
    t = interactive.concentration_table(d, ["a", "b", "c"])
    assert t.loc[t["rango"] == 1, "acumulado"].iloc[0] == pytest.approx(1.0)


def test_una_fila_repartida_sube_gradualmente():
    d = pd.DataFrame({"a": [1 / 3], "b": [1 / 3], "c": [1 / 3]})
    t = interactive.concentration_table(d, ["a", "b", "c"])
    assert t.loc[t["rango"] == 1, "acumulado"].iloc[0] == pytest.approx(1 / 3)


def test_normaliza_cada_fila_a_uno():
    """Compara forma, no magnitud: una fila en porcentaje y otra en 0-1 dan igual."""
    d = pd.DataFrame({"a": [80.0, 0.8], "b": [20.0, 0.2]})
    t = interactive.concentration_table(d, ["a", "b"])
    assert t.loc[t["rango"] == 1, "acumulado"].iloc[0] == pytest.approx(0.8)


def test_abre_por_categoria(comp):
    t = interactive.concentration_table(comp, ["a", "b", "c"], by="grupo")
    assert set(t["grupo"]) == {"x", "y"}
    assert len(t) == 6  # 2 grupos x 3 rangos


def test_cuenta_las_filas_de_cada_grupo(comp):
    t = interactive.concentration_table(comp, ["a", "b", "c"], by="grupo")
    assert t.loc[t["grupo"] == "x", "n"].iloc[0] == 2


def test_ignora_filas_que_suman_cero():
    d = pd.DataFrame({"a": [1.0, 0.0], "b": [0.0, 0.0]})
    t = interactive.concentration_table(d, ["a", "b"])
    assert t["n"].iloc[0] == 1, "la fila de puros ceros no aporta forma"


def test_agrupa_los_niveles_raros_en_otros():
    """Un desplegable de cincuenta opciones no es interactividad."""
    n = 60
    d = pd.DataFrame(
        {
            "a": np.linspace(0.1, 0.9, n),
            "b": 1 - np.linspace(0.1, 0.9, n),
            "sitio": [f"s{i}" for i in range(n)],
        }
    )
    t = interactive.concentration_table(d, ["a", "b"], by="sitio", max_levels=5)
    assert t["sitio"].nunique() == 6, "cinco niveles más 'Otros'"
    assert "Otros" in set(t["sitio"])


def test_exige_al_menos_dos_columnas():
    with pytest.raises(ValueError, match="al menos 2"):
        interactive.concentration_table(pd.DataFrame({"a": [1.0]}), ["a"])


def test_columna_inexistente(comp):
    with pytest.raises(KeyError, match="ausentes"):
        interactive.concentration_table(comp, ["a", "no_existe"])


# --- el gráfico -------------------------------------------------------------


def test_devuelve_un_chart_de_altair(comp):
    ch = interactive.concentration_curve(comp, ["a", "b", "c"], by="grupo")
    assert isinstance(ch, alt.Chart)


def test_la_especificacion_compila(comp):
    spec = interactive.concentration_curve(comp, ["a", "b", "c"], by="grupo").to_dict()
    assert spec["encoding"]["y"]["field"] == "acumulado"
    assert spec["mark"]["type"] == "line"


def test_solo_viajan_los_datos_agregados(comp):
    """La razón de existir de este módulo: el spec no lleva las filas crudas.

    Altair 6 guarda las filas en `datasets`, referenciadas por nombre desde
    `data`, en vez de incrustarlas inline.
    """
    spec = interactive.concentration_curve(comp, ["a", "b", "c"], by="grupo").to_dict()
    filas = next(iter(spec["datasets"].values()))
    assert len(filas) == 6, "2 grupos x 3 rangos, no las filas del DataFrame"


def test_el_filtro_agrega_un_desplegable(comp):
    spec = interactive.concentration_curve(
        comp, ["a", "b", "c"], by="grupo", filter_by="sitio"
    ).to_dict()
    binds = [p for p in spec.get("params", []) if "bind" in p]
    assert any(p["bind"] != "legend" for p in binds), "falta el select del filtro"


def test_usa_la_paleta_de_la_libreria(comp):
    from sumakit import theme

    interactive.apply_theme(theme.LIGHT)
    cfg = alt.theme.active
    assert cfg == "sumakit"
