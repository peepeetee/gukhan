// SPDX-License-Identifier: Apache-2.0
// Real Firefox run through Selenium (Apache-2.0) + geckodriver. Playwright's Firefox cannot load extensions.
const path = require('node:path');
const fs = require('node:fs');
const http = require('node:http');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const local = '../build/firefox-check/node_modules/';
const load = name => { try { return require(name); } catch { return require(local + name); } };
const {Builder, By, until} = load('selenium-webdriver');
const firefox = load('selenium-webdriver/firefox');
(async () => {
  const manifest = JSON.parse(fs.readFileSync('extension/manifest.json', 'utf8'));
  const geckoId = manifest.browser_specific_settings.gecko.id, uuid = crypto.randomUUID();
  const fixture = path.resolve('build/firefox-fixture');
  fs.mkdirSync(fixture, {recursive: true});
  const lexicon = '연구\t研究\n전기\t電氣\n전기\t傳記\n';
  fs.writeFileSync(path.join(fixture, 'lexicon.tsv'), lexicon);
  fs.writeFileSync(path.join(fixture, 'manifest.json'), JSON.stringify({notice: 'Hand-written test fixture',
    outputs: {lexicon: {sha256: crypto.createHash('sha256').update(lexicon).digest('hex')}}}));
  const zip = path.resolve('build/gukhan-firefox.zip');
  fs.rmSync(zip, {force: true});
  execFileSync('zip', ['-r', '-q', zip, '.'], {cwd: 'extension', stdio: 'inherit'});
  const server = http.createServer((q, r) => { r.setHeader('content-type', 'text/html; charset=utf-8');
    r.end('<p id="text">전기 연구</p><pre>전기 연구</pre><input value="전기 연구">'); }).listen(0, '127.0.0.1');
  const base = `http://127.0.0.1:${server.address().port}/`;
  const opts = new firefox.Options().addArguments('-headless')
    .setPreference('extensions.webextensions.uuids', JSON.stringify({[geckoId]: uuid}));
  const driver = await new Builder().forBrowser('firefox').setFirefoxOptions(opts).build();
  const text = async () => driver.findElement(By.css('#text')).getText();
  try {
    await driver.installAddon(zip, true);
    await driver.get(`moz-extension://${uuid}/options.html`);
    await driver.findElement(By.css('#files')).sendKeys(
      [path.join(fixture, 'lexicon.tsv'), path.join(fixture, 'manifest.json')].join('\n'));
    await driver.findElement(By.css('#import')).click();
    await driver.wait(until.elementTextContains(driver.findElement(By.css('#status')), 'headwords imported'), 30000);
    await driver.executeAsyncScript(`const done = arguments[arguments.length - 1];
      browser.storage.local.set({enabled: true, sites: {'127.0.0.1': true}}).then(() => done())`);
    await driver.get(base);
    await driver.wait(until.elementLocated(By.css('[data-gukhan="word"]')), 30000);
    assert.equal(await driver.findElement(By.css('pre')).getText(), '전기 연구');
    await driver.findElement(By.css('[data-gukhan="word"]')).click();
    const panelText = await driver.executeScript(`return document.querySelector('[data-gukhan="panel"]').shadowRoot.textContent`);
    assert.match(panelText, /電氣/);
    await driver.executeScript(`[...document.querySelector('[data-gukhan="panel"]').shadowRoot.querySelectorAll('button')]
      .find(b => b.textContent.startsWith('電氣')).click()`);
    await driver.wait(async () => (await text()).includes('電氣'), 30000);
    await driver.navigate().refresh();
    await driver.wait(async () => (await text()).includes('電氣'), 30000);
    console.log('PASS: Firefox install, dictionary import, candidates, saved override, protected text');
  } finally { await driver.quit(); server.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
