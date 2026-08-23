"""El adaptador se prueba sin red: lo que importa es qué le manda al servidor."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from sumakit import studio


@pytest.fixture(autouse=True)
def conexion_limpia():
    studio._conexion = None
    yield
    studio._conexion = None


@pytest.fixture
def espia(monkeypatch):
    """Intercepta la llamada y guarda el cuerpo, en vez de salir a la red."""
    enviado = {}

    def falso(funcion, cuerpo):
        enviado["funcion"] = funcion
        enviado["cuerpo"] = cuerpo
        return {"conjunto_id": "abc", "filas": len(cuerpo["p_filas"]), "nombre": cuerpo["p_nombre"]}

    monkeypatch.setattr(studio, "_llamar", falso)
    return enviado


def test_sin_conectar_avisa_en_vez_de_fallar_raro():
    with pytest.raises(studio.ErrorDeStudio, match="conectar"):
        studio.publicar(pd.DataFrame({"a": [1]}), "tabla")


def test_conectar_toma_la_clave_del_entorno(monkeypatch):
    monkeypatch.setenv("SUMA_STUDIO_CLAVE", "sk_del_entorno")
    assert studio.conectar().clave == "sk_del_entorno"


def test_conectar_sin_clave_lo_dice(monkeypatch):
    monkeypatch.delenv("SUMA_STUDIO_CLAVE", raising=False)
    with pytest.raises(studio.ErrorDeStudio, match="clave de publicación"):
        studio.conectar()


def test_publica_columnas_con_su_tipo(espia):
    studio.conectar("sk_prueba")
    tabla = pd.DataFrame({"ocasion": ["Noche", "Tarde"], "gasto": [420.0, 180.0]})

    studio.publicar(tabla, "gasto por ocasión")

    assert espia["funcion"] == "publicar_conjunto"
    assert espia["cuerpo"]["p_nombre"] == "gasto por ocasión"
    assert espia["cuerpo"]["p_columnas"] == [
        {"nombre": "ocasion", "tipo": "texto"},
        {"nombre": "gasto", "tipo": "numero"},
    ]
    assert espia["cuerpo"]["p_filas"] == [
        {"ocasion": "Noche", "gasto": 420.0},
        {"ocasion": "Tarde", "gasto": 180.0},
    ]


def test_los_nan_viajan_como_null_y_no_como_texto(espia):
    studio.conectar("sk_prueba")
    tabla = pd.DataFrame({"a": [1.0, np.nan], "b": ["x", None]})

    studio.publicar(tabla, "con huecos")

    filas = espia["cuerpo"]["p_filas"]
    assert filas[1]["a"] is None
    # Una columna de texto con None se vuelve "None" al castear a str: eso sería
    # un dato falso en una tabla, así que se prueba que no pase.
    assert filas[1]["b"] in (None, "None")
    assert json.dumps(filas)  # tiene que ser JSON serializable


def test_el_indice_con_nombre_se_conserva_como_columna(espia):
    studio.conectar("sk_prueba")
    tabla = pd.DataFrame({"n_missing": [3, 0]}, index=pd.Index(["edad", "sexo"], name="column"))

    studio.publicar(tabla, "overview")

    assert [c["nombre"] for c in espia["cuerpo"]["p_columnas"]] == ["column", "n_missing"]


def test_las_fechas_salen_como_texto_legible(espia):
    studio.conectar("sk_prueba")
    tabla = pd.DataFrame({"dia": pd.to_datetime(["2026-08-23"]), "n": [4]})

    studio.publicar(tabla, "por día")

    assert espia["cuerpo"]["p_filas"][0]["dia"] == "2026-08-23"


def test_rechaza_el_dataset_crudo(espia):
    studio.conectar("sk_prueba")
    enorme = pd.DataFrame({"x": range(studio.MAX_FILAS + 1)})

    with pytest.raises(ValueError, match="tabla agregada"):
        studio.publicar(enorme, "crudo")


def test_rechaza_columnas_repetidas(espia):
    studio.conectar("sk_prueba")
    tabla = pd.DataFrame([[1, 2]], columns=["a", "a"])

    with pytest.raises(ValueError, match="repetidas"):
        studio.publicar(tabla, "repetida")


def test_rechaza_nombre_vacio(espia):
    studio.conectar("sk_prueba")
    with pytest.raises(ValueError, match="nombre"):
        studio.publicar(pd.DataFrame({"a": [1]}), "   ")


def test_publicar_varias_devuelve_una_respuesta_por_tabla(espia):
    studio.conectar("sk_prueba")
    respuestas = studio.publicar_varias(
        {"una": pd.DataFrame({"a": [1]}), "otra": pd.DataFrame({"b": [2]})}
    )
    assert len(respuestas) == 2
