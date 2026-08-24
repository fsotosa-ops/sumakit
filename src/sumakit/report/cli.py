"""`sumakit report init` y `sumakit render`.

Las plantillas viajan dentro del paquete, no dentro de un repositorio. Un
proyecto nuevo —de la maestría, de un cliente, de lo que sea— corre
`sumakit report init` y tiene los formatos disponibles sin copiar nada a mano.
Esa es la diferencia entre una herramienta y un directorio que se clona.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path

__all__ = ["init", "render", "main"]

_PAQUETE = "sumakit.report"
_ESQUELETO_NEGOCIO = '''"""Construye el deck de negocio a partir del análisis del notebook.

Se ejecuta, no se renderiza: `python negocio.py`. El resultado es un .pptx
que se abre en PowerPoint o Google Slides para el retoque final.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

from sumakit import nb, theme
from sumakit.deck import Deck

nb.setup(seed=42, palette=theme.LIGHT)

AQUI = Path(__file__).parent
FIGURAS = AQUI / "figuras"
FIGURAS.mkdir(exist_ok=True)

# Genera aquí las figuras con sumakit.plots y guárdalas en FIGURAS/,
# o reutiliza las que el notebook ya exportó.

d = Deck("{titulo}", subtitle="{autor}", footer="")
d.cover()
d.agenda(["Negocio y problemática", "Datos y metodología",
          "Principales hallazgos", "Recomendaciones"])

# Cada hallazgo necesita un título de acción: la conclusión en una frase.
# "Resultados" no pasa la validación, y es a propósito.
d.finding(
    "Escribe aquí el hallazgo completo, no una etiqueta de sección",
    kicker="Principales hallazgos",
    # image=FIGURAS / "algo.png",
    # callouts=["La anotación que le dice al lector qué mirar"],
)

d.save(AQUI / ".." / "entrega" / "negocio.pptx")
print("deck generado")
'''

_ESQUELETO = """---
title: "{titulo}"
author: "{autor}"
date: today
format:
  sumakit/academico-pdf: default
bibliography: referencias.bib
---

# Introduction

Escribe aquí la narrativa. El notebook queda como proceso; este archivo es el
entregable, y jala del notebook solo las figuras que elijas:

{{{{< embed ../desarrollo/{notebook}#fig-ejemplo >}}}}

Para que el embed funcione, la celda del notebook tiene que llevar una
etiqueta. El prefijo importa: `fig-` para figuras, `tbl-` para tablas, y tiene
que coincidir con lo que la celda realmente emite.

```
#| label: fig-ejemplo
#| fig-cap: "Descripción de la figura"
```

Para tablas anchas, emítelas como markdown y fija los anchos. Un DataFrame se
muestra como HTML, y Pandoc lo traduce a un `tabular` de columnas rígidas que
se sale del margen; como markdown, respeta los anchos y parte el texto:

```
#| tbl-colwidths: [12, 12, 76]
profile.as_markdown(stats.sum_constant_groups(df), index=False)
```

Y recuerda que `embed` toma los outputs **guardados** del notebook: si cambias
una celda, hay que re-ejecutarlo para que el informe lo refleje.
"""


def init(
    destino: Path | str = ".",
    *,
    notebook: str = "notebook.ipynb",
    titulo: str = "Informe",
    autor: str = "",
    force: bool = False,
    esqueleto: bool = True,
    tipo: str = "ambos",
) -> Path:
    """Instala los formatos en un proyecto y siembra los esqueletos.

    `tipo` elige qué caminos sembrar: `academico` (PDF vía LaTeX), `negocio`
    (deck de consultoría) o `ambos`. Son dos géneros distintos y por eso son
    dos archivos, no dos secciones del mismo.
    """
    if tipo not in {"academico", "negocio", "ambos"}:
        raise ValueError(f"tipo debe ser academico, negocio o ambos; no {tipo!r}")
    destino = Path(destino).resolve()
    extensiones = destino / "_extensions"

    # La copia va DENTRO del context manager: al salir, `as_file` borra el
    # directorio temporal que extrae del paquete.
    with resources.as_file(resources.files(_PAQUETE)) as raiz:
        origen = Path(raiz) / "_extensions"
        if not origen.is_dir():
            raise FileNotFoundError(
                f"el paquete no trae las extensiones en {origen}. "
                "¿Se instaló sin los datos del paquete?"
            )
        for paquete in sorted(origen.iterdir()):
            if not paquete.is_dir() or paquete.name.startswith("__"):
                continue
            for formato in sorted(paquete.iterdir()):
                if not formato.is_dir():
                    continue
                objetivo = extensiones / paquete.name / formato.name
                if objetivo.exists() and not force:
                    print(f"  = {objetivo.relative_to(destino)} (ya existe)")
                    continue
                if objetivo.exists():
                    shutil.rmtree(objetivo)
                shutil.copytree(formato, objetivo)
                print(f"  + {objetivo.relative_to(destino)}")

    if esqueleto and tipo in {"negocio", "ambos"}:
        script = destino / "negocio.py"
        if script.exists() and not force:
            print(f"  = {script.name} (ya existe)")
        else:
            script.write_text(
                _ESQUELETO_NEGOCIO.format(titulo=titulo, autor=autor), encoding="utf-8"
            )
            print(f"  + {script.name}")

    if esqueleto and tipo in {"academico", "ambos"}:
        qmd = destino / "academico.qmd"
        if qmd.exists() and not force:
            print(f"  = {qmd.name} (ya existe)")
        else:
            qmd.write_text(
                _ESQUELETO.format(titulo=titulo, autor=autor, notebook=notebook),
                encoding="utf-8",
            )
            print(f"  + {qmd.name}")
        bib = destino / "referencias.bib"
        if not bib.exists():
            bib.write_text("", encoding="utf-8")
            print(f"  + {bib.name}")

    return destino


def render(fuente: Path | str, *, salida: Path | str | None = None, ejecutar: bool = False) -> Path:
    """Renderiza un `.qmd` con Quarto y deja el resultado donde corresponda."""
    fuente = Path(fuente).resolve()
    if not fuente.exists():
        raise FileNotFoundError(f"no encuentro {fuente}")

    quarto = shutil.which("quarto")
    if quarto is None:
        raise RuntimeError(
            "Quarto no está instalado. Instálalo con `uv add --dev quarto-cli` o desde quarto.org."
        )

    orden = [quarto, "render", str(fuente)]
    orden.append("--execute" if ejecutar else "--no-execute")
    proceso = subprocess.run(orden, cwd=fuente.parent)
    if proceso.returncode != 0:
        raise RuntimeError(f"quarto render falló con código {proceso.returncode}")

    producido = fuente.with_suffix(".pdf")
    if salida is not None:
        destino = Path(salida).resolve()
        destino.mkdir(parents=True, exist_ok=True)
        final = destino / producido.name
        shutil.move(str(producido), final)
        return final
    return producido


def abrir_configurador() -> int:
    """Lanza el configurador de tema con Streamlit."""
    if shutil.which("streamlit") is None:
        print(
            "El configurador necesita Streamlit:\n  uv add 'sumakit[ui]'   o   uv add streamlit",
            file=sys.stderr,
        )
        return 1
    from importlib import resources as _res

    with _res.as_file(_res.files("sumakit.ui")) as raiz:
        app = Path(raiz) / "configurador.py"
        return subprocess.run(["streamlit", "run", str(app)]).returncode


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada del ejecutable `sumakit`.

    Args:
        argv: Argumentos de línea de órdenes. `None` usa los de `sys.argv`.

    Returns:
        El código de salida del proceso.
    """
    parser = argparse.ArgumentParser(prog="sumakit", description=__doc__)
    sub = parser.add_subparsers(dest="comando", required=True)

    p_report = sub.add_parser("report", help="gestionar formatos de informe")
    sub_report = p_report.add_subparsers(dest="accion", required=True)
    p_init = sub_report.add_parser("init", help="instalar los formatos en este proyecto")
    p_init.add_argument("--destino", default=".")
    p_init.add_argument("--notebook", default="notebook.ipynb")
    p_init.add_argument("--titulo", default="Informe")
    p_init.add_argument("--autor", default="")
    p_init.add_argument("--force", action="store_true")
    p_init.add_argument("--sin-esqueleto", action="store_true")
    p_init.add_argument("--tipo", default="ambos", choices=["academico", "negocio", "ambos"])

    sub.add_parser("theme", help="abrir el configurador de tema")

    p_render = sub.add_parser("render", help="renderizar un .qmd")
    p_render.add_argument("fuente")
    p_render.add_argument("--salida", default=None)
    p_render.add_argument("--ejecutar", action="store_true")

    args = parser.parse_args(argv)
    if args.comando == "theme":
        return abrir_configurador()
    if args.comando == "report":
        init(
            args.destino,
            notebook=args.notebook,
            titulo=args.titulo,
            autor=args.autor,
            force=args.force,
            esqueleto=not args.sin_esqueleto,
            tipo=args.tipo,
        )
    else:
        destino = render(args.fuente, salida=args.salida, ejecutar=args.ejecutar)
        print(f"  -> {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
