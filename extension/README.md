# sumakit · Entregables

La capa que le faltaba al editor: el análisis ya vive aquí, y ahora el
entregable también.

Un interruptor decide a quién le hablas —**academia** o **negocio**— y los
comandos llaman al motor de Python. No reimplementa nada: `sumakit` ya genera
el PDF con citas, el deck editable, los gráficos con tema y la validación de
daltonismo.

## Qué hace

| | |
|---|---|
| **Panel Entregables** | el taller, sus dos informes y tus figuras locales |
| **Interruptor de audiencia** | un clic cambia qué se construye |
| **Construir** | `sumakit render` para el PDF, o el script del deck |
| **Deck en Slides** | embebe el editor de Google Slides dentro del IDE |
| **Configurar el tema** | abre el configurador con validación de color |

## Por qué Slides se embebe y Drive no

Se verificó antes de construirlo. Google **no** bloquea el framing del editor
de Slides —ni con `X-Frame-Options` ni con `frame-ancestors`—, así que el
editor completo carga en un panel y funciona con tu sesión. Drive responde
`X-Frame-Options: SAMEORIGIN` y no se puede embeber: por eso las figuras se
listan desde el disco, que además es más rápido.

## Instalar

```bash
cd extension && npx @vscode/vsce package
# luego: Extensiones → ··· → Install from VSIX
```

Corre igual en VS Code y en Positron.

## Pruebas

```bash
node --test test/pruebas.js
```
