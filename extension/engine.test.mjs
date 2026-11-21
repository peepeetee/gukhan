// SPDX-License-Identifier: Apache-2.0
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseLexicon, convert} from './engine.mjs';
const lex = parseLexicon('연구\t研究\n전기\t傳記\t명사\tt\tstory\t10\t0\t0\n전기\t電氣\t명사\tt\tpower\t10\t3\t10\n안\t案\n안\t안');
test('exact words; endings and ambiguous words preserved', () => {
  assert.deepEqual(convert('연구 전기는 전기 안', lex).map(x => x.text), ['研究', '전기', '전기', '안']);
  assert.equal(convert('전기', lex)[0].candidates[0].form, '電氣');
});
test('particles and endings are stripped, left in Hangul, never guessed', () => {
  const l = parseLexicon('연구\t研究\n전기\t電氣\n공학\t工學\n전기\t傳記\n대통령\t大統領');
  const d = convert('연구가 대통령은 연구하는 연구들의 대통령에서', l);
  assert.deepEqual(d.map(x => x.text), ['研究', '大統領', '研究', '研究', '大統領']);
  assert.equal('연구가'.slice(d[0].end, 3), '가');
  assert.equal(convert('전기가', l)[0].text, '전기'); // ambiguous stem stays Hangul
  assert.equal(convert('연구자', l).length, 0);       // 자 is not a listed ending
  assert.equal(convert('연', parseLexicon('연\t年')).length, 1);
});
test('phrases from overrides and lexicon', () => {
  const l = parseLexicon('전기\t電氣\n전기\t傳記\n공학\t工學\n전기 공학\t電氣 工學');
  assert.deepEqual(convert('전기 공학이', l).map(x => [x.word, x.text, x.start, x.end]), [['전기 공학', '電氣 工學', 0, 5]]);
  assert.deepEqual(convert('전기, 공학', l).map(x => x.text), ['전기', '工學']); // comma blocks the phrase
  assert.equal(convert('전기 공학', l, {'전기 공학': '-'})[0].text, '전기 공학');
  assert.equal(convert('이 순신은', l, {'이 순신': '李 舜臣'}).length, 1);
  assert.equal(convert('이순신', l, {'이순신': '李舜臣'}).length, 1);
});
test('saved choices and keep overrides', () => {
  assert.equal(convert('전기', lex, {전기:'傳記'})[0].text, '傳記');
  assert.equal(convert('연구', lex, {연구:'-'})[0].text, '연구');
});
test('Hanja outside the BMP count as one character', () => {
  assert.equal(parseLexicon('간증\t䵟𪒟').get('간증')[0].form, '䵟𪒟');
});
test('a byte-order mark and Windows line endings do not spoil the first headword', () => {
  const l = parseLexicon('\uFEFF연구\t研究\r\n전기\t電氣\r\n');
  assert.deepEqual([...l.keys()], ['연구', '전기']);
});
test('malformed data rejected', () => assert.throws(() => parseLexicon('연구\t研')));
test('one manifest serves Chrome and Firefox', async () => {
  const {readFileSync} = await import('node:fs');
  const m = JSON.parse(readFileSync(new URL('./manifest.json', import.meta.url), 'utf8'));
  assert.equal(m.manifest_version, 3);
  assert.equal(m.background.service_worker, 'worker.js');
  assert.deepEqual(m.background.scripts, ['worker.js']);
  assert.match(m.browser_specific_settings.gecko.id, /@/);
  assert.deepEqual(m.browser_specific_settings.gecko.data_collection_permissions.required, ['none']);
});
