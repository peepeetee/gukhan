// SPDX-License-Identifier: Apache-2.0
(async () => {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  const supported = /^https?:/.test(tab?.url || '');
  const host = supported ? new URL(tab.url).hostname : '';
  const settings = await chrome.storage.local.get(['enabled', 'sites', 'lexiconInfo']);
  document.querySelector('#host').textContent = host || '이 페이지는 지원하지 않습니다 / Unsupported page';
  const enabled = document.querySelector('#enabled'), site = document.querySelector('#site');
  enabled.checked = !!settings.enabled;
  site.checked = !!settings.sites?.[host]; site.disabled = !supported;
  document.querySelector('#status').textContent = settings.lexiconInfo ? '로컬 처리 / Local processing' : '먼저 사전을 가져오세요 / Import a dictionary first';
  enabled.onchange = () => chrome.storage.local.set({enabled: enabled.checked});
  site.onchange = async () => {
    const {sites = {}} = await chrome.storage.local.get('sites');
    sites[host] = site.checked;
    await chrome.storage.local.set({sites});
  };
  document.querySelector('#options').onclick = () => chrome.runtime.openOptionsPage();
})();
