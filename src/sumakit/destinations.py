"""Suma Studio como `destination` de dlt.

Con esto, **cualquier fuente de dlt aterriza en un proyecto** sin escribir un
conector a medida: bases SQL, APIs REST, buckets, y las que se porten de
`mage_integrations`.

    import dlt
    from sumakit.destinations import suma_studio

    pipeline = dlt.pipeline("banca", destination=suma_studio, dataset_name="taller")
    pipeline.run(mi_fuente(), table_name="perfil por segmento")

La clave sale de `SUMA_STUDIO_KEY`, **la misma variable que usa el SDK**. dlt
tiene su propio esquema de nombres —`DESTINATION__SUMA_STUDIO__PUBLISH_KEY`— y
también funciona, pero obligar a dos nombres para la misma credencial es
fricción sin contrapartida: quien ya publicaba desde un notebook no debería
tener que aprender otro. La librería no lleva credenciales dentro en ninguno de
los dos casos.

## Por qué `batch_size=0`

Es lo que hace que esto funcione, y no es una preferencia. Con el lote por
defecto —diez— dlt llama a la función **una vez por lote**: veinticinco filas son
tres llamadas. Y `studio.publish_dataset` **reemplaza la tabla por su nombre**,
así que las tres llamadas dejarían solo las últimas cinco filas.

Con `batch_size=0` dlt entrega **la ruta del archivo normalizado**, una sola vez
por tabla. Todas las filas llegan juntas y hay un único `publish`.

## Lo que todavía no se puede

`append` y `merge`. Studio solo sabe reemplazar por nombre, así que una carga
incremental —el modo natural de dlt— **no tiene dónde aterrizar**. Se rechaza en
voz alta en vez de perder filas en silencio. Es lo que falta decidir en `N-5`.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import dlt
from dlt.common.schema.typing import TTableSchema

from .studio import DEFAULT_URL, MAX_ROWS, StudioClient, StudioError

#: Lo único que Studio sabe hacer hoy con una tabla que llega.
DISPOSICIONES_SOPORTADAS = frozenset({"replace", "skip"})


def _leer_filas(ruta: str) -> list[dict[str, Any]]:
    """Lee el archivo normalizado que dlt entrega y devuelve filas limpias.

    Tres cosas que solo se descubren abriéndolo, y las tres mordieron:

    1. **Viene comprimido.** El primer intento reventó con un `UnicodeDecodeError`
       en el byte `0x8b`, que es la firma de gzip.
    2. **El formato es `typed-jsonl` y el contenido es un array JSON en una sola
       línea**, no un objeto por línea como el nombre sugiere. Leerlo línea a
       línea daba una lista con *una* lista dentro, y `DataFrame` de eso son
       columnas llamadas `0, 1, 2…`. **La carga decía «ok» y escribía basura.**
    3. **`_dlt_load_id` y `_dlt_id` viajan en el archivo** aunque
       `skip_dlt_columns_and_tables` esté activo: ese flag gobierna el esquema,
       no el contenido. Sin quitarlas, aterrizan en Studio como si fueran datos.
    """
    camino = Path(ruta)
    with camino.open("rb") as crudo:
        comprimido = crudo.read(2) == b"\x1f\x8b"

    abrir = gzip.open if comprimido else open
    with abrir(camino, "rt", encoding="utf-8") as archivo:
        texto = archivo.read()

    if not texto.strip():
        return []

    try:
        cargado = json.loads(texto)
        filas = cargado if isinstance(cargado, list) else [cargado]
    except json.JSONDecodeError:
        # Si no es un documento entero, entonces sí es una fila por línea.
        filas = [json.loads(linea) for linea in texto.splitlines() if linea.strip()]

    return [{k: v for k, v in fila.items() if not k.startswith("_dlt_")} for fila in filas]


@dlt.destination(batch_size=0, naming_convention="direct", skip_dlt_columns_and_tables=True)
def suma_studio(
    file_path: Any,
    table: TTableSchema,
    # dlt los pasa por posición. Marcarlo evita que un renombre de estos dos
    # nombres rompa la llamada en silencio.
    /,
    publish_key: str | None = None,
    url: str = DEFAULT_URL,
) -> None:
    """Publica en Suma Studio lo que dlt haya normalizado.

    Args:
        file_path: La ruta del archivo de esta tabla. Va tipado `Any` porque el
            decorador de dlt admite las dos formas —lotes de filas o ruta— y
            con `batch_size=0` siempre llega la segunda.
        table: El esquema que dlt infirió —`name`, `columns`,
            `write_disposition`—. Se usa el tipo de dlt y no un `dict` a mano:
            si su forma cambia, lo dice el verificador y no la ejecución.
        publish_key: La clave de publicación. `None` la toma de
            `SUMA_STUDIO_KEY`, igual que el SDK. **No se declara con
            `dlt.secrets.value` a propósito**: eso la haría obligatoria bajo el
            nombre de dlt y rompería a quien ya tiene la variable puesta.
        url: La URL del proyecto de Supabase.

    Raises:
        StudioError: Si la disposición no es `replace` —Studio no sabe agregar—
            o si son más filas de las que un entregable puede mostrar.
    """
    import pandas as pd

    disposicion = table.get("write_disposition", "append")
    if disposicion not in DISPOSICIONES_SOPORTADAS:
        raise StudioError(
            f"Suma Studio solo sabe reemplazar una tabla por su nombre, y esta carga pide "
            f"«{disposicion}». Usa write_disposition='replace', o espera a que Studio "
            f"aprenda a agregar."
        )
    if disposicion == "skip":
        return

    filas = _leer_filas(file_path)
    if not filas:
        return

    if len(filas) > MAX_ROWS:
        raise StudioError(
            f"son {len(filas):,} filas y el tope son {MAX_ROWS:,}. Agrega en la fuente: "
            f"un deck grafica entre cinco y treinta puntos"
        )

    nombre = table.get("name")
    if not nombre:
        raise StudioError("dlt no dio nombre a esta tabla, y en Studio el nombre es la tabla")

    StudioClient(publish_key, url=url).publish(pd.DataFrame(filas), nombre)
