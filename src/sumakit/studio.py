"""Adaptador entre el notebook y Suma Studio.

El EDA termina en un notebook que nadie reabre. Este módulo es el puente: la
tabla que acabas de mirar se publica en el proyecto y desde ahí alimenta el
deck y el informe, sin exportar un CSV a mano ni pegar una captura.

    from sumakit import studio

    client = studio.StudioClient("sk_...")   # la clave que da la app
    client.publish(alerts, "alertas")        # un DataFrame → una tabla del proyecto

**La API es el cliente.** No hay estado de módulo que compartir, así que sirve
igual en una celda de Colab, en un script, en un DAG o en un contenedor — que es
donde va a correr si la extracción se hace con dlt.

Las funciones sueltas `connect()` y `publish()` guardan un cliente por defecto y
existen **por compatibilidad** con los notebooks que ya las usan. No son la forma
recomendada: un global mutable no tiene sentido donde hay concurrencia o más de
un proyecto a la vez.

Lo que se publica son **tablas agregadas**, no el dataset crudo: un deck grafica
entre cinco y treinta puntos, y un informe embebe una tabla que cabe en la
página. El crudo se queda en el notebook, que es su lugar.

La clave es de escritura y de un solo proyecto. No sirve para leer nada, así
que puede vivir en un notebook de Colab compartido sin exponer el resto.

Los nombres en español —`conectar`, `publicar`— siguen funcionando con aviso de
obsolescencia: hay notebooks de Colab usando esta API y romperlos en silencio es
peor que la inconsistencia.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import warnings
from dataclasses import dataclass
from typing import Any

import pandas as pd

from ._compat import deprecated_alias

# El proyecto de Sumadots. Se puede apuntar a otro con variables de entorno,
# que es lo que hace falta para probar sin tocar la base de verdad.
DEFAULT_URL = "https://alaurkcvrikhiglcehfe.supabase.co"
DEFAULT_PUBLISHABLE_KEY = "sb_publishable_flF_ntpPnjmMP2IvcKj1_A_cy2MwMVI"

MAX_ROWS = 20_000

# La función de Postgres a la que llama el puente.
#
# **Por qué una función y no los endpoints REST de las tablas**, que es lo que
# alguien va a preguntar al leer esto: porque REST no está disponible. La clave
# de publicación **no es un JWT** —es un secreto opaco cuyo hash vive en
# `studio.publish_key`— así que el SDK habla como `anon`, y `anon` no tiene
# ningún permiso sobre `dataset`, `dataset_row` ni `publish_key`. La RLS decide
# con `auth.uid()`, que para `anon` es nulo: ninguna política puede expresar
# «esta clave escribe en este proyecto y en ninguno más». La función sí, porque
# es `security definer` y hace la búsqueda del hash ella misma.
#
# Eso es lo que permite que la clave viva en un Colab compartido. Con REST haría
# falta una sesión de usuario real, que es justo lo que no se quiere ahí.
#
# De regalo, y por eso no se echa de menos: publicar es borrar el conjunto
# anterior, insertar el nuevo, insertar N filas y tocar `last_used_at`. Por REST
# son cuatro viajes sin transacción, y re-ejecutar una celda podría dejar un
# conjunto a medio reemplazar. Acá es una transacción y un viaje.
#
# Todo esto se deduce del `ADR-0001` de suma-studio —el permiso se hace cumplir
# en Postgres— y por eso no tiene ADR propio: es su consecuencia, no una
# decisión aparte.
#
# El nombre cambió con el `ADR-0007` y este paquete se quedó apuntando al viejo:
# durante ese tiempo publicar respondía 404 y nadie se enteró, porque el SDK no
# tenía CI. La escotilla de compatibilidad de la base cubría las claves del
# jsonb, no el nombre de la función ni el de sus parámetros.
_RPC_PUBLISH = "publish_dataset"


class StudioError(RuntimeError):
    """Algo salió mal hablando con Studio. El mensaje viene del servidor."""


@dataclass(frozen=True)
class PublishResult:
    """Lo que Studio responde tras aceptar una tabla.

    Va tipado y no como `dict` porque quien lo recibe está en un notebook: un
    diccionario obliga a imprimirlo para saber qué trae.
    """

    dataset_id: str
    rows: int
    name: str

    @classmethod
    def _from_response(cls, payload: dict[str, Any]) -> PublishResult:
        return cls(
            dataset_id=str(payload.get("dataset_id", "")),
            rows=int(payload.get("rows", 0)),
            name=str(payload.get("name", "")),
        )


def _from_env(new: str, old: str, fallback: str = "") -> str:
    """Lee una variable de entorno aceptando también su nombre viejo.

    Args:
        new: El nombre actual, en inglés.
        old: El nombre en español, que sigue funcionando con aviso.
        fallback: Qué devolver si no está ninguna de las dos.

    Returns:
        El valor encontrado, o `fallback`.
    """
    if (value := os.environ.get(new)) is not None:
        return value
    if new != old and (value := os.environ.get(old)) is not None:
        warnings.warn(
            f"{old} se renombró a {new}; el nombre viejo dejará de leerse",
            DeprecationWarning,
            stacklevel=3,
        )
        return value
    return fallback


class StudioClient:
    """El cliente del proyecto: dónde publicar y con qué clave.

    Un cliente por proyecto. Se puede tener más de uno a la vez, que es lo que
    un global de módulo no permite y lo que hace falta para aislar una prueba.
    """

    def __init__(
        self,
        key: str | None = None,
        *,
        url: str | None = None,
        publishable_key: str | None = None,
    ) -> None:
        """Arma el cliente, tomando del entorno lo que no se le pase.

        Args:
            key: La clave de publicación del proyecto. `None` la busca en
                `SUMA_STUDIO_KEY`.
            url: La URL del proyecto de Supabase. Solo para apuntar a otra base.
            publishable_key: La clave pública de la API. Solo para apuntar a otra.

        Raises:
            StudioError: Si no hay clave ni en el argumento ni en el entorno.
        """
        key = key or _from_env("SUMA_STUDIO_KEY", "SUMA_STUDIO_CLAVE")
        if not key:
            raise StudioError(
                "falta la clave de publicación: créala en el proyecto, en Suma Studio, "
                "y pásala a connect() o déjala en SUMA_STUDIO_KEY"
            )

        self.key = key
        self.url = url or _from_env("SUMA_STUDIO_URL", "SUMA_STUDIO_URL", DEFAULT_URL)
        self.publishable_key = publishable_key or _from_env(
            "SUMA_STUDIO_PUBLISHABLE_KEY",
            "SUMA_STUDIO_CLAVE_PUBLICA",
            DEFAULT_PUBLISHABLE_KEY,
        )

    @property
    def endpoint(self) -> str:
        """La URL de las funciones RPC, que es lo único que este puente llama."""
        return f"{self.url.rstrip('/')}/rest/v1/rpc"

    def __repr__(self) -> str:
        """Sin la clave dentro: esto se imprime en notebooks que se comparten."""
        return f"StudioClient(url={self.url!r})"

    def _call(self, function: str, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.endpoint}/{function}",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "apikey": self.publishable_key,
                "Authorization": f"Bearer {self.publishable_key}",
                # Las funciones viven en el esquema `studio`, no en `public`.
                # Sin esta cabecera PostgREST busca en public y responde 404.
                "Content-Profile": "studio",
                "Accept-Profile": "studio",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")
            try:
                detail = json.loads(detail).get("message", detail)
            except json.JSONDecodeError:
                pass
            raise StudioError(detail) from error
        except urllib.error.URLError as error:
            raise StudioError(f"no se pudo llegar a Studio: {error.reason}") from error

    def publish(self, table: pd.DataFrame, name: str) -> PublishResult:
        """Publica un DataFrame como una tabla del proyecto.

        Republicar con el mismo nombre **reemplaza** la anterior: re-ejecutar
        una celda no debe dejar duplicados.

        El índice se conserva solo si tiene nombre; un índice numérico anónimo
        es ruido en una tabla que se va a graficar.

        Args:
            table: La tabla agregada que se quiere en el proyecto.
            name: Cómo se va a llamar en el SQL de Studio.

        Returns:
            El id del conjunto, cuántas filas entraron y con qué nombre.

        Raises:
            TypeError: Si `table` no es un DataFrame.
            ValueError: Si el nombre va vacío, hay columnas repetidas, o son
                demasiadas filas para lo que un entregable puede mostrar.
            StudioError: Si Studio rechaza la publicación o no responde.
        """
        if not isinstance(table, pd.DataFrame):
            raise TypeError(f"publish espera un DataFrame, no {type(table).__name__}")

        name = name.strip()
        if not name:
            raise ValueError("la tabla necesita un nombre: es cómo la vas a llamar en el SQL")

        if table.index.name:
            table = table.reset_index()

        if len(table) > MAX_ROWS:
            raise ValueError(
                f"son {len(table):,} filas. Publica la tabla agregada, no el dataset crudo: "
                "un deck grafica entre cinco y treinta puntos"
            )

        if table.columns.duplicated().any():
            repeated = table.columns[table.columns.duplicated()].unique().tolist()
            raise ValueError(f"hay columnas repetidas: {', '.join(repeated)}")

        columns = [
            {"name": str(column), "kind": _column_kind(table[column])} for column in table.columns
        ]

        return PublishResult._from_response(
            self._call(
                _RPC_PUBLISH,
                {
                    "p_key": self.key,
                    "p_name": name,
                    "p_columns": columns,
                    "p_rows": _serialize(table),
                },
            )
        )

    def publish_many(self, tables: dict[str, pd.DataFrame]) -> list[PublishResult]:
        """Publica varias de una vez. Útil al final de un EDA.

        Args:
            tables: Nombre en Studio → la tabla que va con él.

        Returns:
            Una respuesta por tabla, en el orden en que se pasaron.
        """
        return [self.publish(table, name) for name, table in tables.items()]


def _column_kind(series: pd.Series) -> str:
    """El tipo que entiende Studio: solo distingue número de texto."""
    return "number" if pd.api.types.is_numeric_dtype(series) else "text"


def _serialize(table: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame → filas JSON, sin NaN ni tipos que json no sepa escribir."""
    clean = table.copy()

    for column in clean.columns:
        if pd.api.types.is_datetime64_any_dtype(clean[column]):
            clean[column] = clean[column].dt.strftime("%Y-%m-%d")
        elif not pd.api.types.is_numeric_dtype(clean[column]):
            clean[column] = clean[column].astype(str)

    # NaN no es JSON válido; va como null, que es lo que significa.
    return json.loads(clean.to_json(orient="records", date_format="iso"))


# ─── Compatibilidad: el cliente por defecto ──────────────────────────────────
#
# Un cliente guardado en el módulo. **No es la forma recomendada**, y se
# conserva porque hay notebooks que ya llaman así. Un global mutable no tiene
# sentido en un servicio: no hay «sesión», puede haber varios proyectos a la vez
# y hay concurrencia. Es el mismo camino que recorrió Brevo, que en su v5 quitó
# el objeto de configuración global y dejó `Brevo(api_key=...)`.

_default_client: StudioClient | None = None


def connect(
    key: str | None = None,
    *,
    url: str | None = None,
    publishable_key: str | None = None,
) -> StudioClient:
    """Arma un cliente, lo guarda como el de por defecto y lo devuelve.

    Prefiere `StudioClient(...)` directamente: devuelve lo mismo sin dejar
    estado en el módulo. Esto existe por los notebooks que ya lo usan.

    Sin argumento, la clave sale de `SUMA_STUDIO_KEY`. En Colab conviene el
    gestor de secretos en vez de escribirla en una celda:

        from google.colab import userdata
        studio.connect(userdata.get("SUMA_STUDIO_KEY"))

    Args:
        key: La clave de publicación del proyecto.
        url: La URL del proyecto de Supabase.
        publishable_key: La clave pública de la API.

    Returns:
        El cliente, que además queda como el de por defecto.
    """
    global _default_client
    _default_client = StudioClient(key, url=url, publishable_key=publishable_key)
    return _default_client


def _active_client() -> StudioClient:
    if _default_client is None:
        raise StudioError("primero llama a studio.connect(...) con tu clave")
    return _default_client


def publish(table: pd.DataFrame, name: str) -> PublishResult:
    """Publica con el cliente por defecto. Prefiere `StudioClient.publish`."""
    return _active_client().publish(table, name)


def publish_many(tables: dict[str, pd.DataFrame]) -> list[PublishResult]:
    """Publica varias con el cliente por defecto. Prefiere `StudioClient.publish_many`."""
    return _active_client().publish_many(tables)


# ─── Nombres viejos ──────────────────────────────────────────────────────────
#
# La API pública de un SDK es un contrato con gente a la que no puedes llamar.
# Hay notebooks de Colab con `studio.conectar(...)` escrito dentro, y romperlos
# en silencio es peor que la inconsistencia que esto vino a arreglar.


conectar = deprecated_alias(connect, "conectar", "connect", module="studio")
publicar = deprecated_alias(publish, "publicar", "publish", module="studio")
publicar_varias = deprecated_alias(publish_many, "publicar_varias", "publish_many", module="studio")

#: Obsoleto: usa `StudioError`. Es la misma clase y no una subclase, para que un
#: `except ErrorDeStudio` viejo siga atrapando lo que lanza el código nuevo.
ErrorDeStudio = StudioError
#: Obsoleto: usa `StudioClient`.
Conexion = StudioClient

__all__ = [
    "MAX_ROWS",
    "PublishResult",
    "StudioClient",
    "StudioError",
    "connect",
    "publish",
    "publish_many",
]
