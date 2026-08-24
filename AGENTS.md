# sumakit

**El SDK de Suma Studio.** El puente entre el notebook y el proyecto, más las
utilidades de EDA que hicieron falta para llegar hasta ahí.

La app (`~/Desktop/projects/suma-studio`) es el producto; esto es lo que le
habla desde fuera. Ver `ADR-0009` en ese repo.

## El código habla inglés; las personas leen español

**Identificadores en inglés. Docstrings y comentarios en español neutral.**

La regla no es estética: este paquete tenía `luminancia` conviviendo con
`concentration_table`, y **la mezcla es el defecto, no el idioma**. Es lo mismo
que `suma-scout` ya tenía escrito —*«mezclar los dos es peor que cualquiera de
los dos consistente»*— y que `suma-studio` fijó en su `ADR-0007`.

- **Inglés**: módulos, funciones, clases, parámetros, atributos, variables.
- **Español**: docstrings, comentarios, mensajes de error que lee una persona.

## Es un SDK, y eso obliga

**La API pública es un contrato con gente a la que no puedes llamar.** Hay
notebooks de Colab usando esto.

- Un nombre público que cambia **deja un alias con `DeprecationWarning`**.
  Romper un notebook en silencio es peor que la inconsistencia.
- La superficie que hay que mantener estable es **`studio.py`**. El toolkit de
  EDA —`profile`, `stats`, `plots`, `exploration`, `nb`— tiene menos
  compromiso.
- Lo que se publica a Studio son **tablas agregadas**, no el dataset crudo.

## Verificar

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest -q -m "not lento"
```

`-m "not lento"` excluye las cuatro pruebas que renderizan con Quarto de verdad:
necesitan Quarto instalado **y** el paquete visible desde el kernel que Quarto
levanta, que no es el del entorno virtual. Fallan por ambiente, no por código.

**mypy es gradual a propósito.** `disallow_untyped_defs` solo en `studio` y
`theme`. Poner el repo entero en estricto de golpe produce un `# type: ignore`
por línea, que es peor que no tener tipos. Los módulos se suman de a uno.

## Lo que no va aquí

**El render del entregable es de Studio** (`ADR-0009`). `lib/color/index.ts` en
la app es un puerto de `sumakit.color` sostenido por `fixture-del-motor.json`;
mientras exista se mantiene, pero **no se amplía la duplicación**: lo nuevo se
escribe una sola vez, del lado de Studio.
