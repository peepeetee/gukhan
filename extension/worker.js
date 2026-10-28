// SPDX-License-Identifier: Apache-2.0
import {parseLexicon, convert} from './engine.mjs';
let cached;
async function lexicon() {
  if (!cached) cached = chrome.storage.local.get('lexicon').then(s => parseLexicon(s.lexicon || ''));
  return cached;
}
chrome.storage.onChanged.addListener(changes => { if (changes.lexicon) cached = undefined; });
chrome.runtime.onMessage.addListener((message, sender, reply) => {
  (async () => {
    if (message.type !== 'convert' || !sender.tab || !Array.isArray(message.texts)) return {};
    const site = new URL(sender.url).hostname;
    const settings = await chrome.storage.local.get(['enabled', 'sites', 'overrides']);
    if (!settings.enabled || !settings.sites?.[site]) return {disabled: true};
    if (message.texts.length > 100 || message.texts.some(t => typeof t !== 'string' || t.length > 20000)) {
      throw new Error('Page batch too large');
    }
    const index = await lexicon();
    return {results: message.texts.map(t => convert(t, index, settings.overrides || {}))};
  })().then(reply, e => reply({error: String(e)}));
  return true;
});
