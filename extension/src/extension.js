/**
 * sumakit · Entregables
 *
 * La capa que le faltaba al IDE: el análisis ya vive aquí, y ahora el
 * entregable también. Un interruptor decide a quién le hablas —academia o
 * negocio— y los comandos llaman al motor de Python, que es donde vive todo
 * lo que ya estaba construido y probado.
 */
const vscode = require("vscode");
const path = require("path");
const { Entregables } = require("./entregables");
const { describir } = require("./proyecto");
const slides = require("./slides");

function ajustes() {
  return vscode.workspace.getConfiguration("sumakit");
}

function terminal() {
  const existente = vscode.window.terminals.find((t) => t.name === "sumakit");
  return existente || vscode.window.createTerminal("sumakit");
}

async function cambiarAudiencia() {
  const cfg = ajustes();
  const actual = cfg.get("audiencia");
  const nueva = actual === "academia" ? "negocio" : "academia";
  await cfg.update("audiencia", nueva, vscode.ConfigurationTarget.Workspace);
  vscode.window.setStatusBarMessage(
    nueva === "academia"
      ? "sumakit · construyendo para academia (PDF con citas)"
      : "sumakit · construyendo para negocio (deck editable)",
    4000
  );
}

function construir() {
  const p = describir();
  if (!p.ok) {
    vscode.window.showErrorMessage(p.motivo);
    return;
  }
  const audiencia = ajustes().get("audiencia");
  const python = ajustes().get("python") || "uv run";
  const t = terminal();
  t.show(true);

  if (audiencia === "academia") {
    t.sendText(
      `${python} sumakit render "${p.academico}" --salida "${p.entrega}"`
    );
  } else {
    t.sendText(`${python} python "${p.negocio}"`);
  }
}

function abrirTema() {
  const t = terminal();
  t.show(true);
  t.sendText(`${ajustes().get("python") || "uv run"} sumakit theme`);
}

function activate(contexto) {
  const arbol = new Entregables();
  contexto.subscriptions.push(
    vscode.window.registerTreeDataProvider("sumakit.entregables", arbol),
    vscode.commands.registerCommand("sumakit.cambiarAudiencia", async () => {
      await cambiarAudiencia();
      arbol.refrescar();
    }),
    vscode.commands.registerCommand("sumakit.construir", construir),
    vscode.commands.registerCommand("sumakit.abrirSlides", () => slides.abrir(contexto)),
    vscode.commands.registerCommand("sumakit.abrirTema", abrirTema),
    vscode.commands.registerCommand("sumakit.refrescar", () => arbol.refrescar()),
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("sumakit")) arbol.refrescar();
    })
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
