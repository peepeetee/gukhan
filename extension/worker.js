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
chrome.runtime.onMessage.addListener((message, sender, reply) => {
  (async () => {
    if (message.type !== 'convert' || !sender.tab || !Array.isArray(message.texts)) return {};
    const site = new URL(sender.url).hostname;
    const settings = await chrome.storage.local.get(['enabled', 'sites', 'overrides']);
    if (!settings.enabled || !settings.sites?.[site]) return {disabled: true};
    if (message.texts.length > 100 || message.texts.some(t => typeof t !== 'string' || t.length > 20000)) {
      throw new Error('Page batch too large');
    }
    const index = await pageIndex(message.texts);
    return {results: message.texts.map(t => convert(t, index, settings.overrides || {}))};
  })().then(reply, e => { console.error(e); reply({error: String(e)}); });
  return true;
});
