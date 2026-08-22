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
_ESQUELETO = '''---
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
etiqueta:

```
#| label: fig-ejemplo
#| fig-cap: "Descripción de la figura"
```
'''


def init(destino: Path | str = ".", *, notebook: str = "notebook.ipynb",
         titulo: str = "Informe", autor: str = "", force: bool = False,
         esqueleto: bool = True) -> Path:
    """Instala los formatos en un proyecto y siembra el esqueleto del informe."""
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

    if esqueleto:
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


def render(fuente: Path | str, *, salida: Path | str | None = None,
           ejecutar: bool = False) -> Path:
    """Renderiza un `.qmd` con Quarto y deja el resultado donde corresponda."""
    fuente = Path(fuente).resolve()
    if not fuente.exists():
        raise FileNotFoundError(f"no encuentro {fuente}")

    quarto = shutil.which("quarto")
    if quarto is None:
        raise RuntimeError(
            "Quarto no está instalado. Instálalo con `uv add --dev quarto-cli` "
            "o desde quarto.org."
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


def main(argv: list[str] | None = None) -> int:
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

    p_render = sub.add_parser("render", help="renderizar un .qmd")
    p_render.add_argument("fuente")
    p_render.add_argument("--salida", default=None)
    p_render.add_argument("--ejecutar", action="store_true")

    args = parser.parse_args(argv)
    if args.comando == "report":
        init(args.destino, notebook=args.notebook, titulo=args.titulo,
             autor=args.autor, force=args.force, esqueleto=not args.sin_esqueleto)
    else:
        destino = render(args.fuente, salida=args.salida, ejecutar=args.ejecutar)
        print(f"  -> {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
