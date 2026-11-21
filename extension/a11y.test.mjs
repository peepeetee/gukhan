// SPDX-License-Identifier: Apache-2.0
// Colour contrast of the popup, settings page (ui.css) and the candidate card (content.js), light and dark.
// WCAG 2.x: 4.5:1 for text, 3:1 for the focus ring and other interface parts.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const lum = hex => {
  const c = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255).map(v => v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
};
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
const css = readFileSync(new URL('./ui.css', import.meta.url), 'utf8');
const content = readFileSync(new URL('./content.js', import.meta.url), 'utf8');

function variables(block) {
  return Object.fromEntries([...block.matchAll(/--([\w-]+):\s*(#[0-9a-f]{6})/gi)].map(m => [m[1], m[2]]));
}
const light = variables(css.match(/:root\s*\{([^}]*)\}/)[1]);
const dark = variables(css.match(/prefers-color-scheme: dark\)\s*\{\s*:root\s*\{([^}]*)\}/)[1]);

for (const [name, v] of [['light', light], ['dark', dark]]) {
  test(`popup and settings contrast, ${name}`, () => {
    assert.ok(ratio(v.fg, v.bg) >= 4.5, 'text on page');
    assert.ok(ratio(v['on-accent'], v.accent) >= 4.5, 'button label');
    assert.ok(ratio(v.accent, v.bg) >= 3, 'focus ring on page');
    assert.ok(ratio(v.fg, v.accent) >= 3 || ratio(v.accent, v.bg) >= 3, 'focus ring on a button');
    assert.ok(ratio(v.line, v.bg) >= 3, 'control border');
  });
}

test('candidate card contrast, light and dark', () => {
  const pair = key => { const m = content.match(new RegExp(`${key} = night \\? '(#[0-9a-f]{6})' : '(#[0-9a-f]{6})'`, 'i')); assert.ok(m, key); return {dark: m[1], light: m[2]}; };
  const [fg, bg, hover, accent, line] = ['fg', 'bg', 'hover', 'accent', 'line'].map(pair);
  for (const mode of ['light', 'dark']) {
    assert.ok(ratio(fg[mode], bg[mode]) >= 4.5, `${mode} text`);
    assert.ok(ratio(fg[mode], hover[mode]) >= 4.5, `${mode} text on hovered candidate`);
    assert.ok(ratio(accent[mode], bg[mode]) >= 4.5, `${mode} secondary text`);
    assert.ok(ratio(accent[mode], hover[mode]) >= 3, `${mode} focus ring on hovered candidate`);
    assert.ok(ratio(line[mode], bg[mode]) >= 1.3, `${mode} card edge is a separator, not information`);
  }
});

test('every control of the pages has an accessible name', () => {
  for (const file of ['popup.html', 'options.html']) {
    const html = readFileSync(new URL(`./${file}`, import.meta.url), 'utf8');
    assert.match(html, /<html lang="ko">/, file);
    assert.match(html, /name="viewport"/, `${file} scales on a phone`);
    for (const tag of html.match(/<(input|textarea|select)\b[^>]*>/g) || []) {
      const id = tag.match(/id="([^"]+)"/)?.[1];
      const labelled = /aria-label=/.test(tag) || (id && (new RegExp(`for="${id}"`).test(html) ||
        new RegExp(`<label[^>]*>(?:(?!</label>)[\\s\\S])*${tag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`).test(html)));
      assert.ok(labelled, `${file}: ${tag}`);
    }
  }
});

test('the manifest declares Firefox for Android and needs a version that knows the data-collection key', () => {
  const manifest = JSON.parse(readFileSync(new URL('./manifest.json', import.meta.url), 'utf8')), gecko = manifest.browser_specific_settings.gecko;
  assert.ok(parseInt(manifest.browser_specific_settings.gecko_android.strict_min_version) >= parseInt(gecko.strict_min_version));
  assert.deepEqual(gecko.data_collection_permissions.required, ['none']);
});
