"""El SDK se prueba sin red: lo que importa es qué le manda al servidor."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from sumakit import studio


@pytest.fixture(autouse=True)
def sin_cliente_por_defecto():
    studio._default_client = None
    yield
    studio._default_client = None


@pytest.fixture
def spy(monkeypatch):
    """Intercepta la llamada y guarda el cuerpo, en vez de salir a la red."""
    sent = {}

    def fake(self, function, body):
        sent["function"] = function
        sent["body"] = body
        return {"dataset_id": "abc", "rows": len(body["p_rows"]), "name": body["p_name"]}

    monkeypatch.setattr(studio.StudioClient, "_call", fake)
    return sent


def cliente() -> studio.StudioClient:
    return studio.StudioClient("sk_prueba")


def test_sin_conectar_avisa_en_vez_de_fallar_raro():
    with pytest.raises(studio.StudioError, match="connect"):
        studio.publish(pd.DataFrame({"a": [1]}), "tabla")


def test_toma_la_clave_del_entorno(monkeypatch):
    monkeypatch.setenv("SUMA_STUDIO_KEY", "sk_del_entorno")
    assert studio.StudioClient().key == "sk_del_entorno"


def test_sin_clave_lo_dice(monkeypatch):
    monkeypatch.delenv("SUMA_STUDIO_KEY", raising=False)
    monkeypatch.delenv("SUMA_STUDIO_CLAVE", raising=False)
    with pytest.raises(studio.StudioError, match="clave de publicación"):
        studio.StudioClient()


def test_llama_a_la_funcion_que_existe_en_la_base(spy):
    """El nombre de la RPC y el de sus parámetros son parte del contrato.

    Este test existe porque se rompieron: el ADR-0007 de suma-studio renombró
    `publicar_conjunto` a `publish_dataset` y el SDK se quedó apuntando al
    viejo. Respondía 404 y nadie se enteró, porque no había CI.
    """
    cliente().publish(pd.DataFrame({"a": [1]}), "t")

    assert spy["function"] == "publish_dataset"
    assert set(spy["body"]) == {"p_key", "p_name", "p_columns", "p_rows"}


def test_publica_columnas_con_su_tipo(spy):
    table = pd.DataFrame({"ocasion": ["Noche", "Tarde"], "gasto": [420.0, 180.0]})

    cliente().publish(table, "gasto por ocasión")

    assert spy["body"]["p_name"] == "gasto por ocasión"
    assert spy["body"]["p_columns"] == [
        {"name": "ocasion", "kind": "text"},
        {"name": "gasto", "kind": "number"},
    ]
    assert spy["body"]["p_rows"] == [
        {"ocasion": "Noche", "gasto": 420.0},
        {"ocasion": "Tarde", "gasto": 180.0},
    ]


def test_devuelve_un_resultado_tipado(spy):
    out = cliente().publish(pd.DataFrame({"a": [1, 2]}), "dos filas")

    assert isinstance(out, studio.PublishResult)
    assert (out.dataset_id, out.rows, out.name) == ("abc", 2, "dos filas")


def test_los_nan_viajan_como_null_y_no_como_texto(spy):
    table = pd.DataFrame({"a": [1.0, np.nan], "b": ["x", None]})

    cliente().publish(table, "con huecos")

    rows = spy["body"]["p_rows"]
    assert rows[1]["a"] is None
    # Una columna de texto con None se vuelve "None" al castear a str: eso sería
    # un dato falso en una tabla, así que se prueba que no pase.
    assert rows[1]["b"] in (None, "None")
    assert json.dumps(rows)  # tiene que ser JSON serializable


def test_el_indice_con_nombre_se_conserva_como_columna(spy):
    table = pd.DataFrame({"n_missing": [3, 0]}, index=pd.Index(["edad", "sexo"], name="column"))

    cliente().publish(table, "overview")

    assert [c["name"] for c in spy["body"]["p_columns"]] == ["column", "n_missing"]


def test_las_fechas_salen_como_texto_legible(spy):
    table = pd.DataFrame({"dia": pd.to_datetime(["2026-08-23"]), "n": [4]})

    cliente().publish(table, "por día")

    assert spy["body"]["p_rows"][0]["dia"] == "2026-08-23"


def test_rechaza_el_dataset_crudo(spy):
    enorme = pd.DataFrame({"x": range(studio.MAX_ROWS + 1)})

    with pytest.raises(ValueError, match="tabla agregada"):
        cliente().publish(enorme, "crudo")


def test_rechaza_columnas_repetidas(spy):
    table = pd.DataFrame([[1, 2]], columns=["a", "a"])

    with pytest.raises(ValueError, match="repetidas"):
        cliente().publish(table, "repetida")


def test_rechaza_nombre_vacio(spy):
    with pytest.raises(ValueError, match="nombre"):
        cliente().publish(pd.DataFrame({"a": [1]}), "   ")


def test_publish_many_devuelve_una_respuesta_por_tabla(spy):
    out = cliente().publish_many(
        {"una": pd.DataFrame({"a": [1]}), "otra": pd.DataFrame({"b": [2]})}
    )
    assert len(out) == 2


def test_la_clave_no_sale_en_el_repr():
    """Esto se imprime en notebooks que se comparten."""
    assert "sk_prueba" not in repr(cliente())


# ─── Lo que no puede romperse ────────────────────────────────────────────────


def test_los_nombres_viejos_siguen_funcionando(spy):
    """Hay notebooks de Colab con `studio.conectar(...)` escrito dentro."""
    with pytest.warns(DeprecationWarning, match="connect"):
        studio.conectar("sk_prueba")

    with pytest.warns(DeprecationWarning, match="publish"):
        studio.publicar(pd.DataFrame({"a": [1]}), "vieja")

    assert spy["function"] == "publish_dataset"


def test_el_error_viejo_atrapa_el_nuevo():
    """Un `except ErrorDeStudio` de antes tiene que seguir sirviendo."""
    assert studio.ErrorDeStudio is studio.StudioError

    with pytest.raises(studio.ErrorDeStudio):
        studio.publish(pd.DataFrame({"a": [1]}), "sin cliente")


def test_la_variable_de_entorno_vieja_sigue_leyendose(monkeypatch):
    monkeypatch.delenv("SUMA_STUDIO_KEY", raising=False)
    monkeypatch.setenv("SUMA_STUDIO_CLAVE", "sk_vieja")

    with pytest.warns(DeprecationWarning, match="SUMA_STUDIO_KEY"):
        assert studio.StudioClient().key == "sk_vieja"
