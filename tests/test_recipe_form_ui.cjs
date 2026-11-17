const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { runInNewContext } = require("node:vm");
const source = readFileSync(require("node:path").join(__dirname, "../app/static/js/recipe_form.js"), "utf8");

test("ingredient rows can be added and removed, but the last row remains", () => {
  const handlers = {};
  let rows = 1;
  let clones = 0;
  const fragment = {};
  const container = {
    addEventListener: (name, callback) => { handlers[name] = callback; },
    appendChild: node => { assert.equal(node, fragment); rows++; },
    contains: button => button === removeButton,
    querySelectorAll: () => Array(rows),
  };
  const removeButton = {
    closest: () => ({ remove: () => { rows--; } }),
  };
  const template = { content: { cloneNode: deep => {
    assert.equal(deep, true);
    clones++;
    return fragment;
  } } };
  const addButton = { addEventListener: (name, callback) => { handlers.add = callback; } };
  runInNewContext(source, { document: { getElementById: id => ({
    "ingredient-container": container,
    "ingredient-row-template": template,
    "add-ingredient": addButton,
  })[id] } });

  const remove = () => handlers.click({ target: { closest: () => removeButton } });
  remove();
  assert.equal(rows, 1);
  handlers.add();
  handlers.add();
  assert.equal(rows, 3);
  assert.equal(clones, 2);
  handlers.click({ target: { closest: () => null } });
  assert.equal(rows, 3);
  remove();
  remove();
  remove();
  assert.equal(rows, 1);
});

test("loading the script without an ingredient form is harmless", () => {
  assert.doesNotThrow(() => runInNewContext(source, {
    document: { getElementById: () => null },
  }));
});
