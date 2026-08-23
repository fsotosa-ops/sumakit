"""Adaptador entre el notebook y Suma Studio.

El EDA termina en un notebook que nadie reabre. Este módulo es el puente: la
tabla que acabas de mirar se publica en el proyecto y desde ahí alimenta el
deck y el informe, sin exportar un CSV a mano ni pegar una captura.

    from sumakit import studio

    studio.conectar("sk_...")               # la clave que da la app
    studio.publicar(alertas, "alertas")     # un DataFrame → una tabla del proyecto

Lo que se publica son **tablas agregadas**, no el dataset crudo: un deck grafica
entre cinco y treinta puntos, y un informe embebe una tabla que cabe en la
página. El crudo se queda en el notebook, que es su lugar.

La clave es de escritura y de un solo proyecto. No sirve para leer nada, así
que puede vivir en un notebook de Colab compartido sin exponer el resto.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

import pandas as pd

# El proyecto de Sumadots. Se puede apuntar a otro con variables de entorno,
# que es lo que hace falta para probar sin tocar la base de verdad.
URL_POR_DEFECTO = "https://alaurkcvrikhiglcehfe.supabase.co"
CLAVE_PUBLICA_POR_DEFECTO = "sb_publishable_flF_ntpPnjmMP2IvcKj1_A_cy2MwMVI"

MAX_FILAS = 20_000


class ErrorDeStudio(RuntimeError):
    """Algo salió mal hablando con Studio. El mensaje viene del servidor."""


@dataclass
class Conexion:
    clave: str
    url: str = URL_POR_DEFECTO
    clave_publica: str = CLAVE_PUBLICA_POR_DEFECTO

    @property
    def endpoint(self) -> str:
        return f"{self.url.rstrip('/')}/rest/v1/rpc"


_conexion: Conexion | None = None


def conectar(
    clave: str | None = None,
    *,
    url: str | None = None,
    clave_publica: str | None = None,
) -> Conexion:
    """Guarda la clave de publicación para el resto de la sesión.

    Sin argumento, la busca en `SUMA_STUDIO_CLAVE`. En Colab conviene el
    gestor de secretos en vez de escribirla en una celda:

        from google.colab import userdata
        studio.conectar(userdata.get("SUMA_STUDIO_CLAVE"))
    """
    global _conexion

    clave = clave or os.environ.get("SUMA_STUDIO_CLAVE", "")
    if not clave:
        raise ErrorDeStudio(
            "falta la clave de publicación: créala en el proyecto, en Suma Studio, "
            "y pásala a conectar() o déjala en SUMA_STUDIO_CLAVE"
        )

    _conexion = Conexion(
        clave=clave,
        url=url or os.environ.get("SUMA_STUDIO_URL", URL_POR_DEFECTO),
        clave_publica=clave_publica
        or os.environ.get("SUMA_STUDIO_CLAVE_PUBLICA", CLAVE_PUBLICA_POR_DEFECTO),
    )
    return _conexion


def _conexion_activa() -> Conexion:
    if _conexion is None:
        raise ErrorDeStudio("primero llama a studio.conectar(...) con tu clave")
    return _conexion


def _llamar(funcion: str, cuerpo: dict) -> dict:
    conexion = _conexion_activa()
    peticion = urllib.request.Request(
        f"{conexion.endpoint}/{funcion}",
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "apikey": conexion.clave_publica,
            "Authorization": f"Bearer {conexion.clave_publica}",
            # Las funciones viven en el esquema `studio`, no en `public`.
            # Sin esta cabecera PostgREST busca en public y responde 404.
            "Content-Profile": "studio",
            "Accept-Profile": "studio",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detalle = error.read().decode("utf-8", "replace")
        try:
            detalle = json.loads(detalle).get("message", detalle)
        except json.JSONDecodeError:
            pass
        raise ErrorDeStudio(detalle) from error
    except urllib.error.URLError as error:
        raise ErrorDeStudio(f"no se pudo llegar a Studio: {error.reason}") from error


def _tipo_de_columna(serie: pd.Series) -> str:
    return "numero" if pd.api.types.is_numeric_dtype(serie) else "texto"


def _serializar(tabla: pd.DataFrame) -> list[dict]:
    """DataFrame → filas JSON, sin NaN ni tipos que json no sepa escribir."""
    limpio = tabla.copy()

    for columna in limpio.columns:
        if pd.api.types.is_datetime64_any_dtype(limpio[columna]):
            limpio[columna] = limpio[columna].dt.strftime("%Y-%m-%d")
        elif not pd.api.types.is_numeric_dtype(limpio[columna]):
            limpio[columna] = limpio[columna].astype(str)

    # NaN no es JSON válido; va como null, que es lo que significa.
    return json.loads(limpio.to_json(orient="records", date_format="iso"))


def publicar(tabla: pd.DataFrame, nombre: str) -> dict:
    """Publica un DataFrame como una tabla del proyecto.

    Republicar con el mismo nombre **reemplaza** la anterior: re-ejecutar una
    celda no debe dejar duplicados.

        studio.publicar(profile.alerts(df), "alertas")
        studio.publicar(gasto_por_ocasion, "gasto por ocasión")

    El índice se conserva solo si tiene nombre; un índice numérico anónimo es
    ruido en una tabla que se va a graficar.
    """
    if not isinstance(tabla, pd.DataFrame):
        raise TypeError(f"publicar espera un DataFrame, no {type(tabla).__name__}")

    nombre = nombre.strip()
    if not nombre:
        raise ValueError("la tabla necesita un nombre: es cómo la vas a llamar en el SQL")

    if tabla.index.name:
        tabla = tabla.reset_index()

    if len(tabla) > MAX_FILAS:
        raise ValueError(
            f"son {len(tabla):,} filas. Publica la tabla agregada, no el dataset crudo: "
            "un deck grafica entre cinco y treinta puntos"
        )

    if tabla.columns.duplicated().any():
        repetidas = tabla.columns[tabla.columns.duplicated()].unique().tolist()
        raise ValueError(f"hay columnas repetidas: {', '.join(repetidas)}")

    columnas = [
        {"nombre": str(columna), "tipo": _tipo_de_columna(tabla[columna])}
        for columna in tabla.columns
    ]

    respuesta = _llamar(
        "publicar_conjunto",
        {
            "p_clave": _conexion_activa().clave,
            "p_nombre": nombre,
            "p_columnas": columnas,
            "p_filas": _serializar(tabla),
        },
    )

    return respuesta


def publicar_varias(tablas: dict[str, pd.DataFrame]) -> list[dict]:
    """Publica varias de una vez. Útil al final de un EDA.

        studio.publicar_varias({
            "alertas": profile.alerts(df),
            "distribuciones": stats.distribution_report(df),
        })
    """
    return [publicar(tabla, nombre) for nombre, tabla in tablas.items()]
