# sumakit

[![verificar](https://github.com/fsotosa-ops/sumakit/actions/workflows/verificar.yml/badge.svg)](https://github.com/fsotosa-ops/sumakit/actions/workflows/verificar.yml)

**El SDK de Suma Studio**, con las utilidades de EDA que lo rodean.

## Las capas se instalan por separado

El núcleo es el puente al proyecto y **solo necesita `pandas`**. Sirve igual en
una celda de Colab, en un script, en un DAG o en un contenedor: no guarda estado
de módulo ni arrastra librerías de dibujo.

```bash
pip install sumakit             # solo el SDK
pip install "sumakit[eda]"      # + perfilado, estadística y gráficos
pip install "sumakit[all]"      # todo
```

```python
from sumakit import studio

client = studio.StudioClient("sk_...")  # la clave que da la app
client.publish(alerts, "alertas")  # un DataFrame → una tabla del proyecto
```

`connect()` y `publish()` sueltas guardan un cliente por defecto y existen por
compatibilidad con los notebooks que ya las usan; **la API es el cliente**.

| Extra | Qué trae | Módulos |
|---|---|---|
| — | el SDK | `studio` |
| `eda` | numpy, matplotlib, seaborn | `profile`, `stats`, `plots`, `exploration`, `nb`, `theme`, `color` |
| `interactive` | altair | `interactive` |
| `extract` | dlt | `destinations` — Studio como destino de una carga |
| `report` | jinja2, python-pptx, pillow | `deck`, `report` |
| `ml` | scikit-learn | sugerencias de modelado |
| `ui` | streamlit | el configurador de tema |

## El EDA

```python
from sumakit import nb, profile, stats, plots

nb.setup(seed=42)

profile.overview(df)  # tipos, nulos, únicos, ceros, constantes
stats.distribution_report(df)  # asimetría, outliers y escalador sugerido
stats.high_correlation_pairs(df)  # colinealidad, sin entrecerrar los ojos

fig = plots.correlation_heatmap(df)  # devuelve Figure
fig.savefig("correlaciones.svg")  # sirve en notebook, informe y lámina
```

## Tres reglas

1. **Los gráficos devuelven `Figure`; ninguno llama a `plt.show()`.** La misma
   función sirve en el notebook, en el PDF y en un test.
2. **Nada muta estado global.** El tema se aplica una vez, o por bloque con
   `theme.using(...)`.
3. **Ninguna función trae paleta propia.** Todo sale del tema activo.

## Re-skinear por cliente

```python
from sumakit import theme
marca = theme.Palette(name="cliente", categorical=(...), ...)
theme.use(marca)
```

La paleta por defecto está validada para daltonismo y contraste. Las formas que
comparan todos los pares a la vez (scatter, pairplot) admiten un máximo de 3
series: pasado ese límite `theme.categorical()` levanta un error en vez de
generar colores indistinguibles.

## Instalación

```bash
pip install git+https://github.com/<usuario>/sumakit.git      # también en Colab
pip install "sumakit[ml] @ git+https://github.com/<usuario>/sumakit.git"
```

`[ml]` agrega scikit-learn, que habilita la información mutua en
`stats.target_report`.
