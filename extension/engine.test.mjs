// SPDX-License-Identifier: Apache-2.0
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseLexicon, convert} from './engine.mjs';
const lex = parseLexicon('연구\t研究\n전기\t傳記\t명사\tt\tstory\t10\t0\t0\n전기\t電氣\t명사\tt\tpower\t10\t3\t10\n안\t案\n안\t안');
test('exact words; endings and ambiguous words preserved', () => {
  assert.deepEqual(convert('연구 전기는 전기 안', lex).map(x => x.text), ['研究', '전기', '안']);
  assert.equal(convert('전기', lex)[0].candidates[0].form, '電氣');
});
test('saved choices and keep overrides', () => {
  assert.equal(convert('전기', lex, {전기:'傳記'})[0].text, '傳記');
  assert.equal(convert('연구', lex, {연구:'-'})[0].text, '연구');
});
test('malformed data rejected', () => assert.throws(() => parseLexicon('연구\t研')));
