/**
 * Embebe el editor de Google Slides dentro del editor.
 *
 * Se verificó antes de construirlo: Google **no** bloquea el framing de
 * `/edit` —ni con X-Frame-Options ni con frame-ancestors—, así que el editor
 * completo carga dentro de un iframe y se puede usar con la sesión del
 * usuario. Drive, en cambio, responde `X-Frame-Options: SAMEORIGIN` y no se
 * puede embeber: por eso las figuras se listan desde el disco y Drive queda
 * solo como transporte.
 */
const vscode = require("vscode");

const DOMINIO = "https://docs.google.com";

function normalizar(url) {
  const limpia = (url || "").trim();
  if (!limpia) return null;
  if (!limpia.startsWith(DOMINIO)) return null;
  // /edit y /embed sirven; /edit trae el editor completo.
  return limpia.replace(/#.*$/, "");
}

function pagina(url, nonce) {
  return `<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta http-equiv="Content-Security-Policy"
      content="default-src 'none'; frame-src ${DOMINIO}; style-src 'nonce-${nonce}';">
<style nonce="${nonce}">
  html,body{height:100%;margin:0;background:var(--vscode-editor-background)}
  iframe{width:100%;height:100%;border:0;display:block}
  .vacio{
    font-family:var(--vscode-font-family); color:var(--vscode-descriptionForeground);
    padding:34px; max-width:46ch; line-height:1.6;
  }
  .vacio code{
    font-family:var(--vscode-editor-font-family);
    background:var(--vscode-textCodeBlock-background); padding:2px 5px; border-radius:3px;
  }
</style>
</head>
<body>
${
  url
    ? `<iframe src="${url}" allow="clipboard-read; clipboard-write"></iframe>`
    : `<div class="vacio">
        <p>No hay ninguna presentación configurada.</p>
        <p>Pega la URL de tu deck de Google Slides en el ajuste
        <code>sumakit.slidesUrl</code> y vuelve a abrir este panel.</p>
        <p>El editor carga aquí con tu sesión de Google: editas dentro del IDE,
        con las mismas herramientas de siempre.</p>
       </div>`
}
</body>
</html>`;
}

function abrir(contexto) {
  const cruda = vscode.workspace.getConfiguration("sumakit").get("slidesUrl");
  const url = normalizar(cruda);
  if (cruda && !url) {
    vscode.window.showWarningMessage(
      "sumakit.slidesUrl debe ser una URL de docs.google.com. Se ignoró por seguridad."
    );
  }

  const panel = vscode.window.createWebviewPanel(
    "sumakit.slides",
    "Deck · Google Slides",
    vscode.ViewColumn.Beside,
    { enableScripts: true, retainContextWhenHidden: true }
  );
  const nonce = Math.random().toString(36).slice(2, 14);
  panel.webview.html = pagina(url, nonce);
  return panel;
}

module.exports = { abrir, normalizar, pagina };
