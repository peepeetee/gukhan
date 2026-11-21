// SPDX-License-Identifier: Apache-2.0
// Playwright from the environment (CI, a global install) or from the local check directory.
let playwright;
try { playwright = require('playwright'); } catch { playwright = require('../build/browser-check/node_modules/playwright'); }
const {chromium} = playwright;
const path = require('node:path');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
const {copyWithHosts, siteMessage} = require('./smoke-helpers.cjs');
(async () => {
  const fixture = path.resolve('build/browser-fixture');
  fs.mkdirSync(fixture, {recursive:true});
  const lexicon = '연구\t研究\n전기\t電氣\n전기\t傳記\n공학\t工學\n희귀\t\u{30000}\u{30001}\n';  // the last two are CJK Extension G: no ordinary font has them
  fs.writeFileSync(path.join(fixture,'lexicon.tsv'), lexicon);
  fs.writeFileSync(path.join(fixture,'manifest.json'), JSON.stringify({notice:'Hand-written test fixture',outputs:{lexicon:{sha256:crypto.createHash('sha256').update(lexicon).digest('hex')}}}));
  // GUKHAN_EXT: an unpacked store build. Tested through a copy that declares the hosts as granted (see smoke-helpers).
  const extension = copyWithHosts(path.resolve(process.env.GUKHAN_EXT || 'extension'), path.resolve('build/browser-ext'));
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
    await worker.evaluate(() => chrome.storage.local.set({enabled:true}));
    const page = await context.newPage();
    await page.route('http://fixture.test/**', r => r.fulfill({contentType:'text/html',body:'<meta charset="utf-8"><p id="text">전기 연구</p><p id="more">연구가 전기 공학이</p><p id="tick"></p><script>var n=0;setInterval(function(){document.getElementById("tick").textContent="초 "+(++n)},400);window.flashes=0;new MutationObserver(function(){var t=document.getElementById("text").textContent;if(t==="전기 연구"&&window.converted)window.flashes++;if(t.indexOf("研究")>=0)window.converted=true}).observe(document.getElementById("text"),{childList:true,subtree:true,characterData:true})</script><pre>전기 연구</pre><kbd>전기 연구</kbd><samp>전기 연구</samp><div role="textbox">전기 연구</div><input value="전기 연구">'}));
    await page.goto('http://fixture.test/');
    // Nothing is injected until the site is turned on: no script is registered and the page is untouched.
    await page.waitForTimeout(800);
    assert.equal(await page.locator('[data-gukhan]').count(), 0, 'a site that is off was converted');
    assert.equal(await options.evaluate(async () => (await chrome.scripting.getRegisteredContentScripts()).length), 0);
    // Turning the site on, as the popup does after the reader allows it, reaches the page that is already open.
    assert.deepEqual(await options.evaluate(siteMessage('fixture.test', true)), {ok: true});
    assert.deepEqual(await options.evaluate(async () => (await chrome.scripting.getRegisteredContentScripts()).map(s => s.matches[0])), ['*://fixture.test/*']);
    await page.locator('[data-gukhan="word"]').first().waitFor();
    // A page that keeps changing elsewhere (the ticker) must not make converted words flash back to Hangul.
    await page.waitForTimeout(2500);
    assert.equal(await page.evaluate(() => window.flashes), 0);
    for (const tag of ['pre', 'kbd', 'samp', '[role=textbox]']) assert.equal(await page.locator(tag).textContent(), '전기 연구', tag);
    // The popover is unintrusive: hover previews it without taking focus or moving the page;
    // Escape closes it; Enter opens it from the keyboard and Escape returns focus to the word.
    const word = page.locator('[data-gukhan="word"]').first(), panel = page.locator('[data-gukhan="panel"]');
    const layout = () => page.evaluate(() => `${document.documentElement.scrollHeight}:${JSON.stringify(document.querySelector('#more').getBoundingClientRect())}`);
    const before = await layout();
    await word.hover();
    await panel.waitFor({state: 'attached'});
    assert.equal(await layout(), before);
    assert.equal(await page.evaluate(() => document.activeElement === document.body || document.activeElement.dataset.gukhan !== 'panel'), true);
    await page.keyboard.press('Escape');
    await panel.waitFor({state: 'detached'});
    await page.mouse.move(0, 0);
    // A script on the page can dispatch events but not trusted ones: forged input neither opens the card
    // nor saves a choice (a saved choice applies on every site).
    await page.evaluate(() => {
      const w = document.querySelector('[data-gukhan="word"]');
      w.click(); w.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}));
      w.dispatchEvent(new PointerEvent('pointerenter', {pointerType: 'mouse'}));
    });
    await page.waitForTimeout(600);
    assert.equal(await panel.count(), 0, 'forged events opened the card');
    await word.focus(); await page.keyboard.press('Enter');
    await panel.waitFor({state: 'attached'});
    assert.equal(await page.evaluate(() => document.activeElement.dataset.gukhan), 'panel');
    await page.evaluate(() => {
      for (const b of document.querySelector('[data-gukhan="panel"]').shadowRoot.querySelectorAll('button')) b.click();
    });
    await page.waitForTimeout(400);
    assert.deepEqual(await worker.evaluate(() => chrome.storage.local.get('overrides')), {}, 'a forged click saved a choice');
    await page.keyboard.press('Escape');
    await panel.waitFor({state: 'detached'});
    assert.equal(await page.evaluate(() => document.activeElement.dataset.gukhan), 'word');
    await word.click();
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
    await worker.evaluate(() => chrome.storage.local.set({enabled:true}));
    // Turning the site off unregisters its script; the next load is untouched.
    assert.deepEqual(await options.evaluate(siteMessage('fixture.test', false)), {ok: true});
    assert.equal(await options.evaluate(async () => (await chrome.scripting.getRegisteredContentScripts()).length), 0);
    assert.deepEqual(await worker.evaluate(() => chrome.storage.local.get('sites')), {sites: {}});
    await page.reload();
    await page.waitForTimeout(800);
    assert.equal(await page.locator('#text').textContent(),'전기 연구');
    assert.equal(await page.locator('[data-gukhan]').count(), 0);
    // A Hanja the page's font cannot draw is noticed: the popup is told and the candidate card says so.
    const glyph = await context.newPage();
    await glyph.route('http://glyph.test/**', r => r.fulfill({contentType: 'text/html', body: '<meta charset="utf-8"><p>희귀 연구</p>'}));
    await glyph.goto('http://glyph.test/');
    assert.deepEqual(await options.evaluate(siteMessage('glyph.test', true)), {ok: true});
    await glyph.locator('[data-gukhan="word"]').first().waitFor();
    await glyph.waitForFunction(() => document.querySelector('p').textContent.includes('\u{30000}'));
    const lacking = async () => worker.evaluate(async () => Object.entries(await chrome.storage.session.get(null)).filter(([k]) => k.startsWith('glyphs:')).map(([, v]) => v));
    for (let i = 0; i < 40 && !(await lacking()).length; i++) await glyph.waitForTimeout(100);
    const reported = await lacking();
    const pictures = reported.length ? '' : await glyph.evaluate(() => {  // what the page's own canvas draws, for the failure message
      const ctx = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
      const ink = ch => { ctx.clearRect(0, 0, 64, 64); ctx.font = '32px serif'; ctx.fillText(ch, 8, 44); return ctx.getImageData(0, 0, 64, 64).data.filter((v, i) => i % 4 === 3 && v).length + 'px'; };
      return ['H', '\u{30000}', '\u0378', '\u{2FFFD}', '\u{3FFFD}', '\uFFFF'].map(c => c.codePointAt(0).toString(16) + ':' + ink(c)).join(' ');
    });
    assert.ok(reported.length && reported[0].sample.includes('\u{30000}'), 'the missing Extension G character is reported; canvas ink: ' + pictures);
    await glyph.locator('[data-gukhan="word"]').first().click();
    await glyph.locator('[data-gukhan="panel"]').waitFor({state: 'attached'});
    assert.match(await glyph.evaluate(() => document.querySelector('[data-gukhan="panel"]').shadowRoot.textContent), /이 글꼴에 없는 글자/);
    // A large page converts lazily: only text near the viewport is converted, the rest when it scrolls into view.
    const big = await context.newPage();
    const paragraphs = Array.from({length: 3000}, (_, i) => `<p style="height:40px;margin:0">연구 ${i}</p>`).join('');
    await big.route('http://big.test/**', r => r.fulfill({contentType: 'text/html', body: `<meta charset="utf-8">${paragraphs}`}));
    await big.goto('http://big.test/');
    assert.deepEqual(await options.evaluate(siteMessage('big.test', true)), {ok: true});
    await big.waitForFunction(() => document.querySelectorAll('[data-gukhan="word"]').length > 0);
    await big.waitForTimeout(800);
    const near = await big.locator('[data-gukhan="word"]').count();
    assert.ok(near > 0 && near < 300, `only the text near the viewport is converted, got ${near} of 3000`);
    assert.equal(await big.evaluate(() => document.body.lastElementChild.textContent), '연구 2999', 'far text stays Hangul');
    await big.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await big.waitForFunction(() => document.body.lastElementChild.textContent === '研究 2999');
    // A cap on the nodes examined per page: the rest stays Hangul and the popup is told.
    await worker.evaluate(() => chrome.storage.local.set({limits: {total: 30, perPass: 10}}));
    const capped = await context.newPage();
    const spans = Array.from({length: 200}, () => '<span>연구 </span>').join('');
    await capped.route('http://capped.test/**', r => r.fulfill({contentType: 'text/html', body: `<meta charset="utf-8"><div style="font-size:4px">${spans}</div>`}));
    await capped.goto('http://capped.test/');
    assert.deepEqual(await options.evaluate(siteMessage('capped.test', true)), {ok: true});
    await capped.waitForFunction(() => document.querySelectorAll('[data-gukhan="word"]').length >= 30);
    await capped.waitForTimeout(1200);
    assert.equal(await capped.locator('[data-gukhan="word"]').count(), 30, 'the cap stops conversion at 30 nodes');
    assert.equal(await worker.evaluate(async () => Object.values(await chrome.storage.session.get(null)).includes(true)), true, 'the popup is told');
    await worker.evaluate(() => chrome.storage.local.remove('limits'));
    console.log('PASS: real dictionary import, candidates, saved override, protected text, toggle restore, site disable');
  } finally { await context.close(); }
})().catch(e => {console.error(e);process.exitCode=1});

