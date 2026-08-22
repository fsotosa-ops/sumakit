"""Los gráficos devuelven Figure, no None, y sobreviven a los casos límite."""

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from matplotlib.figure import Figure

from sumakit import plots, theme


# --- regresiones de los bugs encontrados en eda_utils.py --------------------

def test_distributions_con_una_sola_columna(df_una_columna):
    """Antes: AttributeError 'Axes' object has no attribute 'flatten'."""
    fig = plots.distributions(df_una_columna)
    assert isinstance(fig, Figure)
    assert len(fig.axes) == 1


def test_distributions_sin_columnas_numericas(df_sin_numericas):
    """Antes: ZeroDivisionError: division by zero."""
    fig = plots.distributions(df_sin_numericas)
    assert isinstance(fig, Figure)


def test_boxes_con_una_sola_columna(df_una_columna):
    assert isinstance(plots.boxes(df_una_columna), Figure)


def test_boxes_sin_columnas_numericas(df_sin_numericas):
    assert isinstance(plots.boxes(df_sin_numericas), Figure)


# --- la regla de diseño: devolver, no mostrar -------------------------------

@pytest.mark.parametrize("fn", ["distributions", "boxes", "correlation_heatmap", "missing_matrix"])
def test_devuelven_figure(df, fn):
    fig = getattr(plots, fn)(df)
    assert isinstance(fig, Figure), f"{fn} debe devolver Figure"


def test_ninguna_funcion_deja_figuras_abiertas(df):
    """Si una función llamara plt.show(), el conteo de figuras se descuadraría."""
    plt.close("all")
    fig = plots.distributions(df)
    assert len(plt.get_fignums()) == 1
    plt.close(fig)
    assert len(plt.get_fignums()) == 0


def test_no_muta_estado_global_de_seaborn(df):
    """El original llamaba sns.reset_defaults() y cambiaba el estilo siguiente."""
    theme.use(theme.LIGHT)
    antes = dict(plt.rcParams)
    plots.distributions(df)
    plots.correlation_heatmap(df)
    plt.close("all")
    cambiadas = {k for k in antes if plt.rcParams[k] != antes[k]}
    assert not cambiadas, f"rcParams mutados: {cambiadas}"


# --- comportamiento ---------------------------------------------------------

def test_grilla_contiene_todos_los_paneles(df):
    n_num = df.select_dtypes("number").shape[1]
    fig = plots.distributions(df)
    assert len(fig.axes) == n_num, "sobran o faltan paneles"


def test_grilla_explicita_insuficiente_falla(df):
    with pytest.raises(ValueError, match="no cabe"):
        plots.distributions(df, num_rows=1, num_cols=1)


def test_columna_inexistente_falla(df):
    with pytest.raises(KeyError, match="ausentes"):
        plots.distributions(df, columns=["no_existe"])


def test_heatmap_apaga_anotaciones_con_muchas_variables():
    import numpy as np
    ancho = pd.DataFrame(np.random.rand(30, 20), columns=[f"v{i}" for i in range(20)])
    fig = plots.correlation_heatmap(ancho)
    textos = [t for t in fig.axes[0].texts]
    assert not textos, "con 20 variables los números no se leen; deben apagarse"


def test_heatmap_necesita_dos_columnas(df_una_columna):
    assert isinstance(plots.correlation_heatmap(df_una_columna), Figure)


def test_missing_matrix_sin_nulos(df_una_columna):
    assert isinstance(plots.missing_matrix(df_una_columna), Figure)


def test_pairs_rechaza_demasiadas_variables():
    import numpy as np
    ancho = pd.DataFrame(np.random.rand(20, 12), columns=[f"v{i}" for i in range(12)])
    with pytest.raises(ValueError, match="ilegibles"):
        plots.pairs(ancho)


def test_pairs_respeta_el_limite_de_tres_series(df):
    """4 niveles en una forma de todos-los-pares debe fallar, no colorear mal."""
    d = df.copy()
    d["cuatro"] = ["a", "b", "c", "d"] * (len(d) // 4)
    with pytest.raises(ValueError, match="máximo validado es 3"):
        plots.pairs(d, columns=["normal", "sesgada"], hue="cuatro")


def test_scaling_comparison_acepta_ndarray(df):
    pytest.importorskip("sklearn")
    from sklearn.preprocessing import StandardScaler
    feats = ["normal", "sesgada"]
    escalado = StandardScaler().fit_transform(df[feats])
    fig = plots.scaling_comparison(df, escalado, feats)
    assert isinstance(fig, Figure)


def test_variable_discreta_se_dibuja_como_conteo():
    """Un KDE sobre enteros con pocos niveles inventa masa entre valores."""
    d = pd.DataFrame({"calificacion": [3, 4, 5, 5, 6, 6, 6, 7, 8] * 10})
    fig = plots.distributions(d)
    ax = fig.axes[0]
    assert len(ax.patches) == 6, "debe haber una barra por nivel, no una curva"


def test_variable_continua_sigue_siendo_densidad(df):
    fig = plots.distributions(df, columns=["normal"])
    assert len(fig.axes[0].patches) == 0, "una continua no se dibuja con barras"


def test_heatmap_sin_grilla_visible(df):
    fig = plots.correlation_heatmap(df)
    ax = fig.axes[0]
    assert not any(line.get_visible() for line in ax.get_ygridlines())


def test_heatmap_no_deja_filas_ni_columnas_vacias(df):
    """El recorte y la máscara deben coincidir: nada de bandas en blanco."""
    fig = plots.correlation_heatmap(df, annot=True)
    ax = fig.axes[0]
    n_filas = len(ax.get_yticklabels())
    # la primera fila debe traer exactamente un valor visible
    valores_primera_fila = [t for t in ax.texts if t.get_position()[1] < 1.0]
    assert valores_primera_fila, "la primera fila quedó vacía: máscara desalineada"
    assert n_filas >= 2
