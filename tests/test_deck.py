"""El deck impone la gramática de consultoría, no solo dibuja láminas."""

import matplotlib
matplotlib.use("Agg")

import pandas as pd
import pytest
from pptx import Presentation
from pptx.util import Inches

from sumakit import plots
from sumakit.deck import Deck, TituloNoAccionable

HALLAZGO = "Dos tercios de la cartera realizó tres transacciones o menos en el mes"


@pytest.fixture
def figura(tmp_path):
    fig = plots.ranking(pd.Series({"lunes": 3.0, "martes": 5.0, "miércoles": 1.0}))
    ruta = tmp_path / "fig.png"
    fig.savefig(ruta)
    return ruta


# --- la regla que justifica el módulo ---------------------------------------

def test_rechaza_un_titulo_que_es_etiqueta():
    """"Resultados" obliga al lector a deducir; un hallazgo se lo entrega."""
    with pytest.raises(TituloNoAccionable, match="etiqueta"):
        Deck("d").finding("Resultados")


def test_acepta_un_titulo_de_accion():
    d = Deck("d")
    d.finding(HALLAZGO)
    assert len(d) == 1


def test_el_mensaje_explica_como_arreglarlo():
    with pytest.raises(TituloNoAccionable) as e:
        Deck("d").finding("Conclusiones")
    assert "frase completa" in str(e.value) and "strict=False" in str(e.value)


def test_strict_false_es_la_salida_de_emergencia():
    d = Deck("d", strict=False)
    d.finding("Resultados")
    assert len(d) == 1


def test_la_regla_tambien_aplica_a_las_tablas():
    with pytest.raises(TituloNoAccionable):
        Deck("d").table("Datos", pd.DataFrame({"a": [1]}))


# --- estructura -------------------------------------------------------------

def test_las_laminas_son_16_9():
    d = Deck("d")
    assert d.prs.slide_width == Inches(13.333)
    assert d.prs.slide_height == Inches(7.5)


def test_construye_el_arco_completo(figura):
    d = Deck("Título", subtitle="sub", footer="SUMADOTS")
    d.cover()
    d.agenda(["Negocio", "Datos", "Hallazgos", "Recomendaciones"])
    d.section("Principales hallazgos")
    d.finding(HALLAZGO, kicker="Principales hallazgos", image=figura)
    d.closing("Gracias")
    assert len(d) == 5


def test_la_figura_queda_embebida(figura, tmp_path):
    d = Deck("d")
    d.finding(HALLAZGO, image=figura)
    ruta = d.save(tmp_path / "x.pptx")
    import zipfile
    with zipfile.ZipFile(ruta) as z:
        assert [n for n in z.namelist() if n.startswith("ppt/media/")], \
            "la figura no viajó dentro del pptx"


def test_figura_inexistente_falla_claro():
    with pytest.raises(FileNotFoundError, match="figura"):
        Deck("d").finding(HALLAZGO, image="no/existe.png")


def test_los_callouts_agregan_formas(figura):
    d = Deck("d")
    s_sin = d.finding(HALLAZGO, image=figura)
    n_sin = len(s_sin.shapes)
    s_con = d.finding(HALLAZGO, image=figura,
                      callouts=[("una anotación", 0.5, 0.1), ("otra", 0.1, 0.6)])
    assert len(s_con.shapes) == n_sin + 2


def test_el_titulo_de_accion_aparece_en_la_lamina(figura):
    d = Deck("d")
    s = d.finding(HALLAZGO, kicker="Hallazgos", image=figura)
    textos = " ".join(f.text_frame.text for f in s.shapes if f.has_text_frame)
    assert HALLAZGO in textos
    assert "Hallazgos" in textos


def test_la_tabla_lleva_encabezado_y_filas():
    datos = pd.DataFrame({"a": [1, 2], "b": [3.5, 4.5]}, index=["x", "y"])
    d = Deck("d")
    s = d.table(HALLAZGO, datos)
    tabla = next(f.table for f in s.shapes if f.has_table)
    assert tabla.cell(0, 1).text == "a"
    assert tabla.cell(1, 0).text == "x"


def test_el_archivo_guardado_se_puede_reabrir(tmp_path):
    d = Deck("d")
    d.cover()
    ruta = d.save(tmp_path / "sub/carpeta/x.pptx")
    assert ruta.exists()
    assert len(Presentation(str(ruta)).slides) == 1


def test_usa_el_color_de_acento_del_tema():
    from sumakit import theme
    d = Deck("d", palette=theme.LIGHT)
    assert str(d._acento) == theme.LIGHT.categorical[0].lstrip("#").upper()
