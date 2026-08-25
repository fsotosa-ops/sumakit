"""El contrato: toda salida debe sobrevivir a notebook, PDF y PowerPoint.

Esta es la prueba que faltaba y por cuya ausencia se rompió todo. Las figuras
de `explore()` se veían bien en el notebook pero desaparecían al renderizar,
porque vivían incrustadas en un blob HTML que ni LaTeX ni PowerPoint leen.

Aquí se renderiza de verdad, con Quarto, y se cuenta lo que llegó al archivo
final. Si alguien vuelve a incrustar una figura en HTML, esto se pone rojo.

Se salta si Quarto no está instalado: es una dependencia del entorno, no de
la librería.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path

import pytest

quarto = shutil.which("quarto")
# Cada prueba lanza un render real: ~20 s. Se marcan lentas para poder
# excluirlas del ciclo rápido con `pytest -m "not lento"`.
requiere_quarto = pytest.mark.skipif(quarto is None, reason="quarto no está instalado")
lento = pytest.mark.lento

# Usa cada superficie de la librería que produce algo visible.
NOTEBOOK = """
import matplotlib
matplotlib.use("Agg")
import numpy as np, pandas as pd
from sumakit import nb, profile, stats, plots, cluster, explore

nb.setup(seed=42)
rng = np.random.default_rng(0)
n = 300
a = rng.dirichlet([2, 3, 5], n)
df = pd.DataFrame({
    "manana": a[:, 0], "tarde": a[:, 1], "noche": a[:, 2],
    "monto": rng.exponential(500, n),
    "grupo": rng.choice(list("abc"), n),
})

from sklearn.cluster import KMeans
X = df.select_dtypes("number")
modelos = {k: KMeans(n_clusters=k, random_state=0, n_init=10).fit(X) for k in range(2, 5)}
etiquetas = modelos[3].labels_
""".strip()


# Cada superficie de la librería que produce algo visible. El prefijo no es
# decorativo: `_FIGURAS` cuenta con él, y una figura nueva que se agregue aquí
# queda cubierta sin tocar ninguna aserción.
SALIDAS = [
    ("fig-corr", "plots.correlation_heatmap(df)"),
    ("fig-dist", "plots.distributions(df, columns=['monto'])"),
    ("fig-explore", "explore(df)"),
    ("fig-elbow", "plots.elbow(cluster.k_report(X, modelos))"),
    ("fig-silueta", "plots.silhouette(X, etiquetas)"),
    ("fig-segmentos", "plots.segments(cluster.segments(df, etiquetas))"),
    ("tbl-overview", "profile.overview(df)"),
    ("tbl-comp", "stats.sum_constant_groups(df)"),
    ("tbl-segmentos", "profile.as_markdown(cluster.distinctive(df, etiquetas))"),
]
_FIGURAS = [e for e, _ in SALIDAS if e.startswith("fig-")]


def _celda(fuente: str, etiqueta: str | None = None) -> dict:
    if etiqueta:
        fuente = f"#| label: {etiqueta}\n{fuente}"
    lineas = fuente.split("\n")
    return {
        "cell_type": "code",
        "id": uuid.uuid4().hex[:8],
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [linea + "\n" for linea in lineas[:-1]] + [lineas[-1]],
    }


def _escribir_notebook(destino: Path) -> Path:
    celdas = [_celda(NOTEBOOK)] + [_celda(codigo, etiqueta) for etiqueta, codigo in SALIDAS]
    nb = {
        "cells": celdas,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.13"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    ruta = destino / "contrato.ipynb"
    ruta.write_text(json.dumps(nb), encoding="utf-8")
    return ruta


def _render(ruta: Path, formato: str) -> Path:
    r = subprocess.run(
        [quarto, "render", str(ruta), "--to", formato, "--execute"],
        capture_output=True,
        text=True,
        cwd=ruta.parent,
    )
    if r.returncode != 0:
        pytest.fail(f"quarto render --to {formato} falló:\n{r.stderr[-1500:]}")
    sufijos = {"pdf": ".pdf", "latex": ".tex", "pptx": ".pptx", "html": ".html"}
    salida = ruta.with_suffix(sufijos[formato])
    assert salida.exists(), f"no se generó {salida.name}"
    return salida


@pytest.fixture(scope="module")
def proyecto(tmp_path_factory) -> Path:
    return _escribir_notebook(tmp_path_factory.mktemp("contrato"))


@lento
@requiere_quarto
def test_las_figuras_llegan_al_pdf(proyecto):
    """El defecto original: el PDF salía con cero imágenes."""
    datos = _render(proyecto, "pdf").read_bytes()
    imagenes = datos.count(b"/Subtype/Image") + datos.count(b"/Subtype /Image")
    # Aquí no se puede censar. Una figura de matplotlib entra al PDF como
    # gráfico vectorial —un Form XObject—, no como `/Subtype/Image`; solo los
    # heatmaps rasterizan y aparecen en esta cuenta. El censo por figura se hace
    # sobre el .tex, en `test_todas_las_figuras_llegan_al_documento`.
    assert imagenes > 0, "ninguna figura sobrevivió al PDF"


@lento
@requiere_quarto
def test_las_figuras_llegan_al_powerpoint(proyecto):
    with zipfile.ZipFile(_render(proyecto, "pptx")) as z:
        medios = [n for n in z.namelist() if n.startswith("ppt/media/")]
    assert medios, "ninguna figura sobrevivió al pptx"


@lento
@requiere_quarto
@pytest.mark.xfail(
    reason="el writer de pptx de Pandoc descarta figuras por posición; ver el cuerpo",
    strict=False,
)
def test_todas_las_figuras_llegan_al_powerpoint(proyecto):
    """Deuda conocida, anotada para que no vuelva a pasar inadvertida.

    Pandoc numera las siete figuras del documento y emite cinco: se come la
    tercera y la séptima. No es por contenido —la séptima es un heatmap de la
    misma construcción que la primera, que sí llega— sino por dónde caen en la
    secuencia de bloques. La misma figura, aislada en un notebook mínimo,
    sobrevive.

    Esto no bloquea el entregable y por eso es `xfail` y no un fallo: el informe
    sale por LaTeX, donde el censo está completo, y el deck lo produce
    `sumakit.deck` con python-pptx, que no pasa por Pandoc. El `--to pptx` de
    Quarto es la vía de conveniencia, y es la única que pierde figuras.
    """
    with zipfile.ZipFile(_render(proyecto, "pptx")) as z:
        medios = [n for n in z.namelist() if n.startswith("ppt/media/")]
    assert len(medios) >= len(_FIGURAS), (
        f"solo {len(medios)} figuras en el pptx; se esperaban al menos {len(_FIGURAS)}"
    )


@lento
@requiere_quarto
def test_las_tablas_se_convierten_a_latex(proyecto):
    """Un Styler con CSS no sobrevive a LaTeX: las tablas deben degradar.

    Se revisa el .tex y no el .pdf porque los flujos del PDF van comprimidos:
    buscar "tabular" en sus bytes crudos no encuentra nada aunque la tabla esté.
    """
    tex = _render(proyecto, "latex").read_text(encoding="utf-8", errors="ignore")
    assert "tabular" in tex or "longtable" in tex, "ninguna tabla se convirtió a LaTeX"


@lento
@requiere_quarto
def test_todas_las_figuras_llegan_al_documento(proyecto):
    r"""El censo: una figura que llega no puede seguir tapando a las que no.

    `\includegraphics` es la cuenta honesta, porque cada figura deja uno
    independientemente de si es vectorial o ráster. Es un piso y no una
    igualdad: `explore()` emite varias figuras desde una sola celda.
    """
    tex = _render(proyecto, "latex").read_text(encoding="utf-8", errors="ignore")
    incluidas = tex.count("includegraphics")
    assert incluidas >= len(_FIGURAS), (
        f"solo {incluidas} figuras en el documento; se esperaban al menos {len(_FIGURAS)}"
    )


@lento
@requiere_quarto
def test_el_html_sigue_siendo_el_formato_rico(proyecto):
    html = _render(proyecto, "html").read_text(encoding="utf-8", errors="ignore")
    assert "<table" in html
    assert "<img" in html or "base64" in html
