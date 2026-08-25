# sumakit

[![verificar](https://github.com/fsotosa-ops/sumakit/actions/workflows/verificar.yml/badge.svg)](https://github.com/fsotosa-ops/sumakit/actions/workflows/verificar.yml)

**Utilidades para talleres de ciencia de datos y machine learning.** El ciclo
completo: perfilar los datos, diagnosticarlos, y salir con un informe y una
presentación que no parezcan generados por defecto.

## Instalación

```bash
pip install "sumakit @ git+https://github.com/fsotosa-ops/sumakit.git"
```

Sirve igual en Colab. **No hace falta pedir extras**: un `pip install sumakit`
a secas hace el taller completo, y el CI lo comprueba en un entorno donde solo
está el núcleo. Detrás de extras queda lo que de verdad es opcional:

| Extra | Qué habilita |
|---|---|
| `ml` | scikit-learn — información mutua en `stats.target_report` |
| `interactive` | altair — el módulo `interactive` |

## El EDA

```python
from sumakit import nb, profile, stats, plots

nb.setup(seed=42)

profile.alerts(df)  # qué revisar primero, ordenado por severidad
profile.overview(df)  # tipos, nulos, únicos, ceros, constantes
stats.distribution_report(df)  # asimetría, outliers y escalador sugerido
stats.high_correlation_pairs(df)  # colinealidad, sin entrecerrar los ojos

fig = plots.correlation_heatmap(df)
fig.savefig("correlaciones.svg")  # sirve en notebook, informe y lámina
```

`explore(df)` hace la primera pasada completa en una sola llamada, guiada por
las alertas: en vez de graficar las 26 columnas, grafica las que tienen algo
que decir.

## Dos contratos

Son lo que hace que una tabla del notebook llegue al PDF y a la lámina sin
volver a maquetarla:

- **Perfilado y diagnóstico devuelven `DataFrame`.** Por eso `profile.styled`
  (para el notebook) y `profile.as_markdown` (para que la tabla sobreviva al
  PDF sin salirse del margen) sirven sobre cualquiera de ellas.
- **Lo que dibuja devuelve `Figure`, y nunca llama a `plt.show()`.** La misma
  función sirve en el notebook, en Quarto, en el deck y en un test.

Y dos reglas más: **nada muta estado global** —el tema se aplica una vez, o por
bloque con `theme.using(...)`— y **ninguna función trae paleta propia**: todo
sale del tema activo.

## Diagnostica; no transforma ni ajusta

El preprocesamiento es de scikit-learn, porque un transformador ajustado hay que
reusarlo sobre test y ese contrato es suyo. El modelo lo ajustas tú, a la vista,
y sumakit describe el resultado. En un taller eso importa: lo que se evalúa es
que sepas aplicar el método, así que la llamada al método tiene que verse.

## El entregable

```python
from sumakit import deck
```

`deck` produce el `.pptx`: portada, agenda, hallazgos con título accionable
—`NonActionableTitleError` si el título no dice nada—, tablas y lámina de cifra.
Y `sumakit` como comando instala el formato académico de Quarto en cualquier
proyecto, con el preámbulo de LaTeX que hace que las tablas quepan.

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

## Suma Studio

`studio` y `destinations` son el puente a [Suma Studio](https://github.com/fsotosa-ops/suma-studio).
**Están en stand-by**: el código se conserva y las pruebas siguen corriendo, pero
no es por donde va el paquete hoy. `destinations` pide el extra `extract`.
