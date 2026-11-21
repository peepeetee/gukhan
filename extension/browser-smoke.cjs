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
  // The character list (reading, English meaning) the candidate card shows; its hash is in the manifest, like the lexicon's.
  const charInfo = '# hanja\treadings\tmeaning\n電\t전\telectricity\n氣\t기\tair, gas; breath\n傳\t전,촌\tpass on; biography\n記\t기\trecord\n';
  fs.writeFileSync(path.join(fixture,'char-info.tsv'), charInfo);
  const sha = text => crypto.createHash('sha256').update(text).digest('hex');
  fs.writeFileSync(path.join(fixture,'manifest.json'), JSON.stringify({notice:'Hand-written test fixture',outputs:{lexicon:{sha256:sha(lexicon)},char_info:{sha256:sha(charInfo)}}}));
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
    await options.locator('#files').setInputFiles([path.join(fixture,'lexicon.tsv'),path.join(fixture,'manifest.json'),path.join(fixture,'char-info.tsv')]);
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
    // Accessibility: the word's name leads with the Hangul reading, it is read as Korean, shows a focus ring,
    // and the card marks the saved choice, has a status line and gives focus back on Tab.
    const access = await word.evaluate(w => ({label: w.getAttribute('aria-label'), lang: w.lang, role: w.getAttribute('role'),
      description: w.getAttribute('aria-description'), outline: getComputedStyle(w).outlineStyle, original: w.dataset.original, text: w.textContent}));
    assert.equal(access.role, 'button'); assert.equal(access.lang, 'ko'); assert.match(access.description, /후보/);
    assert.ok(access.label.startsWith(access.original), `the name starts with the Hangul reading: ${access.label}`);
    assert.notEqual(access.outline, 'none', 'a focused word shows a focus ring');
    await page.keyboard.press('Enter'); await panel.waitFor({state: 'attached'});
    const access2 = await page.evaluate(() => {
      const root = document.querySelector('[data-gukhan="panel"]').shadowRoot, buttons = [...root.querySelectorAll('button')];
      return {pressed: buttons.map(b => b.getAttribute('aria-pressed')), status: !!root.querySelector('[role=status]'),
        ring: getComputedStyle(root.activeElement).outlineStyle};
    });
    assert.ok(access2.pressed.every(v => v === 'true' || v === 'false') && access2.pressed.includes('false'), 'candidates report whether they are the saved choice');
    assert.ok(access2.status, 'the Hanja detail line is a status region'); assert.notEqual(access2.ring, 'none', 'the focused candidate shows a focus ring');
    await page.keyboard.press('Tab'); await panel.waitFor({state: 'detached'});
    assert.equal(await page.evaluate(() => document.activeElement.dataset.gukhan !== 'panel'), true);
    await word.focus();
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
    // Output styles: the reader's choice applies live to every converted word. (The override above makes 전기 = 傳記.)
    assert.deepEqual(await options.evaluate(siteMessage('fixture.test', true)), {ok: true});
    const more = () => page.evaluate(() => document.querySelector('#more').textContent);
    await page.waitForFunction(() => document.querySelector('#more').textContent === '研究가 傳記 工學이');
    const style = async (value, expected) => {
      await worker.evaluate(v => chrome.storage.local.set({style: v}), value);
      await page.waitForFunction(e => document.querySelector('#more').textContent === e, expected);
    };
    await style('gloss', '연구(研究)가 전기(傳記) 공학(工學)이');
    await style('hanja-gloss', '研究(연구)가 傳記(전기) 工學(공학)이');
    await style('ruby', '研(연)究(구)가 傳(전)記(기) 工(공)學(학)이');  // <rp> brackets show where ruby is not supported
    assert.deepEqual(await page.evaluate(() => [...document.querySelectorAll('#more ruby rt')].map(x => x.textContent)), ['연', '구', '전', '기', '공', '학']);
    assert.equal(await page.locator('#more [data-gukhan="word"]').first().evaluate(w => w.dataset.original), '연구', 'a styled word is still the word the card is about');
    await style('mixed', '研究가 傳記 工學이');
    assert.equal(await page.locator('#more ruby').count(), 0, 'going back to mixed leaves no ruby');
    // The card shows each Hanja's reading and meaning from the imported character list.
    await page.locator('#more [data-gukhan="word"]').nth(1).click();
    await panel.waitFor({state: 'attached'});
    const card = () => page.evaluate(() => document.querySelector('[data-gukhan="panel"]').shadowRoot.textContent);
    for (let i = 0; i < 40 && !(await card()).includes('傳 전/촌 · pass on; biography'); i++) await page.waitForTimeout(100);
    assert.match(await card(), /傳 전\/촌 · pass on; biography/);
    await page.getByRole('button', {name: /^電氣/}).hover();
    assert.match(await card(), /電 전 · electricity/);
    assert.match(await card(), /氣 기 · air, gas; breath/);
    await page.keyboard.press('Escape'); await panel.waitFor({state: 'detached'});
    await worker.evaluate(() => chrome.storage.local.set({enabled:false}));
    await page.waitForFunction(() => !document.querySelector('[data-gukhan="word"]'));
    await worker.evaluate(() => chrome.storage.local.set({enabled:true}));
    assert.deepEqual(await options.evaluate(siteMessage('fixture.test', false)), {ok: true});
    // A Hanja the page's font cannot draw is noticed: the popup is told and the candidate card says so.
    const glyph = await context.newPage();
    await glyph.route('http://glyph.test/**', r => r.fulfill({contentType: 'text/html', body: '<meta charset="utf-8"><p>희귀 연구</p>'}));
    await glyph.goto('http://glyph.test/');
    assert.deepEqual(await options.evaluate(siteMessage('glyph.test', true)), {ok: true});
    await glyph.locator('[data-gukhan="word"]').first().waitFor();
    await glyph.waitForFunction(() => document.querySelector('p').textContent.includes('\u{30000}'));
    const lacking = async () => worker.evaluate(async () => Object.entries(await chrome.storage.session.get(null)).filter(([k]) => k.startsWith('glyphs:')).map(([, v]) => v));
    // What does this browser draw for a character no font has? Nothing, or one box shared by all of them, are what the
    // check recognises. A box that carries the character's own code point (Firefox, and the CI runner's headless
    // Chromium, which draws one) differs per character; there the check must stay silent rather than guess.
    const pictures = await glyph.evaluate(() => {
      const ctx = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
      const ink = ch => { ctx.clearRect(0, 0, 64, 64); ctx.font = '32px serif'; ctx.fillText(ch, 8, 44); const a = ctx.getImageData(0, 0, 64, 64).data; let n = 0, h = 0; for (let i = 3; i < a.length; i += 4) if (a[i]) { n++; h = (h * 31 + i * a[i]) >>> 0; } return {n, h}; };
      const a = ink('\u{30000}'), b = ink('\u{30001}');
      return {detectable: a.n === 0 || (a.n === b.n && a.h === b.h), a, b};
    });
    if (pictures.detectable) {
      for (let i = 0; i < 40 && !(await lacking()).length; i++) await glyph.waitForTimeout(100);
      const reported = await lacking();
      assert.ok(reported.length && reported[0].sample.includes('\u{30000}'), 'the missing Extension G character is reported');
      await glyph.locator('[data-gukhan="word"]').first().click();
      await glyph.locator('[data-gukhan="panel"]').waitFor({state: 'attached'});
      assert.match(await glyph.evaluate(() => document.querySelector('[data-gukhan="panel"]').shadowRoot.textContent), /이 글꼴에 없는 글자/);
    } else {
      await glyph.waitForTimeout(1000);
      assert.equal((await lacking()).length, 0, 'a browser that draws a box per character gets no report (the check does not guess)');
      console.log('NOTE: this browser draws a per-character box for missing glyphs; the glyph check stays silent, as documented. ' + JSON.stringify(pictures));
    }
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

