const { test } = require("node:test");
const assert = require("node:assert");
const path = require("node:path");
const Module = require("node:module");

// Redirige `require("vscode")` al doble antes de cargar los módulos.
const originalResolve = Module._resolveFilename;
Module._resolveFilename = function (peticion, ...resto) {
  if (peticion === "vscode") return path.join(__dirname, "vscode.js");
  return originalResolve.call(this, peticion, ...resto);
};

const slides = require("../src/slides");
const { describir } = require("../src/proyecto");

test("acepta una URL de Slides y le quita el fragmento", () => {
  assert.strictEqual(
    slides.normalizar("https://docs.google.com/presentation/d/ABC/edit#slide=id.p1"),
    "https://docs.google.com/presentation/d/ABC/edit"
  );
});

test("rechaza cualquier otro dominio", () => {
  // Sin esto, un ajuste del workspace podría cargar una página arbitraria
  // dentro del editor.
  assert.strictEqual(slides.normalizar("https://evil.example.com/x"), null);
  assert.strictEqual(slides.normalizar("javascript:alert(1)"), null);
});

test("una URL vacía no rompe nada", () => {
  assert.strictEqual(slides.normalizar(""), null);
  assert.strictEqual(slides.normalizar(undefined), null);
});

test("la CSP solo permite marcos de docs.google.com", () => {
  const html = slides.pagina("https://docs.google.com/x", "abc123");
  assert.ok(html.includes("frame-src https://docs.google.com"));
  assert.ok(html.includes("default-src 'none'"));
});

test("sin URL muestra una explicación, no un marco vacío", () => {
  const html = slides.pagina(null, "abc123");
  assert.ok(!html.includes("<iframe"));
  assert.ok(html.includes("sumakit.slidesUrl"));
});

test("sin carpeta abierta lo dice en vez de fallar", () => {
  const p = describir();
  assert.strictEqual(p.ok, false);
  assert.match(p.motivo, /carpeta abierta/);
});
