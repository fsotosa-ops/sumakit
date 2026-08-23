/**
 * Lee el proyecto abierto y descubre dónde están las piezas.
 *
 * La estructura que busca es la que siembra `sumakit report init`:
 * un taller con desarrollo/, informe/ y entrega/. Si no la encuentra, lo dice
 * en vez de fallar en silencio.
 */
const vscode = require("vscode");
const path = require("path");
const fs = require("fs");

function raiz() {
  const carpetas = vscode.workspace.workspaceFolders;
  return carpetas && carpetas.length ? carpetas[0].uri.fsPath : null;
}

/** Busca hacia abajo la primera carpeta `informe/` con un academico.qmd. */
function buscarInformes(base, profundidad = 5) {
  const encontrados = [];
  const recorrer = (dir, nivel) => {
    if (nivel > profundidad) return;
    let entradas;
    try {
      entradas = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const e of entradas) {
      if (!e.isDirectory()) continue;
      if ([".git", ".venv", "node_modules", "__pycache__", ".quarto"].includes(e.name)) continue;
      const completo = path.join(dir, e.name);
      if (e.name === "informe") {
        encontrados.push(completo);
        continue;
      }
      recorrer(completo, nivel + 1);
    }
  };
  recorrer(base, 0);
  return encontrados;
}

function describir() {
  const base = raiz();
  if (!base) return { ok: false, motivo: "No hay una carpeta abierta." };

  const informes = buscarInformes(base);
  if (!informes.length) {
    return {
      ok: false,
      base,
      motivo: "No encontré ninguna carpeta informe/. Créala con: sumakit report init",
    };
  }

  const informe = informes[0];
  const taller = path.dirname(informe);
  const figuras = path.join(informe, "figuras");
  return {
    ok: true,
    base,
    taller,
    informe,
    entrega: path.join(taller, "entrega"),
    academico: path.join(informe, "academico.qmd"),
    negocio: path.join(informe, "negocio.py"),
    figuras: fs.existsSync(figuras)
      ? fs.readdirSync(figuras).filter((f) => /\.(png|svg|jpg)$/i.test(f))
      : [],
    otrosInformes: informes.length - 1,
  };
}

module.exports = { describir, raiz };
