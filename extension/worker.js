// SPDX-License-Identifier: Apache-2.0
import {convert, neededKeys} from './engine.mjs';
import {readKeys} from './lexstore.js';

// A small index with just the headwords (and phrase lists) the given texts can need.
async function pageIndex(texts) {
  const found = await readKeys(neededKeys(texts));
  const phraseKeys = [...found].filter(([k]) => k.startsWith(' ')).flatMap(([, list]) => list);
  for (const [k, v] of await readKeys(phraseKeys)) found.set(k, v);
  const index = new Map();
  for (const [k, v] of found) if (!k.startsWith(' ')) index.set(k, v);
  return index;
}
async function convertMessage(message, sender) {
  if (!sender.tab || !Array.isArray(message.texts)) return {};
  const site = new URL(sender.url).hostname;
  const settings = await chrome.storage.local.get(['enabled', 'sites', 'overrides']);
  if (!settings.enabled || !settings.sites?.[site]) return {disabled: true};
  if (message.texts.length > 100 || message.texts.some(t => typeof t !== 'string' || t.length > 20000)) {
    throw new Error('한 번에 보낸 글이 너무 큽니다 / Page batch too large');
  }
  const index = await pageIndex(message.texts);
  return {results: message.texts.map(t => convert(t, index, settings.overrides || {}))};
}
// One listener: a second one would race the first for the reply.
chrome.runtime.onMessage.addListener((message, sender, reply) => {
  if (sender.id !== chrome.runtime.id) return;
  let task;
  if (message?.type === 'convert') task = convertMessage(message, sender);
  else if (message?.type === 'site') {
    // Only the extension's own pages (popup, settings) may change sites, never a content script on a web page.
    task = sender.url?.startsWith(chrome.runtime.getURL('')) ? siteMessage(message) : Promise.reject(new Error('refused'));
  } else if (message?.type === 'capped' && sender.tab) {
    // a page too large to convert whole: the popup tells the reader (per tab, forgotten when the browser closes)
    task = chrome.storage.session.set({[`capped:${sender.tab.id}`]: message.capped === true}).then(() => ({}));
  } else if (message?.type === 'glyphs' && sender.tab && Number.isInteger(message.count)) {
    // characters the page's font cannot draw, for the popup to mention (per tab, forgotten when the browser closes)
    const sample = Array.isArray(message.sample) ? message.sample.slice(0, 8).map(c => String(c).slice(0, 2)) : [];
    task = chrome.storage.session.set({[`glyphs:${sender.tab.id}`]: {count: message.count, sample}}).then(() => ({}));
  } else task = Promise.resolve({});
  task.then(reply, e => { console.error(e); reply({error: String(e?.message || e)}); });
  return true;
});
// --- Per-site access. The extension asks for no site at install: the popup asks the browser for one
// host at a time (permissions.request needs the reader's click), and this worker then registers the
// content script for that host only. Turning a site off unregisters the script and gives the
// permission back. "sites" in storage lists the hosts that are on.
const scriptId = host => `gukhan-site:${host}`;
const matchOf = host => `*://${host}/*`;  // for the content script
// Permissions use both schemes spelled out: Chromium's permissions.contains() says no to a `*://` pattern even when it is granted.
const originsOf = host => [`http://${host}/*`, `https://${host}/*`];
const validHost = host => typeof host === 'string' && /^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$/.test(host) && host.length <= 253;

async function registeredIds() {
  return new Set((await chrome.scripting.getRegisteredContentScripts()).map(s => s.id));
}
async function setSite(host, on) {
  const {sites = {}} = await chrome.storage.local.get('sites');
  if (on) sites[host] = true; else delete sites[host];
  await chrome.storage.local.set({sites});
}
async function enableSite(host, tabId) {
  if (!validHost(host)) throw new Error('이 주소는 지원하지 않습니다 / Unsupported address');
  if (!await chrome.permissions.contains({origins: originsOf(host)})) {
    throw new Error('사이트 접근이 허용되지 않았습니다 / Site access was not granted');
  }
  if (!(await registeredIds()).has(scriptId(host))) {
    await chrome.scripting.registerContentScripts([{id: scriptId(host), matches: [matchOf(host)], js: ['content.js'], runAt: 'document_idle', persistAcrossSessions: true}]);
  }
  await setSite(host, true);
  // The page that is already open does not get a registered script until its next load.
  if (Number.isInteger(tabId)) {
    try { await chrome.scripting.executeScript({target: {tabId}, files: ['content.js']}); } catch (e) { console.warn(e); }
  }
}
async function disableSite(host) {
  if (!validHost(host)) throw new Error('이 주소는 지원하지 않습니다 / Unsupported address');
  await setSite(host, false);  // open pages restore their Hangul when the setting changes
  if ((await registeredIds()).has(scriptId(host))) await chrome.scripting.unregisterContentScripts({ids: [scriptId(host)]});
  await chrome.permissions.remove({origins: originsOf(host)}).catch(() => {});
}
// After an install, update or restart: the sites that are on keep their script, a site whose permission
// the reader revoked in the browser's own settings is turned off, and no script is left for a site that is off.
async function reconcile() {
  const {sites = {}} = await chrome.storage.local.get('sites');
  const ids = await registeredIds();
  for (const host of Object.keys(sites)) {
    if (!sites[host]) continue;
    if (!validHost(host) || !await chrome.permissions.contains({origins: originsOf(host)})) { await setSite(host, false); continue; }
    if (!ids.has(scriptId(host))) {
      await chrome.scripting.registerContentScripts([{id: scriptId(host), matches: [matchOf(host)], js: ['content.js'], runAt: 'document_idle', persistAcrossSessions: true}]);
    }
  }
  for (const id of ids) if (id.startsWith('gukhan-site:') && !sites[id.slice('gukhan-site:'.length)]) await chrome.scripting.unregisterContentScripts({ids: [id]});
}
async function siteMessage({host, on, tabId}) {
  if (on) await enableSite(host, tabId); else await disableSite(host);
  return {ok: true};
}
chrome.runtime.onStartup.addListener(() => reconcile().catch(console.error));

// First install: open settings, where a bundled dictionary (if this build has one) is loaded.
chrome.runtime.onInstalled.addListener(({reason}) => {
  reconcile().catch(console.error);
  if (reason === 'install') chrome.runtime.openOptionsPage();
});
