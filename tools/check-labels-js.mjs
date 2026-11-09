#!/usr/bin/env node
// Verifica la grammatica di pyspendless/static/js/ps-labels.js contro le stesse
// fixture usate dal lato Python (pyspendless/test/fixtures/labels_cases.json).
// Task26-0, metro della Fase 4.
//
//     node tools/check-labels-js.mjs        # exit 0 se tutti i casi passano
//
// Node e' uno strumento LOCALE, come tools/tailwindcss: il progetto non ne
// dipende, sul server non c'e', e nulla nel repo lo richiede a runtime. Serve
// a non dover aprire un browser per sapere se il parser JS e' allineato a
// quello Python. La parte di UI (Tom Select, chip, sincronizzazione con la
// textarea) non e' verificabile qui: quella sta in tools/probe-labels.html.
//
// Perche' funziona senza DOM: ps-labels.js deve poter essere CARICATO in un
// ambiente senza `window` e senza `document` — all'import non tocca il DOM e
// non assume TomSelect. E' lo stesso vincolo che gli serve in produzione per
// degradare quando il CDN non risponde.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const CASES = join(ROOT, 'pyspendless/test/fixtures/labels_cases.json');
const SCRIPT = join(ROOT, 'pyspendless/static/js/ps-labels.js');

let passed = 0, failed = 0;
const failures = [];

function group(name, fails, total) {
  if (fails.length === 0) {
    passed++;
    console.log(`  OK   ${name} (${total}/${total} casi)`);
    return;
  }
  failed++;
  failures.push(name);
  console.log(`  FAIL ${name} (${fails.length}/${total} casi falliti)`);
  fails.slice(0, 5).forEach((f) => console.log(`         - ${f}`));
  if (fails.length > 5) console.log(`         ... e altri ${fails.length - 5}`);
}

function die(message, detail) {
  console.log(`  FAIL ${message}`);
  if (detail) console.log(`         ${detail}`);
  console.log(`\n${'-'.repeat(68)}\n0 gruppi superati, 1 fallito`);
  process.exit(1);
}

const cases = JSON.parse(readFileSync(CASES, 'utf8'));

let source;
try {
  source = readFileSync(SCRIPT, 'utf8');
} catch (err) {
  die('Fase 4 non ancora implementata: pyspendless/static/js/ps-labels.js', String(err));
}

// Finto ambiente browser: solo `window`, niente `document`. Se il file tocca
// il DOM al caricamento, qui si vede subito — ed e' un difetto, non un limite
// di questo harness.
const sandbox = { window: {} };
sandbox.window.window = sandbox.window;
try {
  new Function('window', 'globalThis', source + '\n;return window.PsLabels;');
} catch (err) {
  die('ps-labels.js non e\' sintatticamente valido', String(err));
}
let L;
try {
  L = new Function('window', source + '\n;return window.PsLabels;')(sandbox.window);
} catch (err) {
  die('ps-labels.js solleva al caricamento in un ambiente senza DOM', String(err));
}
if (!L) die('ps-labels.js non definisce window.PsLabels');

const required = ['isValid', 'extract', 'extractNorm', 'hasLabel', 'addLabel',
                  'removeLabel', 'renameLabel', 'canonicalize', 'normalizeSpace'];
const absent = required.filter((fn) => typeof L[fn] !== 'function');
if (absent.length) die('PsLabels non espone le funzioni del contratto', `mancano: ${absent.join(', ')}`);

const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

function run(name, fn, argsOf) {
  const fails = [];
  for (const c of cases[name]) {
    let got;
    try { got = fn.apply(null, argsOf(c)); }
    catch (err) { fails.push(`${JSON.stringify(c)} -> eccezione ${err}`); continue; }
    const want = c.expected;
    const ok = typeof want === 'boolean' ? Boolean(got) === want : eq(got, want);
    if (!ok) fails.push(`${JSON.stringify(c)} -> ottenuto ${JSON.stringify(got)}`);
  }
  group(`PsLabels.${name}`, fails, cases[name].length);
}

console.log('== Fase 4 — ps-labels.js, grammatica (fixture condivise col lato Python) ==');
run('is_valid',        L.isValid,        (c) => [c.name]);
run('extract',         L.extract,        (c) => [c.note]);
run('extract_norm',    L.extractNorm,    (c) => [c.note]);
run('has_label',       L.hasLabel,       (c) => [c.note, c.label]);
run('add_label',       L.addLabel,       (c) => [c.note, c.label]);
run('remove_label',    L.removeLabel,    (c) => [c.note, c.label]);
run('rename_label',    L.renameLabel,    (c) => [c.note, c.old, c.new]);
run('canonicalize',    L.canonicalize,   (c) => [c.note, c.mapping]);
run('normalize_space', L.normalizeSpace, (c) => [c.text]);

if (source.includes('(?<')) {
  failed++; failures.push('lookbehind');
  console.log('  FAIL ps-labels.js usa un lookbehind nelle regex (Safari < 16.4 non lo supporta)');
} else {
  passed++;
  console.log('  OK   nessun lookbehind nelle regex');
}

console.log(`\n${'-'.repeat(68)}\n${passed} gruppi superati, ${failed} falliti`);
if (failures.length) {
  console.log('\nFalliti:');
  failures.forEach((f) => console.log(`  - ${f}`));
}
process.exit(failed === 0 ? 0 : 1);
