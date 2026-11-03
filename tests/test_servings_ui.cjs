const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { runInNewContext } = require("node:vm");
const source = readFileSync(require("node:path").join(__dirname, "../app/static/js/servings.js"), "utf8");

test("changing servings submits valid counts and blocks invalid counts", () => {
  let onChange;
  let valid = true;
  let submissions = 0;
  const input = {
    addEventListener(event, callback) {
      assert.equal(event, "change");
      onChange = callback;
    },
    reportValidity: () => valid,
  };
  const form = { requestSubmit: () => submissions++ };
  runInNewContext(source, {
    document: { getElementById: id => ({ servings: input, "servings-form": form })[id] },
  });
  onChange();
  assert.equal(submissions, 1);
  valid = false;
  onChange();
  assert.equal(submissions, 1);
  valid = true;
  onChange();
  assert.equal(submissions, 2);
});
