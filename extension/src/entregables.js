/** El árbol del panel lateral. */
const vscode = require("vscode");
const path = require("path");
const { describir } = require("./proyecto");

const ICONO = {
  academia: "mortar-board",
  negocio: "graph",
};

class Nodo extends vscode.TreeItem {
  constructor(etiqueta, colapso, opciones = {}) {
    super(etiqueta, colapso);
    Object.assign(this, opciones);
  }
}

class Entregables {
  constructor() {
    this._cambio = new vscode.EventEmitter();
    this.onDidChangeTreeData = this._cambio.event;
  }

  refrescar() {
    this._cambio.fire();
  }

  getTreeItem(nodo) {
    return nodo;
  }

  getChildren(padre) {
    const p = describir();
    if (!p.ok) {
      return [
        new Nodo(p.motivo, vscode.TreeItemCollapsibleState.None, {
          iconPath: new vscode.ThemeIcon("info"),
        }),
      ];
    }

    const audiencia = vscode.workspace.getConfiguration("sumakit").get("audiencia");

    if (!padre) {
      return [
        new Nodo(
          audiencia === "academia" ? "Academia · PDF con citas" : "Negocio · deck editable",
          vscode.TreeItemCollapsibleState.None,
          {
            description: "clic para cambiar",
            iconPath: new vscode.ThemeIcon(ICONO[audiencia]),
            command: { command: "sumakit.cambiarAudiencia", title: "Cambiar" },
            contextValue: "audiencia",
          }
        ),
        new Nodo(path.basename(p.taller), vscode.TreeItemCollapsibleState.Expanded, {
          iconPath: new vscode.ThemeIcon("folder-opened"),
          contextValue: "taller",
        }),
        new Nodo(`Figuras (${p.figuras.length})`, vscode.TreeItemCollapsibleState.Collapsed, {
          iconPath: new vscode.ThemeIcon("file-media"),
          contextValue: "figuras",
        }),
      ];
    }

    if (padre.contextValue === "taller") {
      const abrir = (etiqueta, ruta, icono) =>
        new Nodo(etiqueta, vscode.TreeItemCollapsibleState.None, {
          iconPath: new vscode.ThemeIcon(icono),
          resourceUri: vscode.Uri.file(ruta),
          command: {
            command: "vscode.open",
            title: "Abrir",
            arguments: [vscode.Uri.file(ruta)],
          },
        });
      return [
        abrir("academico.qmd", p.academico, "file-text"),
        abrir("negocio.py", p.negocio, "file-code"),
      ];
    }

    if (padre.contextValue === "figuras") {
      if (!p.figuras.length) {
        return [
          new Nodo("Sin figuras todavía", vscode.TreeItemCollapsibleState.None, {
            description: "se generan desde el notebook",
            iconPath: new vscode.ThemeIcon("circle-outline"),
          }),
        ];
      }
      return p.figuras.map(
        (f) =>
          new Nodo(f, vscode.TreeItemCollapsibleState.None, {
            iconPath: new vscode.ThemeIcon("file-media"),
            command: {
              command: "vscode.open",
              title: "Ver",
              arguments: [vscode.Uri.file(path.join(p.informe, "figuras", f))],
            },
          })
      );
    }

    return [];
  }
}

module.exports = { Entregables };
