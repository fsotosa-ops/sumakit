/** Doble mínimo de la API de VS Code, para probar la lógica pura fuera del editor. */
class ThemeIcon { constructor(id) { this.id = id; } }
class EventEmitter { constructor(){ this.event = () => {}; } fire(){} }
class TreeItem {
  constructor(label, collapsibleState) { this.label = label; this.collapsibleState = collapsibleState; }
}
module.exports = {
  ThemeIcon, EventEmitter, TreeItem,
  TreeItemCollapsibleState: { None: 0, Collapsed: 1, Expanded: 2 },
  ViewColumn: { Beside: -2 },
  ConfigurationTarget: { Workspace: 2 },
  Uri: { file: (p) => ({ fsPath: p, scheme: "file" }) },
  window: {
    showWarningMessage: () => {}, showErrorMessage: () => {},
    createWebviewPanel: () => ({ webview: {} }),
    terminals: [], createTerminal: () => ({ show(){}, sendText(){} }),
    setStatusBarMessage: () => {}, registerTreeDataProvider: () => ({}),
  },
  workspace: {
    workspaceFolders: null,
    getConfiguration: () => ({ get: (k) => module.exports.__ajustes[k], update: async () => {} }),
    onDidChangeConfiguration: () => ({}),
  },
  commands: { registerCommand: () => ({}) },
  __ajustes: { audiencia: "negocio", slidesUrl: "", python: "uv run" },
};
