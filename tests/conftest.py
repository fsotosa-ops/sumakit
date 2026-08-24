import matplotlib

matplotlib.use("Agg")  # sin backend gráfico: los tests no abren ventanas

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def df():
    """Dataset sintético con las patologías que un EDA debe detectar."""
    rng = np.random.default_rng(0)
    n = 300
    data = pd.DataFrame({
        "normal": rng.normal(10, 2, n),
        "sesgada": rng.exponential(2, n),          # asimetría alta -> robust
        "constante": np.ones(n),
        "con_nulos": rng.normal(0, 1, n),
        "categoria": rng.choice(["a", "b", "c"], n, p=[0.8, 0.15, 0.05]),
    })
    data.loc[:49, "con_nulos"] = np.nan            # bloque contiguo de nulos
    data["copia_normal"] = data["normal"] * 2 + 1  # colinealidad perfecta
    data["objetivo"] = data["normal"] * 0.5 + rng.normal(0, 0.5, n)
    return data


@pytest.fixture
def df_una_columna():
    """El caso que rompía kde_plot: una sola columna numérica."""
    return pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "cat": list("abcd")})


@pytest.fixture
def df_sin_numericas():
    """El otro caso que rompía: ninguna columna numérica."""
    return pd.DataFrame({"cat": list("abcd")})
