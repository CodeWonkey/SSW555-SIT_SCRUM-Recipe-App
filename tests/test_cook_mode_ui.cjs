const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const filename = path.join(__dirname, '../app/static/js/cook_mode.js');
const script = fs.readFileSync(filename, 'utf8');
const { commandFor } = require(filename);

test('next and previous voice commands are recognized', () => {
  assert.equal(commandFor('NEXT STEP'), 1);
  assert.equal(commandFor('next.'), 1);
  assert.equal(commandFor('Go back'), -1);
  assert.equal(commandFor('previous step'), -1);
});
test('noisy, ambiguous input does not change the step', () => {
  assert.equal(commandFor('oven is hot'), 0);
  assert.equal(commandFor('maybe the next thing'), 0);
  assert.equal(commandFor(''), 0);
});

function setup({ supported = true } = {}) {
  const events = {};
  const items = [0, 1, 2].map(() => ({ hidden: false }));
  const elements = Object.fromEntries([
    'cook-previous', 'cook-next', 'cook-counter', 'cook-listen', 'cook-stop', 'cook-status'
  ].map(id => [id, { disabled: false, textContent: '', addEventListener(name, callback) {
    events[`${id}:${name}`] = callback;
  } }]));
  const document = {
    hidden: false,
    getElementById(id) { return id === 'cook-mode' ? { querySelectorAll: () => items } : elements[id]; },
    addEventListener(name, callback) { events[`document:${name}`] = callback; }
  };
  let speech;
  class Recognition {
    constructor() { speech = this; }
    start() {}
    stop() { if (this.onend) this.onend(); }
  }
  const context = { document, window: supported ? { SpeechRecognition: Recognition } : {} };
  vm.runInNewContext(script, context, { filename });
  return { events, items, elements, document, speech: () => speech };
}

test('manual buttons work when speech recognition is unsupported', () => {
  const page = setup({ supported: false });
  assert.equal(page.elements['cook-listen'].disabled, true);
  page.events['cook-next:click']();
  assert.equal(page.elements['cook-counter'].textContent, 'Step 2 of 3');
  page.events['cook-previous:click']();
  assert.equal(page.elements['cook-counter'].textContent, 'Step 1 of 3');
});

test('voice navigation ignores noise and handles denied microphone', () => {
  const page = setup();
  page.events['cook-listen:click']();
  const speech = page.speech();
  speech.onresult({ resultIndex: 0, results: [{ isFinal: true, 0: { transcript: 'NEXT STEP' } }] });
  assert.equal(page.elements['cook-counter'].textContent, 'Step 2 of 3');
  speech.onresult({ resultIndex: 0, results: [{ isFinal: true, 0: { transcript: 'chop faster, please' } }] });
  assert.equal(page.elements['cook-counter'].textContent, 'Step 2 of 3');
  speech.onresult({ resultIndex: 0, results: [{ isFinal: true, 0: { transcript: 'previous step' } }] });
  assert.equal(page.elements['cook-counter'].textContent, 'Step 1 of 3');
  speech.onerror({ error: 'not-allowed' });
  assert.match(page.elements['cook-status'].textContent, /Microphone denied/);
  assert.equal(page.elements['cook-listen'].disabled, false);
});
