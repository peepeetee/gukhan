// SPDX-License-Identifier: Apache-2.0
// A build with a bundled dictionary loads it on first install, with no file picking (headless Chromium).
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('../build/browser-check/node_modules/playwright'); }
const {chromium} = playwright;
const path = require('node:path');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {execFileSync} = require('node:child_process');
(async () => {
  const work = path.resolve('build/bundled-smoke'), dict = path.join(work, 'dict'), ext = path.join(work, 'ext');
  fs.rmSync(work, {recursive: true, force: true}); fs.mkdirSync(dict, {recursive: true});
  fs.writeFileSync(path.join(dict, 'lexicon.tsv'), '연구\t研究\t명사\tstdict:1\t조사하는 일\t0\t0\t0\n전기\t電氣\t명사\tstdict:2\t에너지\t0\t0\t0\n');
  fs.writeFileSync(path.join(dict, 'manifest.json'), JSON.stringify({licence: 'CC-BY-SA-2.0-KR', notice: 'Hand-written test fixture', outputs: {}}));
  const xpi = path.join(work, 'bundled.xpi');
  execFileSync('python3', ['scripts/package_extension.py', xpi, '--dictionary', dict, '--no-definitions'], {stdio: 'inherit'});
  fs.mkdirSync(ext); execFileSync('unzip', ['-q', xpi, '-d', ext]);
  assert.equal(fs.readFileSync(path.join(ext, 'dictionary/lexicon.tsv'), 'utf8').split('\n')[0], '연구\t研究\t\t\t\t0\t0\t0');
  const context = await chromium.launchPersistentContext(path.join(work, 'profile'), {
    channel: 'chromium', headless: true, args: [`--disable-extensions-except=${ext}`, `--load-extension=${ext}`]});
  try {
    const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker');
    const id = new URL(worker.url()).host;
    // First install opens the settings page by itself; the bundled dictionary loads there.
    let options;
    for (let i = 0; i < 50 && !options; i++) {
      options = context.pages().find(p => p.url() === `chrome-extension://${id}/options.html`);
      if (!options) await new Promise(r => setTimeout(r, 200));
    }
    assert.ok(options, 'first install should open the settings page');
    await options.locator('#status').filter({hasText: 'headwords imported'}).waitFor({timeout: 60000});
    await worker.evaluate(() => chrome.storage.local.set({enabled: true, sites: {'fixture.test': true}}));
    const page = await context.newPage();
    await page.route('http://fixture.test/**', r => r.fulfill({contentType: 'text/html', body: '<meta charset="utf-8"><p id="text">연구가 전기를</p>'}));
    await page.goto('http://fixture.test/');
    await page.waitForFunction(() => document.querySelector('#text').textContent === '研究가 電氣를');
    console.log('PASS: bundled dictionary loaded on first install, no definitions column, conversion works');
  } finally { await context.close(); }
})().catch(e => {console.error(e); process.exitCode = 1;});
