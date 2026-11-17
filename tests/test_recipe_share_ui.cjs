const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { runInNewContext } = require("node:vm");
const source = readFileSync(require("node:path").join(__dirname, "../app/static/js/recipe_share.js"), "utf8");

function setup(navigator = {}) {
  const callbacks = {};
  const elements = {
    "share-text": { value: "Soup\nServings: 2", focus() { this.focused = true; }, select() { this.selected = true; } },
    "share-copy": { hidden: true, addEventListener: (_, callback) => callbacks.copy = callback },
    "share-native": { hidden: true, dataset: { title: "Soup" }, addEventListener: (_, callback) => callbacks.share = callback },
    "share-status": { textContent: "" },
  };
  runInNewContext(source, { navigator, document: { getElementById: id => elements[id] } });
  return { elements, callbacks };
}

test("unsupported sharing keeps copy available with manual fallback", async () => {
  const { elements, callbacks } = setup();
  assert.equal(elements["share-native"].hidden, true);
  assert.equal(elements["share-copy"].hidden, false);
  await callbacks.copy();
  assert.equal(elements["share-text"].selected, true);
  assert.equal(elements["share-text"].focused, true);
  assert.match(elements["share-status"].textContent, /Copy unavailable/);
});

test("copy writes the entire recipe and confirms success", async () => {
  let copied;
  const { elements, callbacks } = setup({ clipboard: { writeText: async text => copied = text } });
  await callbacks.copy();
  assert.equal(copied, elements["share-text"].value);
  assert.match(elements["share-status"].textContent, /Recipe copied/);
});

test("denied clipboard access selects recipe for manual copying", async () => {
  const { elements, callbacks } = setup({ clipboard: { writeText: async () => { throw new Error("Denied"); } } });
  await callbacks.copy();
  assert.equal(elements["share-text"].selected, true);
  assert.match(elements["share-status"].textContent, /Copy unavailable/);
});

test("native sharing sends recipe text without a local URL", async () => {
  let payload;
  const { elements, callbacks } = setup({ share: async data => payload = data });
  assert.equal(elements["share-native"].hidden, false);
  await callbacks.share();
  assert.equal(payload.title, "Soup");
  assert.equal(payload.text, elements["share-text"].value);
  assert.equal(payload.url, undefined);
  assert.equal(elements["share-native"].disabled, false);
});

test("canceled and failed native shares keep alternatives available", async () => {
  for (const name of ["AbortError", "NotAllowedError"]) {
    const { elements, callbacks } = setup({ share: async () => { const error = new Error(); error.name = name; throw error; } });
    await callbacks.share();
    assert.match(elements["share-status"].textContent, name === "AbortError" ? /canceled/ : /unavailable/);
    assert.equal(elements["share-native"].disabled, false);
    assert.equal(elements["share-copy"].hidden, false);
  }
});
