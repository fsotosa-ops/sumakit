"""El destination se prueba sin red: lo que importa es qué le manda a Studio."""

from __future__ import annotations

import gzip
import json

import pytest

dlt = pytest.importorskip("dlt")

from sumakit import destinations  # noqa: E402
from sumakit.studio import StudioError  # noqa: E402


@pytest.fixture
def spy(monkeypatch, tmp_path):
    """Intercepta el `publish` y guarda lo que habría viajado."""
    enviado = {}

    def fake_publish(self, table, name):
        enviado["name"] = name
        enviado["columns"] = list(table.columns)
        enviado["rows"] = len(table)
        return None

    monkeypatch.setattr("sumakit.studio.StudioClient.publish", fake_publish)
    monkeypatch.setenv("SUMA_STUDIO_KEY", "sk_prueba")
    return enviado


def jsonl(tmp_path, filas, *, con_dlt=True):
    """Escribe el archivo **como lo escribe dlt**, que no es lo que el nombre sugiere.

    Comprimido, un array JSON en una sola línea, y con las columnas internas
    `_dlt_*` dentro. La primera versión de este test escribía un objeto por
    línea sin comprimir —o sea, una ficción— y por eso pasaba en verde mientras
    la carga real escribía basura en Studio.
    """
    ruta = tmp_path / "tabla.typed-jsonl.gz"
    completas = [
        {**f, "_dlt_load_id": "1787620687.31", "_dlt_id": f"id{i}"} if con_dlt else f
        for i, f in enumerate(filas)
    ]
    with gzip.open(ruta, "wt", encoding="utf-8") as archivo:
        archivo.write(json.dumps(completas))
    return str(ruta)


def tabla(nombre="perfil", disposicion="replace"):
    return {"name": nombre, "write_disposition": disposicion, "columns": {}}


def llamar(ruta, t):
    """Llama a la función que hay dentro del decorador, sin levantar un pipeline."""
    return destinations.suma_studio.__wrapped__(ruta, t, publish_key="sk_prueba")


def test_publica_todas_las_filas_de_una_vez(spy, tmp_path):
    """El `batch_size=0` existe para esto y conviene que un test lo fije.

    Con el lote por defecto dlt llamaría una vez cada diez filas, y como
    `publish_dataset` reemplaza por nombre, solo sobrevivirían las últimas.
    """
    ruta = jsonl(tmp_path, [{"segmento": chr(65 + i % 5), "ticket": 100.0 + i} for i in range(25)])

    llamar(ruta, tabla())

    assert spy["rows"] == 25
    assert spy["name"] == "perfil"
    assert spy["columns"] == ["segmento", "ticket"]


def test_una_columna_nueva_viaja_sola(spy, tmp_path):
    """El esquema evoluciona solo: el destination no tiene que enterarse.

    En Studio esa columna llega **sin significado**, y un término sin definir no
    entra a ningún entregable. Ahí encaja el diccionario con la extracción.
    """
    ruta = jsonl(tmp_path, [{"segmento": "A", "ticket": 100.0, "pct_noche": 0.13}])

    llamar(ruta, tabla())

    assert spy["columns"] == ["segmento", "ticket", "pct_noche"]


def test_una_carga_incremental_se_rechaza_en_voz_alta(spy, tmp_path):
    """Studio solo reemplaza. Callarse aquí sería perder filas en silencio."""
    ruta = jsonl(tmp_path, [{"a": 1}])

    with pytest.raises(StudioError, match="reemplazar"):
        llamar(ruta, tabla(disposicion="append"))

    assert "name" not in spy


def test_el_dataset_crudo_no_pasa(spy, tmp_path):
    ruta = jsonl(tmp_path, [{"a": i} for i in range(20_001)])

    with pytest.raises(StudioError, match="tope"):
        llamar(ruta, tabla())


def test_una_tabla_vacia_no_publica_nada(spy, tmp_path):
    llamar(jsonl(tmp_path, []), tabla())
    assert "name" not in spy


def test_las_columnas_internas_de_dlt_no_llegan_a_studio(spy, tmp_path):
    """`_dlt_load_id` y `_dlt_id` viajan en el archivo aunque el flag esté puesto.

    `skip_dlt_columns_and_tables` gobierna el esquema, no el contenido. Sin
    quitarlas a mano, aterrizan en el proyecto como si fueran datos.
    """
    ruta = jsonl(tmp_path, [{"segmento": "A", "ticket": 100.0}])

    llamar(ruta, tabla())

    assert spy["columns"] == ["segmento", "ticket"]


def test_una_fila_por_linea_tambien_se_lee(tmp_path, spy):
    """Hoy dlt escribe un array; si mañana escribe líneas, esto no se rompe."""
    ruta = tmp_path / "lineas.jsonl"
    ruta.write_text('{"a": 1}\n{"a": 2}\n', encoding="utf-8")

    llamar(str(ruta), tabla())

    assert spy["rows"] == 2
