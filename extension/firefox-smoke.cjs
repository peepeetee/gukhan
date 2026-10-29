// SPDX-License-Identifier: Apache-2.0
// End-to-end check of the unpacked extension in a real Firefox, driven over Marionette.
// No dependencies: Node's built-in net and http, plus an installed Firefox (>= 128).
// Set FIREFOX_BIN to the executable if it is not in a default location.
const {spawn} = require('node:child_process');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const net = require('node:net');
const path = require('node:path');

const GECKO_ID = JSON.parse(fs.readFileSync(path.resolve('extension/manifest.json'), 'utf8')).browser_specific_settings.gecko.id;
const UUID = '3f8f1c9e-1d2a-4c55-9c7a-6b2f0a1d9e11';

function firefoxBinary() {
  const candidates = [process.env.FIREFOX_BIN, 'C:\\Program Files\\Mozilla Firefox\\firefox.exe',
    'C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe', '/usr/bin/firefox', '/snap/bin/firefox',
    '/Applications/Firefox.app/Contents/MacOS/firefox'];
  const found = candidates.find(c => c && fs.existsSync(c));
  if (!found) throw new Error('Firefox not found; set FIREFOX_BIN');
  return found;
}
const freePort = () => new Promise(res => { const s = net.createServer().listen(0, '127.0.0.1', () => { const {port} = s.address(); s.close(() => res(port)); }); });
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const fixtureDir = path.resolve('build/firefox-fixture');
  fs.mkdirSync(fixtureDir, {recursive: true});
  const lexicon = '연구\t研究\n전기\t電氣\n전기\t傳記\n';
  fs.writeFileSync(path.join(fixtureDir, 'lexicon.tsv'), lexicon);
  fs.writeFileSync(path.join(fixtureDir, 'manifest.json'), JSON.stringify({notice: 'Hand-written test fixture',
    outputs: {lexicon: {sha256: crypto.createHash('sha256').update(lexicon).digest('hex')}}}));

  const server = http.createServer((req, res) => {
    res.writeHead(200, {'content-type': 'text/html; charset=utf-8'});
    res.end('<meta charset="utf-8"><p id="text">전기 연구</p><pre>전기 연구</pre><input value="전기 연구">');
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const siteUrl = `http://127.0.0.1:${server.address().port}/`;
  const siteHost = '127.0.0.1';

  const profile = path.resolve('build/firefox-profile');
  fs.rmSync(profile, {recursive: true, force: true}); fs.mkdirSync(profile, {recursive: true});
  fs.writeFileSync(path.join(profile, 'user.js'), [
    `user_pref("extensions.webextensions.uuids", ${JSON.stringify(JSON.stringify({[GECKO_ID]: UUID}))});`,
    'user_pref("browser.shell.checkDefaultBrowser", false);', 'user_pref("datareporting.policy.dataSubmissionEnabled", false);',
    'user_pref("browser.startup.homepage_override.mstone", "ignore");'].join('\n'));

  const port = await freePort();
  fs.appendFileSync(path.join(profile, 'user.js'), `\nuser_pref("marionette.port", ${port});\n`);
  const firefox = spawn(firefoxBinary(), ['--headless', '--no-remote', '--marionette', '--profile', profile, 'about:blank'],
    {stdio: ['ignore', 'ignore', 'pipe'], env: {...process.env, MOZ_REMOTE_ALLOW_SYSTEM_ACCESS: '1'}});
  let stderr = ''; firefox.stderr.on('data', d => { stderr += d; });

  // Minimal Marionette client: frames are "<length>:<json>"; commands are [0, id, name, params].
  let sock, buffer = '', nextId = 1; const pending = new Map();
  function onData(chunk) {
    buffer += chunk.toString('utf8');
    for (;;) {
      const colon = buffer.indexOf(':'); if (colon < 0) return;
      const length = Number(buffer.slice(0, colon)); const bytes = Buffer.from(buffer.slice(colon + 1));
      if (bytes.length < length) return;
      const body = bytes.subarray(0, length).toString('utf8'); buffer = bytes.subarray(length).toString('utf8');
      const m = JSON.parse(body);
      if (Array.isArray(m) && m[0] === 1) { const p = pending.get(m[1]); if (p) { pending.delete(m[1]); m[2] ? p.reject(new Error(`${m[2].error}: ${m[2].message}`)) : p.resolve(m[3]); } }
    }
  }
  async function connect() {
    for (let i = 0; i < 100; i++) {
      try { sock = net.connect(port, '127.0.0.1'); await new Promise((ok, bad) => { sock.once('connect', ok); sock.once('error', bad); }); sock.on('data', onData); return; }
      catch { await sleep(300); }
    }
    throw new Error('Marionette did not come up\n' + stderr.slice(-2000));
  }
  const send = (name, params = {}) => new Promise((resolve, reject) => {
    const id = nextId++; pending.set(id, {resolve, reject});
    const body = JSON.stringify([0, id, name, params]); sock.write(`${Buffer.byteLength(body)}:${body}`);
  });
  // Scripts run in the page's own global (sandbox: null) so extension pages see their `chrome` object.
  const run = async script => (await send('WebDriver:ExecuteScript', {script: `return (${script});`, args: [], sandbox: null})).value;
  const runAsync = async script => (await send('WebDriver:ExecuteAsyncScript', {script: `const done = arguments[arguments.length - 1]; (${script}).then(() => done(true));`, args: [], sandbox: null})).value;
  async function until(expression, what, timeout = 30000) {
    const end = Date.now() + timeout; let last;
    while (Date.now() < end) { try { if (await run(expression) === true) return; } catch (e) { last = e; } await sleep(150); }
    throw new Error(`timeout waiting for ${what}${last ? ': ' + last.message : ''}`);
  }
  // Marionette refuses to navigate content to moz-extension:// URLs, so extension pages are opened as trusted tabs from the browser chrome.
  const tab = async url => {
    const known = new Set(await send('WebDriver:GetWindowHandles'));
    if (url.startsWith('moz-extension:')) {
      await send('Marionette:SetContext', {value: 'chrome'});
      await send('WebDriver:ExecuteScript', {script: 'const t = gBrowser.addTrustedTab(arguments[0]); gBrowser.selectedTab = t; return true;', args: [url], sandbox: 'system'});
      await send('Marionette:SetContext', {value: 'content'});
    } else {
      await send('WebDriver:NewWindow', {type: 'tab', focus: true});
    }
    let handle;
    for (let i = 0; i < 50 && !handle; i++) { handle = (await send('WebDriver:GetWindowHandles')).find(h => !known.has(h)); if (!handle) await sleep(100); }
    await send('WebDriver:SwitchToWindow', {handle, focus: true});
    if (!url.startsWith('moz-extension:')) await send('WebDriver:Navigate', {url});
    for (let i = 0; i < 100; i++) { if ((await run('document.readyState')) === 'complete') break; await sleep(100); }
    return handle;
  };
  const focus = handle => send('WebDriver:SwitchToWindow', {handle, focus: true});

  try {
    await connect();
    await new Promise(r => setTimeout(r, 500));
    await send('WebDriver:NewSession', {capabilities: {}});
    const added = await send('Addon:Install', {path: path.resolve('extension'), temporary: true});
    assert.equal(added.value, GECKO_ID);

    const options = await tab(`moz-extension://${UUID}/options.html`);
    const el = (await send('WebDriver:FindElement', {using: 'css selector', value: '#files'})).value;
    const elementId = Object.values(el)[0];
    await send('WebDriver:ElementSendKeys', {id: elementId, text: [path.join(fixtureDir, 'lexicon.tsv'), path.join(fixtureDir, 'manifest.json')].join('\n')});
    await run("document.querySelector('#import').click() || true");
    await until("document.querySelector('#status').textContent.includes('headwords imported')", 'dictionary import');
    await runAsync(`chrome.storage.local.set({enabled: true, sites: {'${siteHost}': true}})`);

    const page = await tab(siteUrl);
    await until("!!document.querySelector('[data-gukhan=\"word\"]')", 'underlined words');
    assert.equal(await run("document.querySelector('pre').textContent"), '전기 연구');
    assert.equal(await run("document.querySelector('input').value"), '전기 연구');
    await run("document.querySelector('[data-gukhan=\"word\"]').click() || true");
    await until("!!document.querySelector('[data-gukhan=\"panel\"]')", 'candidate panel');
    await run("[...document.querySelector('[data-gukhan=\"panel\"]').shadowRoot.querySelectorAll('button')].find(b => b.textContent.startsWith('電氣')).click() || true");
    await until("document.querySelector('#text').textContent.includes('電氣')", 'saved choice applied');
    await send('WebDriver:Refresh');
    await until("document.querySelector('#text').textContent.includes('電氣')", 'choice kept after reload');

    await focus(options);
    await run("(document.querySelector('#overrides').value = '전기 = 傳記', document.querySelector('#save').click(), true)");
    await focus(page);
    await until("document.querySelector('#text').textContent.includes('傳記')", 'override from settings');
    await focus(options); await runAsync('chrome.storage.local.set({enabled: false})'); await focus(page);
    await until("document.querySelector('#text').textContent === '전기 연구' && !document.querySelector('[data-gukhan=\"word\"]')", 'restore when disabled');
    await focus(options); await runAsync('chrome.storage.local.set({enabled: true, sites: {}})'); await focus(page);
    await send('WebDriver:Refresh'); await sleep(1500);
    assert.equal(await run("document.querySelector('#text').textContent"), '전기 연구');
    assert.equal(await run("!!document.querySelector('[data-gukhan=\"word\"]')"), false);
    await tab(`moz-extension://${UUID}/popup.html`);
    await until("document.querySelector('#status').textContent.length > 0", 'popup renders');
    console.log('PASS (Firefox): real dictionary import, candidates, saved override, protected text, toggle restore, site disable, popup renders');
  } finally {
    try { sock?.destroy(); } catch {}
    firefox.kill(); server.close();
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
