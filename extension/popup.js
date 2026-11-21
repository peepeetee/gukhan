// SPDX-License-Identifier: Apache-2.0
(async () => {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  const supported = /^https?:/.test(tab?.url || '');
  const host = supported ? new URL(tab.url).hostname : '';
  const settings = await chrome.storage.local.get(['enabled', 'sites', 'lexiconInfo', 'style']);
  document.querySelector('#host').textContent = host || '이 페이지는 지원하지 않습니다 / Unsupported page';
  const enabled = document.querySelector('#enabled'), site = document.querySelector('#site'), status = document.querySelector('#status');
  const usable = supported && /^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$/.test(host);  // an IP literal in brackets cannot be a match pattern
  const styleBox = document.querySelector('#style');
  styleBox.value = ['mixed', 'gloss', 'hanja-gloss', 'ruby'].includes(settings.style) ? settings.style : 'mixed';
  styleBox.onchange = () => chrome.storage.local.set({style: styleBox.value});  // pages redraw by themselves
  enabled.checked = !!settings.enabled;
  site.checked = !!settings.sites?.[host]; site.disabled = !usable;
  const idle = settings.lexiconInfo ? '로컬 처리 / Local processing' : '먼저 사전을 가져오세요 / Import a dictionary first';
  status.textContent = idle;
  enabled.onchange = () => chrome.storage.local.set({enabled: enabled.checked});
  // Nothing has access to any site until the reader turns one on here; the browser then asks about this
  // one site (the request must come straight from this click), and turning it off gives the access back.
  site.onchange = async () => {
    const on = site.checked; site.disabled = true;
    try {
      if (on && !await chrome.permissions.request({origins: [`http://${host}/*`, `https://${host}/*`]})) {
        throw new Error('허용하지 않아 바꾸지 않았습니다 / Not allowed, so nothing changed');
      }
      const answer = await chrome.runtime.sendMessage({type: 'site', host, on, tabId: tab.id});
      if (answer?.error) throw new Error(answer.error);
      if (on && !enabled.checked) { enabled.checked = true; await chrome.storage.local.set({enabled: true}); }
      status.textContent = on ? `${host} 에서 켰습니다 / On for ${host}` : `${host} 접근을 돌려주었습니다 / Access to ${host} given back`;
    } catch (e) {
      site.checked = !on; status.textContent = String(e.message || e);
    } finally { site.disabled = false; }
  };
  const lacking = tab ? (await chrome.storage.session.get(`glyphs:${tab.id}`))[`glyphs:${tab.id}`] : undefined;
  if (lacking?.count) {
    const note = document.querySelector('#glyphs'); note.hidden = false;
    note.textContent = `글꼴에 없는 漢字 ${lacking.count}자(${lacking.sample.join(' ')})는 네모로 보일 수 있습니다. Noto Serif/Sans CJK KR 같은 글꼴을 설치해 보세요. / ` +
      `${lacking.count} Hanja (${lacking.sample.join(' ')}) are missing from this page's font and may show as boxes; try a font such as Noto Serif or Noto Sans CJK KR.`;
  }
  const capped = tab ? (await chrome.storage.session.get(`capped:${tab.id}`))[`capped:${tab.id}`] : false;
  document.querySelector('#capped').hidden = !capped;
  document.querySelector('#options').onclick = () => chrome.runtime.openOptionsPage();
})();
