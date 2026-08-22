"""El CLI existe para que la maquinaria no viva dentro de un repositorio.

La prueba que importa es que funcione en un directorio recién creado que no
sabe nada del proyecto donde nació.
"""

from pathlib import Path

import pytest
import yaml

from sumakit.report import cli


def test_instala_las_extensiones_en_un_directorio_ajeno(tmp_path):
    cli.init(tmp_path, esqueleto=False)
    ext = tmp_path / "_extensions" / "sumakit" / "academico"
    assert (ext / "_extension.yml").exists()
    assert (ext / "preambulo.tex").exists()


def test_la_extension_declara_el_formato_pdf(tmp_path):
    cli.init(tmp_path, esqueleto=False)
    spec = yaml.safe_load(
        (tmp_path / "_extensions/sumakit/academico/_extension.yml").read_text()
    )
    formatos = spec["contributes"]["formats"]
    assert "pdf" in formatos
    assert formatos["pdf"]["number-sections"] is True
    assert formatos["pdf"]["include-in-header"] == "preambulo.tex"


def test_siembra_el_esqueleto_del_informe(tmp_path):
    cli.init(tmp_path, titulo="Mi informe", autor="Alguien", notebook="x.ipynb")
    qmd = (tmp_path / "academico.qmd").read_text(encoding="utf-8")
    assert "Mi informe" in qmd and "Alguien" in qmd
    assert "sumakit/academico-pdf" in qmd, "el nombre del formato debe ser el calificado"
    assert "x.ipynb#fig-ejemplo" in qmd, "el esqueleto muestra cómo embeber del notebook"
    assert (tmp_path / "referencias.bib").exists()


def test_no_pisa_lo_que_ya_existe(tmp_path):
    cli.init(tmp_path)
    (tmp_path / "academico.qmd").write_text("MI TRABAJO", encoding="utf-8")
    cli.init(tmp_path)
    assert (tmp_path / "academico.qmd").read_text() == "MI TRABAJO"


def test_force_si_pisa(tmp_path):
    cli.init(tmp_path)
    (tmp_path / "academico.qmd").write_text("MI TRABAJO", encoding="utf-8")
    cli.init(tmp_path, force=True)
    assert (tmp_path / "academico.qmd").read_text() != "MI TRABAJO"


def test_render_avisa_si_no_encuentra_la_fuente(tmp_path):
    with pytest.raises(FileNotFoundError, match="no encuentro"):
        cli.render(tmp_path / "no-existe.qmd")


def test_el_preambulo_trae_booktabs_y_el_acento(tmp_path):
    cli.init(tmp_path, esqueleto=False)
    tex = (tmp_path / "_extensions/sumakit/academico/preambulo.tex").read_text()
    assert "booktabs" in tex
    assert "sumakitaccent" in tex


def test_el_acento_del_preambulo_coincide_con_la_paleta(tmp_path):
    """Si divergen, el PDF y los gráficos dejan de ser el mismo sistema."""
    from sumakit import theme
    cli.init(tmp_path, esqueleto=False)
    tex = (tmp_path / "_extensions/sumakit/academico/preambulo.tex").read_text()
    esperado = theme.LIGHT.categorical[0].lstrip("#").upper()
    assert f"{{HTML}}{{{esperado}}}" in tex.upper()


def test_main_acepta_la_linea_de_comandos(tmp_path, capsys):
    assert cli.main(["report", "init", "--destino", str(tmp_path)]) == 0
    assert (tmp_path / "academico.qmd").exists()


def test_siembra_los_dos_caminos(tmp_path):
    """Académico y negocio son géneros distintos: dos archivos, no dos secciones."""
    cli.init(tmp_path, titulo="T", autor="A")
    assert (tmp_path / "academico.qmd").exists()
    assert (tmp_path / "negocio.py").exists()


def test_puede_sembrar_solo_uno(tmp_path):
    cli.init(tmp_path, tipo="academico")
    assert (tmp_path / "academico.qmd").exists()
    assert not (tmp_path / "negocio.py").exists()


def test_el_esqueleto_de_negocio_usa_la_api_del_deck(tmp_path):
    cli.init(tmp_path, tipo="negocio", titulo="Mi deck")
    py = (tmp_path / "negocio.py").read_text(encoding="utf-8")
    assert "from sumakit.deck import Deck" in py
    assert "Mi deck" in py
    assert "título de acción" in py, "el esqueleto debe explicar la regla"


def test_tipo_invalido_falla(tmp_path):
    with pytest.raises(ValueError, match="academico, negocio o ambos"):
        cli.init(tmp_path, tipo="inventado")
