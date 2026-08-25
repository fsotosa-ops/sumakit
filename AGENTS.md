# sumakit

**Utilidades para talleres de ciencia de datos y machine learning.** El ciclo de
un taller: perfilar, diagnosticar, modelar —eso último lo hace scikit-learn— y
salir con un informe y una presentación.

## El código habla inglés; las personas leen español

**Identificadores en inglés. Docstrings y comentarios en español neutral.**

La regla no es estética: este paquete tenía `luminancia` conviviendo con
`concentration_table`, y **la mezcla es el defecto, no el idioma**. Es lo mismo
que `suma-scout` ya tenía escrito —*«mezclar los dos es peor que cualquiera de
los dos consistente»*— y que `suma-studio` fijó en su `ADR-0007`.

- **Inglés**: módulos, funciones, clases, parámetros, atributos, variables.
- **Español**: docstrings, comentarios, mensajes de error que lee una persona.

## Diagnostica; no transforma ni ajusta

**Ninguna función de este paquete devuelve datos transformados ni un modelo
ajustado.** Recibe un DataFrame o unas etiquetas, y devuelve una tabla o una
figura.

Hay dos razones y las dos importan:

- **Técnica**: un transformador ajustado hay que reusarlo sobre test. Ese
  contrato es de scikit-learn (`Pipeline`, `ColumnTransformer`) y competir con
  él produce un artefacto peor que el estándar.
- **Académica**: esto se usa en talleres donde lo evaluado es que sepas aplicar
  el método. Si `KMeans(n_clusters=k, random_state=42)` queda escondido dentro
  de una función de sumakit, el profesor no puede ver lo que vino a ver. La
  llamada al método tiene que estar en la celda.

Corolario para funciones nuevas de modelado: reciben `labels` o modelos ya
entrenados; el bucle que los entrena vive en el notebook. `cluster` es el
primero que sigue esa forma —`k_report(X, models)`, `segments(df, labels)`— y
`evaluate` deberá seguirla igual.

## Dos contratos, y son lo que sostiene el entregable

- **Perfilado y diagnóstico devuelven `DataFrame`**, no texto ni HTML. Por eso
  `profile.styled` y `profile.as_markdown` sirven sobre cualquiera de ellas sin
  saber de dónde vienen.
- **Lo que dibuja devuelve `Figure`, y nunca llama a `plt.show()`.** Lo fija
  `tests/test_render_contract.py`, que comprueba que las figuras lleguen al PDF
  y al PowerPoint.

Una función nueva que rompa cualquiera de los dos rompe el camino al entregable,
que es la mitad del valor del paquete.

## Versionar no es opcional

`pip install` de una versión que no cambió responde *"Requirement already
satisfied"* y no hace nada. Con la versión clavada en `0.1.0` durante 27
commits, un Colab quedó con un `profile` sin `as_markdown` y el error apareció
como `AttributeError`, no como "tienes una versión vieja".

- **Todo cambio en la superficie pública sube la versión menor**, incluido
  *agregar* una función. Agregar también rompe a quien tiene la versión vieja.
- La versión vive **solo** en `pyproject.toml`. `__init__.py` la deriva con
  `importlib.metadata`. Escribirla dos veces es cómo se desincronizan.

## El núcleo hace el taller completo

El EDA y el entregable son dependencias del núcleo, no extras. La regla anterior
—«solo pandas, porque un contenedor que publica tablas no necesita
matplotlib»— venía de suma-studio, que está en stand-by. Hoy esto corre en un
notebook y en Colab, y los dos quieren dibujar.

Detrás de extras queda solo `ml` (scikit-learn) e `interactive` (altair). Los
extras `eda` y `report` se conservan **vacíos**, porque hay notebooks con
`pip install "sumakit[eda]"` escrito dentro.

La carga perezosa de `__init__.py` (PEP 562) **se queda**, pero por otro motivo:
ya no es para poder instalar sin extras, es para que `import sumakit` no cueste
el arranque de matplotlib y seaborn cuando solo vas a mirar una tabla. El CI lo
comprueba.

## Verificar

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest -q -m "not lento"
```

`ruff format` corre también sobre los bloques de Python del `README.md`.

`-m "not lento"` excluye las cuatro pruebas que renderizan con Quarto de verdad:
necesitan Quarto instalado **y** el paquete visible desde el kernel que Quarto
levanta, que no es el del entorno virtual. Fallan por ambiente, no por código.

**mypy es gradual a propósito.** `disallow_untyped_defs` solo en `studio` y
`theme`. Poner el repo entero en estricto de golpe produce un `# type: ignore`
por línea, que es peor que no tener tipos. Los módulos se suman de a uno.

## suma-studio, en stand-by

`studio.py` y `destinations.py` son el puente a la app
(`~/Desktop/projects/suma-studio`). El código se conserva y sus pruebas siguen
corriendo, pero el paquete no va por ahí hoy.

Dos consecuencias de que esté en stand-by:

- **El `ADR-0009` no aplica aquí.** Mandaba retirar `deck` y `report` de este
  paquete porque el render sería de Studio. Sin Studio, el render es de sumakit
  y `deck` es ciudadano de primera.
- `lib/color/index.ts` en la app es un puerto de `sumakit.color` sostenido por
  `fixture-del-motor.json`. Mientras exista se mantiene, pero no se amplía.
