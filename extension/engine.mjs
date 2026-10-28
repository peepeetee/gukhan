// SPDX-License-Identifier: Apache-2.0
export function parseLexicon(text) {
  const index = new Map();
  for (const line of text.split(/\r?\n/)) {
    if (!line || line.startsWith('#')) continue;
    const [word, form, pos = '', source = '', sense = '', weight = '0', level = '0', rank = '0'] = line.split('\t');
    if (!word || !form || word.length !== form.length) throw new Error('Invalid lexicon / 사전 형식 오류');
    const numbers = [weight, level, rank].map(Number);
    if (!numbers.every(Number.isFinite)) throw new Error('Invalid ranking / 순위 오류');
    const entries = index.get(word) || [];
    entries.push({form, pos, source, sense, weight: numbers[0], level: numbers[1], rank: numbers[2]});
    index.set(word, entries);
  }
  for (const entries of index.values()) entries.sort((a, b) =>
    b.weight - a.weight || b.level - a.level || (a.rank || Infinity) - (b.rank || Infinity) ||
    (a.form < b.form ? -1 : a.form > b.form ? 1 : 0));
  return index;
}

// No browser morphology model: exact whole-word matches only. Never strip endings.
export function convert(text, index, overrides = {}) {
  const result = [];
  for (const match of text.matchAll(/[가-힣]+/g)) {
    const word = match[0], candidates = index.get(word);
    if (!candidates?.length) continue;
    const forms = [...new Set(candidates.map(e => e.form))];
    const chosen = Object.hasOwn(overrides, word) ? overrides[word] :
      word.length > 1 && forms.length === 1 ? forms[0] : word;
    result.push({start: match.index, end: match.index + word.length, word,
      text: chosen === '-' ? word : chosen, candidates});
  }
  return result;
}
