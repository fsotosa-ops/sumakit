"""El diagnóstico de una segmentación: elegir k, y explicar en qué se distingue.

sumakit no ajusta ningún modelo. Estas funciones reciben etiquetas o modelos ya
entrenados; el bucle que los entrena vive a la vista en el notebook, porque en
un taller lo que se evalúa es justamente esa llamada.
"""

import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure

pytest.importorskip("sklearn")

from sklearn.cluster import KMeans  # noqa: E402

from sumakit import cluster, plots  # noqa: E402


@pytest.fixture
def datos():
    """Tres grupos separados de verdad, para que el diagnóstico tenga qué ver.

    Cada grupo es alto en una variable y bajo en las otras dos, así que la tabla
    de perfilado tiene una respuesta inequívoca y se puede afirmar sobre ella.
    """
    rng = np.random.default_rng(0)
    centros = {"a": (10, 0, 0), "b": (0, 10, 0), "c": (0, 0, 10)}
    filas, etiquetas = [], []
    for nombre, centro in centros.items():
        n = {"a": 60, "b": 30, "c": 10}[nombre]  # desbalanceado a propósito
        filas.append(rng.normal(centro, 0.5, (n, 3)))
        etiquetas += [nombre] * n
    X = pd.DataFrame(np.vstack(filas), columns=["monto", "frecuencia", "antiguedad"])
    return X, np.array(etiquetas)


@pytest.fixture
def modelos(datos):
    X, _ = datos
    return {k: KMeans(n_clusters=k, random_state=0, n_init=10).fit(X) for k in range(2, 6)}


# --- k_report ---------------------------------------------------------------


def test_k_report_una_fila_por_modelo(datos, modelos):
    X, _ = datos
    out = cluster.k_report(X, modelos)
    assert list(out.index) == [2, 3, 4, 5]
    assert out.index.name == "k"


def test_k_report_encuentra_el_k_verdadero(datos, modelos):
    """Los datos tienen tres grupos; la silueta debe señalarlos."""
    X, _ = datos
    out = cluster.k_report(X, modelos)
    assert out["silhouette"].idxmax() == 3


def test_k_report_trae_las_cuatro_metricas(datos, modelos):
    X, _ = datos
    out = cluster.k_report(X, modelos)
    assert list(out.columns) == ["inertia", "silhouette", "calinski_harabasz", "davies_bouldin"]


def test_k_report_tolera_un_modelo_sin_inertia(datos, modelos):
    """No todo algoritmo de segmentación tiene inercia; el jerárquico no."""
    from sklearn.cluster import AgglomerativeClustering

    X, _ = datos
    modelos[3] = AgglomerativeClustering(n_clusters=3).fit(X)
    out = cluster.k_report(X, modelos)
    assert np.isnan(out.loc[3, "inertia"])
    assert not np.isnan(out.loc[3, "silhouette"]), "las demás métricas sí se calculan"


def test_k_report_vacio_si_no_hay_modelos(datos):
    X, _ = datos
    assert cluster.k_report(X, {}).empty


# --- sizes ------------------------------------------------------------------


def test_sizes_cuenta_y_reparte(datos):
    _, etiquetas = datos
    out = cluster.sizes(etiquetas)
    assert out["n"].sum() == 100
    assert out["pct"].sum() == pytest.approx(100.0)


def test_sizes_pone_el_desbalance_arriba(datos):
    """Un grupo que se come el 60% invalida la segmentación: que se vea primero."""
    _, etiquetas = datos
    out = cluster.sizes(etiquetas)
    assert out.index[0] == "a"
    assert out["n"].is_monotonic_decreasing


# --- segments ---------------------------------------------------------------


def test_segments_dice_en_que_se_distingue_cada_grupo(datos):
    X, etiquetas = datos
    out = cluster.segments(X, etiquetas)
    fila = out[(out["cluster"] == "b") & (out["feature"] == "frecuencia")].iloc[0]
    assert fila["z"] > 1, "el grupo b es alto en frecuencia y la tabla debe decirlo"
    assert fila["mean"] > fila["overall"]


def test_segments_compara_contra_el_promedio_global(datos):
    X, etiquetas = datos
    out = cluster.segments(X, etiquetas)
    esperado = X["monto"].mean()
    assert out[out["feature"] == "monto"]["overall"].unique() == pytest.approx(esperado)


def test_segments_pone_lo_mas_distintivo_primero(datos):
    X, etiquetas = datos
    out = cluster.segments(X, etiquetas)
    primero = out[out["cluster"] == "c"].iloc[0]
    assert primero["feature"] == "antiguedad"


def test_segments_ignora_las_columnas_no_numericas(datos):
    X, etiquetas = datos
    X = X.assign(ciudad=["bogota"] * 100)
    assert "ciudad" not in set(cluster.segments(X, etiquetas)["feature"])


def test_segments_no_divide_por_cero_en_una_constante(datos):
    """Una columna constante tiene desviación 0: z sería inf y ensucia todo."""
    X, etiquetas = datos
    X = X.assign(plan=1.0)
    z = cluster.segments(X, etiquetas).query("feature == 'plan'")["z"]
    assert np.isfinite(z).all()
    assert (z == 0).all()


def test_segments_exige_una_etiqueta_por_fila(datos):
    X, etiquetas = datos
    with pytest.raises(ValueError, match="etiquetas"):
        cluster.segments(X, etiquetas[:-1])


# --- distinctive ------------------------------------------------------------


def test_distinctive_recorta_a_las_top(datos):
    X, etiquetas = datos
    out = cluster.distinctive(X, etiquetas, top=2)
    assert (out.groupby("cluster").size() == 2).all()


def test_distinctive_dice_si_es_alto_o_bajo(datos):
    X, etiquetas = datos
    out = cluster.distinctive(X, etiquetas, top=3)
    fila = out[(out["cluster"] == "a") & (out["feature"] == "monto")].iloc[0]
    assert fila["direction"] == "alto"
    otra = out[(out["cluster"] == "a") & (out["feature"] == "frecuencia")].iloc[0]
    assert otra["direction"] == "bajo"


# --- las figuras ------------------------------------------------------------


def test_elbow_devuelve_figure(datos, modelos):
    X, _ = datos
    assert isinstance(plots.elbow(cluster.k_report(X, modelos)), Figure)


def test_elbow_consume_la_tabla_no_los_datos(datos, modelos):
    """Si dibujara recalculando, habría dos fuentes de verdad para el mismo codo."""
    X, _ = datos
    tabla = cluster.k_report(X, modelos)
    fig = plots.elbow(tabla)
    assert len(fig.axes) == 2, "un panel para la inercia y otro para la silueta"


def test_silhouette_devuelve_figure(datos):
    X, etiquetas = datos
    assert isinstance(plots.silhouette(X, etiquetas), Figure)


def test_segments_devuelve_figure(datos):
    X, etiquetas = datos
    assert isinstance(plots.segments(cluster.segments(X, etiquetas)), Figure)


# --- el mensaje cuando falta el extra ---------------------------------------


def test_sin_sklearn_dice_que_extra_instalar(monkeypatch):
    """Un `ModuleNotFoundError: sklearn` no le dice a nadie qué hacer.

    `cluster` es el único módulo del paquete que exige un extra, así que es el
    único donde este mensaje importa.
    """
    import builtins
    import sys

    import sumakit

    # Importar el submódulo lo deja pegado como atributo del paquete, y ahí
    # `__getattr__` ya no se consulta. Hay que quitar las dos copias.
    monkeypatch.delitem(sys.modules, "sumakit.cluster", raising=False)
    monkeypatch.delattr(sumakit, "cluster", raising=False)
    real = builtins.__import__

    def sin_sklearn(nombre, *a, **k):
        if nombre.startswith("sklearn"):
            raise ModuleNotFoundError("No module named 'sklearn'")
        return real(nombre, *a, **k)

    monkeypatch.setattr(builtins, "__import__", sin_sklearn)

    with pytest.raises(ModuleNotFoundError, match="extra `ml`"):
        _ = sumakit.cluster
