// SPDX-License-Identifier: Apache-2.0
// Score the browser engine (extension/engine.mjs) on the regression sets.
//   node scripts/measure_extension.mjs build/lexicon/lexicon.tsv tests/regression/*.tsv
// A decision is a dictionary word the engine found in the Hangul text whose published form is all
// Hanja. It is "right" (engine wrote the published Hanja), "wrong" (wrote other Hanja) or "flagged"
// (left Hangul); "over" counts words the engine converted where the published text keeps Hangul. "in candidates" counts right plus every other decision whose candidate list holds
// the published Hanja. Nothing here changes what the engine writes.
import fs from 'node:fs';
import {parseLexicon, convert} from '../extension/engine.mjs';

const [lexPath, ...files] = process.argv.slice(2);
if (!lexPath || !files.length) { console.error('usage: measure_extension.mjs lexicon.tsv items.tsv...'); process.exit(2); }
const fold = s => s.replace(/强/g, '強').replace(/眞/g, '真').replace(/爲/g, '為').replace(/祕/g, '秘').replace(/兦/g, '亡');
const isHan = c => /\p{Script=Han}/u.test(c);
const lex = parseLexicon(fs.readFileSync(lexPath, 'utf8'));
const t = {items: 0, misaligned: 0, decisions: 0, right: 0, wrong: 0, flagged: 0, over: 0, inCandidates: 0, offeredAmongFlagged: 0, flaggedForms: 0, maxForms: 0, top1: 0, top3: 0};
for (const f of files) for (const line of fs.readFileSync(f, 'utf8').split('\n')) {
  if (!line || line.startsWith('#')) continue;
  const [, , hangul, raw] = line.split('\t'); if (!raw) continue;
  const mixed = fold(raw.replace(/ # CHECK.*$/, ''));
  if ([...mixed].length !== [...hangul].length) { t.misaligned++; continue; }
  t.items++;
  for (const d of convert(hangul, lex, {})) {
    const gold = mixed.slice(d.start, d.end).replace(/ /g, '');
    if (![...gold].every(isHan)) { if (d.text !== d.word) t.over++; continue; }  // published text keeps Hangul here
    t.decisions++;
    const got = fold(d.text).replace(/ /g, '');
    const order = [...new Set(d.candidates.map(c => fold(c.form).replace(/ /g, '')))], rank = order.indexOf(gold), offered = rank >= 0;
    if (d.text === d.word && offered) { t.top1 += rank === 0; t.top3 += rank < 3; }
    if (d.text !== d.word && got === gold) { t.right++; t.inCandidates++; }
    else {
      const forms = new Set(d.candidates.map(c => c.form)).size;
      if (d.text !== d.word) t.wrong++; else { t.flagged++; t.flaggedForms += forms; t.maxForms = Math.max(t.maxForms, forms); }
      if (offered) { t.inCandidates++; if (d.text === d.word) t.offeredAmongFlagged++; }
    }
  }
}
const pct = n => (100 * n / t.decisions).toFixed(1) + '%';
console.log(JSON.stringify(t));
console.log(`decisions=${t.decisions} right=${t.right} (${pct(t.right)}) wrong=${t.wrong} (${pct(t.wrong)}) flagged=${t.flagged} (${pct(t.flagged)}) over=${t.over}`);
console.log(`flagged words list ${(t.flaggedForms / t.flagged).toFixed(1)} candidates on average (max ${t.maxForms})`);
console.log(`among flagged words that offer it: published Hanja listed first ${t.top1}, within the first three ${t.top3} of ${t.offeredAmongFlagged}`);
console.log(`in_candidates=${t.inCandidates} (${pct(t.inCandidates)}); of the flagged, ${t.offeredAmongFlagged} offer the published Hanja`);
