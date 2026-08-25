"""Diagnóstico de una segmentación: elegir `k`, y explicar en qué se distingue.

**Ninguna función de aquí ajusta un modelo.** Reciben etiquetas —`modelo.labels_`—
o modelos ya entrenados, y devuelven tablas. La razón no es de arquitectura: esto
se usa en talleres donde lo evaluado es que sepas aplicar el método, así que la
llamada al algoritmo tiene que estar a la vista en el notebook y no escondida
dentro de una función de la librería.

    modelos = {k: KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
               for k in range(2, 9)}
    profile.styled(cluster.k_report(X, modelos))   # ¿cuál k?
    profile.styled(cluster.segments(df, km.labels_))  # ¿qué es cada grupo?

`k_report` responde la primera pregunta y `segments` la segunda, que es la que
llega a la presentación: un cluster sin una frase que lo describa no es un
segmento, es un número.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)

__all__ = ["k_report", "sizes", "segments", "distinctive"]

_METRICAS = ["inertia", "silhouette", "calinski_harabasz", "davies_bouldin"]

# `X` en mayúscula viola N803 a propósito. Es la convención de scikit-learn
# —mayúscula la matriz, minúscula el vector— y la respeta todo el ecosistema.
# Renombrarla a `x` haría que este módulo fuera el único sitio donde la firma no
# se parece a la que quien lo usa acaba de escribir.


def _etiquetas(labels: Any, n: int | None = None) -> np.ndarray:
    out = np.asarray(labels)
    if n is not None and len(out) != n:
        raise ValueError(f"hay {len(out)} etiquetas para {n} filas: debe haber una por fila")
    return out


def _separacion(X: Any, etiquetas: np.ndarray) -> dict[str, float]:  # noqa: N803
    """Las tres métricas que solo tienen sentido con más de un grupo.

    Con un solo cluster —o con tantos como filas— no hay separación que medir y
    scikit-learn levanta una excepción. Devolver NaN deja la fila en la tabla,
    que es lo que permite comparar ese k contra los demás en vez de perderlo.
    """
    distintas = len(np.unique(etiquetas))
    if not 2 <= distintas <= len(etiquetas) - 1:
        return dict.fromkeys(_METRICAS[1:], float("nan"))
    return {
        "silhouette": float(silhouette_score(X, etiquetas)),
        "calinski_harabasz": float(calinski_harabasz_score(X, etiquetas)),
        "davies_bouldin": float(davies_bouldin_score(X, etiquetas)),
    }


def k_report(X: Any, models: dict[int, Any]) -> pd.DataFrame:  # noqa: N803
    """Una fila por modelo, para elegir `k` mirando números y no la forma de una curva.

    `models` es el diccionario `{k: modelo_ajustado}` que armaste tú. Cuatro
    métricas porque ninguna basta sola: la inercia siempre baja al subir `k` —el
    "codo" es un juicio visual—, mientras que la silueta y Calinski-Harabasz
    tienen máximo y Davies-Bouldin tiene mínimo. Cuando las tres coinciden, la
    decisión se defiende sola en el informe.

    Un modelo sin `inertia_` (el jerárquico, por ejemplo) deja esa celda en NaN
    y conserva el resto.
    """
    if not models:
        return pd.DataFrame(columns=_METRICAS, index=pd.Index([], name="k"))

    filas = {}
    for k, modelo in sorted(models.items()):
        etiquetas = _etiquetas(modelo.labels_)
        filas[k] = {
            "inertia": float(getattr(modelo, "inertia_", float("nan"))),
            **_separacion(X, etiquetas),
        }

    out = pd.DataFrame.from_dict(filas, orient="index")[_METRICAS]
    out.index.name = "k"
    return out


def sizes(labels: Any) -> pd.DataFrame:
    """Cuántas filas cayó en cada grupo, del más grande al más pequeño.

    Va ordenado por tamaño y no por etiqueta a propósito: un cluster que se come
    el 80% de los datos no es una segmentación, y un cluster de doce filas no
    sostiene una recomendación de negocio. Los dos defectos aparecen en los
    extremos de esta tabla.
    """
    s = pd.Series(_etiquetas(labels))
    n = s.value_counts()
    out = pd.DataFrame({"n": n, "pct": (n / len(s) * 100).round(2)})
    out.index.name = "cluster"
    return out


def segments(df: pd.DataFrame, labels: Any) -> pd.DataFrame:
    """En qué se desvía cada grupo del promedio, en unidades comparables.

    La columna que importa es `z`: la distancia entre la media del grupo y la
    media global, medida en desviaciones estándar de la variable. Sin
    estandarizar no se pueden comparar un monto en pesos con una antigüedad en
    meses, y la tabla acaba diciendo que el monto siempre es lo más importante
    porque es lo que tiene números más grandes.

    Sale en formato largo —una fila por grupo y variable— para que se pueda
    filtrar y ordenar, y con lo más distintivo de cada grupo arriba.
    `plots.segments` la consume tal cual.
    """
    etiquetas = _etiquetas(labels, len(df))
    num = df.select_dtypes(include=np.number)

    media_global = num.mean()
    # Una columna constante tiene desviación 0. Dividir por ella da inf y
    # contamina el orden entero de la tabla; su desviación real es cero.
    escala = num.std().replace(0, np.nan)

    por_cluster = num.groupby(etiquetas).mean()
    por_cluster.index.name = "cluster"
    por_cluster.columns.name = "feature"
    z = ((por_cluster - media_global) / escala).fillna(0.0)

    out = pd.DataFrame({"mean": por_cluster.stack(), "z": z.stack().round(2)}).reset_index()
    out["overall"] = out["feature"].map(media_global)

    orden = out["z"].abs().rename("_fuerza")
    return (
        out.join(orden)
        .sort_values(["cluster", "_fuerza"], ascending=[True, False])
        .drop(columns="_fuerza")
        .reset_index(drop=True)[["cluster", "feature", "mean", "overall", "z"]]
    )


def distinctive(df: pd.DataFrame, labels: Any, *, top: int = 3) -> pd.DataFrame:
    """Las `top` variables que más distinguen a cada grupo, con su dirección.

    Es `segments` recortado a lo que cabe en el título de una lámina. `direction`
    traduce el signo de `z` para que no haya que leerlo: un hallazgo se escribe
    "compran mucho y hace poco", no "z = 2.1, z = -1.8".
    """
    out = segments(df, labels).groupby("cluster", group_keys=False).head(top).copy()
    out["direction"] = np.where(out["z"] >= 0, "alto", "bajo")
    return out.reset_index(drop=True)
