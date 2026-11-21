// SPDX-License-Identifier: Apache-2.0
import {parseLexicon} from './engine.mjs';
import {saveIndex} from './lexstore.js';
const status = document.querySelector('#status');
async function show() {
  const s = await chrome.storage.local.get(['notice', 'overrides']);
  document.querySelector('#notice').textContent = s.notice || '';
  document.querySelector('#overrides').value = Object.entries(s.overrides || {}).map(([w, h]) => `${w} = ${h}`).join('\n');
}
// Import a dictionary: the bytes of lexicon.tsv and the parsed manifest.json that describes them.
async function importDictionary(bytes, metadata) {
  const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2, '0')).join('');
  if (digest !== metadata.outputs?.lexicon?.sha256 || typeof metadata.notice !== 'string') throw new Error('manifest가 사전과 맞지 않습니다 / Manifest does not match dictionary');
  const entries = parseLexicon(new TextDecoder().decode(bytes));
  if (!entries.size) throw new Error('빈 사전입니다 / Empty dictionary');
  status.textContent = '저장 중… / Saving…';
  await saveIndex(entries);
  await chrome.storage.local.remove('lexicon');  // pre-IndexedDB copy
  await chrome.storage.local.set({lexiconInfo: {headwords: entries.size, sha256: digest}, notice: metadata.notice});
  status.textContent = `${entries.size} 단어 / headwords imported`; await show();
}
document.querySelector('#import').onclick = async () => {
  try {
    const files = [...document.querySelector('#files').files];
    const lex = files.find(f => f.name === 'lexicon.tsv'), manifest = files.find(f => f.name === 'manifest.json');
    if (!lex || !manifest) throw new Error('lexicon.tsv와 manifest.json을 고르세요 / Select lexicon.tsv + manifest.json');
    await importDictionary(await lex.arrayBuffer(), JSON.parse(await manifest.text()));
  } catch (e) { status.textContent = String(e); }
};
// A dictionary shipped inside the add-on (dictionary/lexicon.tsv + manifest.json) is loaded on
// first run, and again whenever the add-on ships a different one. Nothing is fetched from the web.
async function loadBundled() {
  let metadata;
  try {
    const response = await fetch('dictionary/manifest.json');
    if (!response.ok) return;
    metadata = await response.json();
  } catch { return; }  // no bundled dictionary in this build
  const {lexiconInfo} = await chrome.storage.local.get('lexiconInfo');
  if (lexiconInfo?.sha256 === metadata.outputs?.lexicon?.sha256) return;
  status.textContent = '내장 사전을 불러오는 중입니다 (1분쯤) / Loading the built-in dictionary (about a minute)…';
  await importDictionary(await (await fetch('dictionary/lexicon.tsv')).arrayBuffer(), metadata);
}
document.querySelector('#save').onclick = async () => {
  try {
    const overrides = {};
    // Same syntax as the CLI override file: "word = 漢字", "#" starts a comment, a tab may replace "=".
    for (const raw of document.querySelector('#overrides').value.split('\n')) {
      const line = raw.split('#', 1)[0].trim();
      if (!line) continue;
      const m = line.match(/^([가-힣]+(?: [가-힣]+)*)\s*(?:=|\t)\s*(\S+(?: \S+)*)$/u);
      // A phrase ("전기 공학 = 電氣 工學") keeps one space between words on both sides.
      const key = m?.[1], val = m?.[2];
      const ok = m && (val === '-' || (/^[가-힣\p{Script=Han}]+(?: [가-힣\p{Script=Han}]+)*$/u.test(val) &&
        key.split(' ').length === val.split(' ').length && [...key.replace(/ /g, '')].length === [...val.replace(/ /g, '')].length));
      if (!ok) throw new Error('Invalid override / 선택 형식 오류');
      overrides[key] = val;
    }
    await chrome.storage.local.set({overrides}); status.textContent = '저장됨 / Saved';
  } catch (e) { status.textContent = String(e); }
};
show();
loadBundled().catch(e => { status.textContent = String(e); });
