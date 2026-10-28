// SPDX-License-Identifier: Apache-2.0
import {parseLexicon} from './engine.mjs';
const status = document.querySelector('#status');
async function show() {
  const s = await chrome.storage.local.get(['notice', 'overrides']);
  document.querySelector('#notice').textContent = s.notice || '';
  document.querySelector('#overrides').value = Object.entries(s.overrides || {}).map(([w, h]) => `${w} = ${h}`).join('\n');
}
document.querySelector('#import').onclick = async () => {
  try {
    const files = [...document.querySelector('#files').files];
    const lex = files.find(f => f.name === 'lexicon.tsv'), manifest = files.find(f => f.name === 'manifest.json');
    if (!lex || !manifest) throw new Error('Select lexicon.tsv + manifest.json');
    const text = await lex.text(), metadata = JSON.parse(await manifest.text());
    const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', await lex.arrayBuffer()))]
      .map(x => x.toString(16).padStart(2, '0')).join('');
    if (digest !== metadata.outputs?.lexicon?.sha256 || typeof metadata.notice !== 'string') throw new Error('Manifest does not match dictionary');
    const entries = parseLexicon(text);
    if (!entries.size) throw new Error('Empty dictionary');
    await chrome.storage.local.set({lexicon: text, notice: metadata.notice});
    status.textContent = `${entries.size} 단어 / headwords imported`; await show();
  } catch (e) { status.textContent = String(e); }
};
document.querySelector('#save').onclick = async () => {
  try {
    const overrides = {};
    // Same syntax as the CLI override file: "word = 漢字", "#" starts a comment, a tab may replace "=".
    for (const raw of document.querySelector('#overrides').value.split('\n')) {
      const line = raw.split('#', 1)[0].trim();
      if (!line) continue;
      const m = line.match(/^([가-힣]+)\s*(?:=|\t)\s*([^=\s]+)$/u);
      if (!m || (m[2] !== '-' && (!/^[가-힣\p{Script=Han}]+$/u.test(m[2]) || m[1].length !== m[2].length))) throw new Error('Invalid override / 선택 형식 오류');
      overrides[m[1]] = m[2];
    }
    await chrome.storage.local.set({overrides}); status.textContent = '저장됨 / Saved';
  } catch (e) { status.textContent = String(e); }
};
show();
