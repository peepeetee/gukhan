// SPDX-License-Identifier: Apache-2.0
// Playwright from the environment (CI, a global install) or from the local check directory.
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('../build/browser-check/node_modules/playwright'); }
const {chromium} = playwright;
const path = require('node:path');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
(async () => {
  const fixture = path.resolve('build/browser-fixture');
  fs.mkdirSync(fixture, {recursive:true});
  const lexicon = '연구\t研究\n전기\t電氣\n전기\t傳記\n공학\t工學\n';
  fs.writeFileSync(path.join(fixture,'lexicon.tsv'), lexicon);
  fs.writeFileSync(path.join(fixture,'manifest.json'), JSON.stringify({notice:'Hand-written test fixture',outputs:{lexicon:{sha256:crypto.createHash('sha256').update(lexicon).digest('hex')}}}));
  const extension = path.resolve('extension');
  fs.rmSync(path.resolve('build/browser-profile'), {recursive: true, force: true}); // a stale profile keeps the previous extension copy
  const context = await chromium.launchPersistentContext(path.resolve('build/browser-profile'), {
    channel:'chromium', headless:true,
    args:[`--disable-extensions-except=${extension}`,`--load-extension=${extension}`]
  });
  try {
    const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker');
    const id = new URL(worker.url()).host;
    const options = await context.newPage();
    await options.goto(`chrome-extension://${id}/options.html`);
    await options.locator('#files').setInputFiles([path.join(fixture,'lexicon.tsv'),path.join(fixture,'manifest.json')]);
    await options.locator('#import').click();
    await options.locator('#status').filter({hasText:'headwords imported'}).waitFor({timeout:60000});
    await worker.evaluate(() => chrome.storage.local.set({enabled:true,sites:{'fixture.test':true}}));
    const page = await context.newPage();
    await page.route('http://fixture.test/**', r => r.fulfill({contentType:'text/html',body:'<meta charset="utf-8"><p id="text">전기 연구</p><p id="more">연구가 전기 공학이</p><pre>전기 연구</pre><input value="전기 연구">'}));
    await page.goto('http://fixture.test/');
    await page.locator('[data-gukhan="word"]').first().waitFor();
    assert.equal(await page.locator('pre').textContent(),'전기 연구');
    await page.locator('[data-gukhan="word"]').first().click();
    await page.locator('[data-gukhan="panel"]').waitFor({state: 'attached'}); // host has no box; the dialog lives in its shadow root
    await page.getByRole('button', {name: /^電氣/}).click();
    await page.waitForFunction(() => document.querySelector('#text').textContent.includes('電氣'));
    await page.reload();
    await page.waitForFunction(() => document.querySelector('#text').textContent.includes('電氣'));
    // A particle stays Hangul after the stem; the ambiguous 전기 stays Hangul until chosen.
    await page.waitForFunction(() => document.querySelector('#more').textContent === '研究가 電氣 工學이');
    // Settings UI persists an override, causing live re-render.
    await options.locator('#overrides').fill('전기 = 傳記'); await options.locator('#save').click();
    await page.waitForFunction(() => document.querySelector('#text').textContent.includes('傳記'));
    await options.locator('#overrides').fill('전기 = 傳記\n전기 공학 = 電氣 工學'); await options.locator('#save').click();
    await page.waitForFunction(() => document.querySelector('#more').textContent === '研究가 電氣 工學이');
    await options.locator('#overrides').fill('전기 = 傳記'); await options.locator('#save').click();
    await page.waitForFunction(() => document.querySelector('#more').textContent === '研究가 傳記 工學이');
    await worker.evaluate(() => chrome.storage.local.set({enabled:false}));
    await page.waitForFunction(() => document.querySelector('#text').textContent === '전기 연구' && !document.querySelector('[data-gukhan="word"]'));
    await worker.evaluate(() => chrome.storage.local.set({enabled:true,sites:{}}));
    await page.reload();
    assert.equal(await page.locator('#text').textContent(),'전기 연구');
    console.log('PASS: real dictionary import, candidates, saved override, protected text, toggle restore, site disable');
  } finally { await context.close(); }
})().catch(e => {console.error(e);process.exitCode=1});

