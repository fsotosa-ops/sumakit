"""La lógica del configurador, probada sin navegador.

Streamlit no se puede testear headless de forma razonable, pero las funciones
que producen las previsualizaciones sí: son las que pueden romperse.
"""

import matplotlib

matplotlib.use("Agg")

import pytest
from matplotlib.figure import Figure

from sumakit import theme

pytest.importorskip("streamlit")
from sumakit.ui import configurador  # noqa: E402


def test_la_figura_de_ejemplo_usa_el_tema():
    fig = configurador._figura_ejemplo(theme.LIGHT)
    assert isinstance(fig, Figure)
    lineas = fig.axes[0].get_lines()
    assert lineas, "debería dibujar series"
    assert lineas[0].get_color() == theme.LIGHT.categorical[0]


def test_la_previsualizacion_no_ensucia_el_tema_activo():
    """Usa theme.using: la paleta global no debe quedar cambiada."""
    theme.use(theme.LIGHT)
    configurador._figura_ejemplo(theme.DARK)
    assert theme.active().name == theme.LIGHT.name


def test_la_lamina_de_ejemplo_respeta_la_geometria_del_deck():
    from sumakit import deck
    fig = configurador._lamina_ejemplo(theme.LIGHT)
    ax = fig.axes[0]
    assert ax.get_xlim() == (0, 13.333), "debe usar el lienzo 16:9 del deck"
    assert deck._ANCHO == 13.333


def test_la_lamina_usa_el_fondo_de_la_paleta():
    fig = configurador._lamina_ejemplo(theme.DARK)
    assert fig.patch.get_facecolor()[:3] != (1.0, 1.0, 1.0)


def test_serializar_recorre_todos_los_campos_de_color():
    datos = configurador._serializar(theme.LIGHT)
    for campo in ("categorical", "surface", "text_primary", "grid",
                  "diverging_low", "diverging_high", "neutral"):
        assert campo in datos


def test_lo_serializado_se_puede_volver_a_cargar(tmp_path):
    import json
    ruta = tmp_path / "t.json"
    ruta.write_text(json.dumps(configurador._serializar(theme.DARK)), encoding="utf-8")
    leida = theme.load(ruta)
    assert leida.categorical == theme.DARK.categorical
    assert leida.surface == theme.DARK.surface


def test_el_tema_guardado_sigue_siendo_validable(tmp_path):
    """Cargar y validar es el ciclo completo del configurador."""
    theme.save(theme.LIGHT, tmp_path / "t.json")
    informe = theme.validate(theme.load(tmp_path / "t.json"))
    assert len(informe) == 5
