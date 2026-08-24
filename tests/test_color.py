"""Aritmética de color, contrastada con hechos conocidos."""

import numpy as np
import pytest

from sumakit import color, theme


def test_contraste_maximo_es_21():
    """Blanco sobre negro es el máximo teórico de WCAG."""
    assert color.contraste("#000000", "#ffffff") == pytest.approx(21.0, abs=0.05)


def test_contraste_de_un_color_consigo_mismo_es_1():
    assert color.contraste("#2a78d6", "#2a78d6") == pytest.approx(1.0)


def test_contraste_es_simetrico():
    assert color.contraste("#000", "#fff") == pytest.approx(color.contraste("#fff", "#000"))


def test_acepta_hex_de_tres_digitos():
    assert np.allclose(color.a_rgb("#fff"), color.a_rgb("#ffffff"))


def test_hex_invalido_falla():
    with pytest.raises(ValueError, match="hexadecimal"):
        color.a_rgb("no-es-un-color")


def test_lab_del_blanco():
    """El blanco de referencia tiene L*=100 y cromaticidad nula."""
    lab = color.a_lab("#ffffff")
    assert lab[0] == pytest.approx(100, abs=0.5)
    assert abs(lab[1]) < 1 and abs(lab[2]) < 1


def test_el_rojo_y_el_verde_colapsan_con_deuteranopia():
    """El caso de manual: son el par que más se confunde."""
    normal = color.delta_e("#e34948", "#008300")
    simulado = color.delta_e(
        color.simular_cvd("#e34948", "deuteranopía"), color.simular_cvd("#008300", "deuteranopía")
    )
    assert normal > 100
    assert simulado < 20, "debería colapsar y no lo hace"


def test_el_azul_y_el_naranja_sobreviven():
    """Es el par seguro por excelencia, y por eso son los dos primeros slots."""
    simulado = color.delta_e(
        color.simular_cvd("#2a78d6", "deuteranopía"), color.simular_cvd("#eb6834", "deuteranopía")
    )
    assert simulado > 50


def test_tipo_de_daltonismo_invalido():
    with pytest.raises(ValueError, match="tipo debe ser"):
        color.simular_cvd("#000000", "inventado")


# --- validación de paletas --------------------------------------------------


def test_la_paleta_por_defecto_pasa_los_chequeos_de_separacion():
    out = theme.validate(theme.LIGHT)
    separacion = out[out["chequeo"].str.startswith("separación")]
    assert separacion["pasa"].all()


def test_detecta_una_paleta_indistinguible():
    mala = theme.Palette(
        name="mala",
        categorical=("#2a78d6", "#2b79d7"),
        sequential=theme.LIGHT.sequential,
        diverging_low="#000",
        diverging_high="#fff",
        neutral="#eee",
        surface="#ffffff",
        text_primary="#000",
        text_secondary="#555",
        grid="#ddd",
    )
    out = theme.validate(mala)
    fila = out[out["chequeo"] == "separación (visión normal)"].iloc[0]
    assert not fila["pasa"], "dos azules casi iguales deben fallar"


def test_detecta_un_color_que_se_pierde_en_el_fondo():
    invisible = theme.Palette(
        name="invisible",
        categorical=("#fdfdfd", "#2a78d6"),
        sequential=theme.LIGHT.sequential,
        diverging_low="#000",
        diverging_high="#fff",
        neutral="#eee",
        surface="#ffffff",
        text_primary="#000",
        text_secondary="#555",
        grid="#ddd",
    )
    fila = theme.validate(invisible).iloc[0]
    assert not fila["pasa"] and fila["valor"] < 1.2


def test_all_pairs_es_mas_exigente_que_adyacentes():
    """Un scatter compara todas las series a la vez, no solo las vecinas."""
    adyacentes = theme.validate(theme.LIGHT)
    todos = theme.validate(theme.LIGHT, all_pairs=True)
    sep = "separación (visión normal)"
    assert (
        todos[todos["chequeo"] == sep]["valor"].iloc[0]
        <= adyacentes[adyacentes["chequeo"] == sep]["valor"].iloc[0]
    )


def test_exige_al_menos_dos_colores():
    with pytest.raises(ValueError, match="al menos 2"):
        theme.validate(theme.LIGHT, n=1)


def test_el_detalle_explica_el_contraste_bajo():
    fila = theme.validate(theme.LIGHT).iloc[0]
    if not fila["pasa"]:
        assert "etiquetas directas" in fila["detalle"]
