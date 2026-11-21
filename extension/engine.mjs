// SPDX-License-Identifier: Apache-2.0
export function parseLexicon(text) {
  const index = new Map();
  for (const line of text.replace(/^\uFEFF/, '').split(/\r?\n/)) {
    if (!line || line.startsWith('#')) continue;
    const [word, form, pos = '', source = '', sense = '', weight = '0', level = '0', rank = '0'] = line.split('\t');
    if (!word || !form || [...word].length !== [...form].length) throw new Error('Invalid lexicon / 사전 형식 오류');
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

// Particles and endings that may follow a noun. Without a morphology model the browser
// only strips these fixed strings; the stem must be a lexicon headword of two or more
// syllables and the remainder stays Hangul untouched. Anything else is left alone.
const PARTICLES = ['이', '가', '은', '는', '을', '를', '의', '에', '에서', '에게', '에는', '에도', '에서는', '에서도',
  '으로', '로', '으로서', '로서', '으로써', '로써', '으로는', '로는', '으로도', '로도', '와', '과', '도', '만', '까지', '부터',
  '마다', '조차', '처럼', '보다', '이나', '나', '이며', '며', '이다', '이고', '이라', '라', '이란', '란', '이라는', '라는',
  '에의', '으로의', '로의', '와의', '과의', '에서의', '들', '들이', '들은', '들을', '들의', '들도', '들에', '들과', '인', '이다',
  '하다', '한다', '했다', '하였다', '하는', '하고', '하여', '하며', '하면', '하게', '하기', '함', '합니다', '하지', '한', '할', '해', '해서',
  '되다', '된다', '되는', '되어', '되고', '됨', '되며', '된', '될', '됩니다'];
const SUFFIXES = new Set(PARTICLES);

// Stems of `word` for the particle fallback, longest first: [{stem, rest}].
function stems(word, index) {
  const out = [];
  for (let n = word.length - 1; n >= 2; n--) {
    if (SUFFIXES.has(word.slice(n)) && index.has(word.slice(0, n))) out.push({stem: word.slice(0, n), rest: word.slice(n)});
  }
  return out;
}

// No browser morphology model: whole words, fixed particles and phrases only.
// Never guesses: ambiguous words stay Hangul until the user chooses.
export function convert(text, index, overrides = {}) {
  const tokens = [...text.matchAll(/[가-힣]+/g)].map(m => ({word: m[0], start: m.index, end: m.index + m[0].length}));
  const phrases = phraseIndex(index, overrides);
  const result = [];
  for (let i = 0; i < tokens.length;) {
    const hit = matchPhrase(text, tokens, i, phrases, index, overrides) || matchWord(tokens[i], index, overrides);
    if (hit) { result.push(hit.decision); i += hit.tokens; } else i++;
  }
  return result;
}

// Phrase keys (a space inside) grouped by first word: {max, keys}. The lexicon's part is built
// once per index; the few phrase overrides are added per call.
function addPhrases(map, keys) {
  for (const k of keys) {
    const parts = k.split(' '), e = map.get(parts[0]) || {max: 0, keys: new Set()};
    e.max = Math.max(e.max, parts.length); e.keys.add(k); map.set(parts[0], e);
  }
  return map;
}
function phraseIndex(index, overrides) {
  if (!index.phraseMap) index.phraseMap = addPhrases(new Map(), [...index.keys()].filter(k => k.includes(' ')));
  const own = addPhrases(new Map(), Object.keys(overrides).filter(k => k.includes(' ')));
  return {get(first) {
    const a = index.phraseMap.get(first), b = own.get(first);
    return a && b ? {max: Math.max(a.max, b.max), keys: {has: k => a.keys.has(k) || b.keys.has(k)}} : a || b;
  }};
}

// Resolve one key: a saved choice wins, then a single unambiguous form; otherwise leave Hangul.
function resolve(key, index, overrides) {
  const own = Object.hasOwn(overrides, key);
  const candidates = index.get(key) || [];
  const forms = [...new Set(candidates.map(e => e.form))];
  if (own) return {candidates: overrides[key] === '-' || candidates.length ? candidates : [{form: overrides[key], sense: 'override'}],
    text: overrides[key] === '-' ? key : overrides[key]};
  if (!candidates.length) return;
  return {candidates, text: key.replace(/ /g, '').length > 1 && forms.length === 1 ? forms[0] : key};
}

function matchPhrase(text, tokens, i, phrases, index, overrides) {
  const entry = phrases.get(tokens[i].word);
  if (!entry) return;
  const run = [tokens[i]];  // tokens separated by exactly one space
  while (i + run.length < tokens.length && run.length < entry.max &&
         tokens[i + run.length].start - run[run.length - 1].end === 1 &&
         text[run[run.length - 1].end] === ' ') run.push(tokens[i + run.length]);
  for (let n = run.length; n >= 2; n--) {
    const head = run.slice(0, n - 1).map(t => t.word).join(' '), last = run[n - 1].word;
    const lasts = [last, ...stems(last, {has: k => entry.keys.has(`${head} ${k}`)}).map(s => s.stem)];
    for (const tail of lasts) {
      const key = `${head} ${tail}`, r = entry.keys.has(key) && resolve(key, index, overrides);
      if (r) return {tokens: n, decision: {start: run[0].start, end: run[n - 1].start + tail.length, word: key, ...r}};
    }
  }
}

function matchWord(token, index, overrides) {
  for (const key of [token.word, ...stems(token.word, {has: k => index.has(k) || Object.hasOwn(overrides, k)}).map(s => s.stem)]) {
    const r = resolve(key, index, overrides);
    if (r) return {tokens: 1, decision: {start: token.start, end: token.start + key.length, word: key, ...r}};
  }
}

// Keys a page's text can need from the dictionary: each word, its stems before a listed
// particle, and the phrase lists that start with a word (" 전기" -> phrase headwords).
export function neededKeys(texts) {
  const keys = new Set();
  for (const text of texts) for (const [word] of text.matchAll(/[가-힣]+/g)) {
    keys.add(word); keys.add(' ' + word);
    for (let n = 2; n < word.length; n++) if (SUFFIXES.has(word.slice(n))) keys.add(word.slice(0, n));
  }
  return keys;
}
