// SPDX-License-Identifier: Apache-2.0
(() => {
  const wrappers = new Set();
  let generation = 0, timer, panel;
  const protectedSelector = 'script,style,textarea,input,select,option,pre,code,a,button,[contenteditable], [data-gukhan]';
  function restore() {
    for (const span of wrappers) {
      if (span.isConnected) span.replaceWith(document.createTextNode(span.dataset.original));
    }
    wrappers.clear(); panel?.remove(); panel = undefined;
  }
  async function choose(event, decision) {
    event.preventDefault(); event.stopPropagation(); panel?.remove();
    panel = document.createElement('div'); panel.dataset.gukhan = 'panel';
    const shadow = panel.attachShadow({mode: 'closed'});
    const box = document.createElement('div');
    box.style.cssText = 'position:fixed;bottom:20px;right:20px;max-height:60vh;overflow:auto;max-width:360px;padding:20px;background:white;color:#172d2b;box-shadow:0 3px 30px #777;font:16px/1.5 sans-serif;z-index:2147483647';
    box.setAttribute('role', 'dialog'); box.setAttribute('aria-label', decision.word);
    const title = document.createElement('p'); title.textContent = `${decision.word} · 선택 저장 / Save choice`; box.append(title);
    const choices = [{form: '-', sense: '한글 유지 / Keep Hangul'}, ...decision.candidates];
    for (const candidate of choices) {
      const button = document.createElement('button');
      button.textContent = `${candidate.form} ${candidate.sense || ''}`;
      button.style.cssText = 'display:block;margin:8px 0;cursor:pointer';
      button.onclick = async () => {
        const {overrides = {}} = await chrome.storage.local.get('overrides');
        overrides[decision.word] = candidate.form;
        await chrome.storage.local.set({overrides}); panel?.remove();
      };
      box.append(button);
    }
    const close = document.createElement('button'); close.textContent = '닫기 / Close'; close.onclick = () => panel?.remove();
    box.append(close); shadow.append(box); document.documentElement.append(panel); close.focus();
  }
  async function render() {
    const run = ++generation;
    observer.disconnect(); restore();
    try {
      const s = await chrome.storage.local.get(['enabled', 'sites']);
      if (!s.enabled || !s.sites?.[location.hostname]) return;
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {acceptNode(node) {
        return node.parentElement && !node.parentElement.closest(protectedSelector) && /[가-힣]/.test(node.data) && node.data.length <= 20000
          ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }});
      const nodes = []; while (walker.nextNode()) nodes.push(walker.currentNode);
      for (let offset = 0; offset < nodes.length; offset += 50) {
        const batch = nodes.slice(offset, offset + 50), originals = batch.map(n => n.data);
        const response = await chrome.runtime.sendMessage({type: 'convert', texts: originals});
        if (run !== generation || !response?.results) return;
        batch.forEach((node, i) => {
          if (!node.isConnected || node.data !== originals[i] || !response.results[i].length) return;
          const fragment = document.createDocumentFragment(); let end = 0;
          for (const decision of response.results[i]) {
            fragment.append(document.createTextNode(originals[i].slice(end, decision.start)));
            const span = document.createElement('span'); span.dataset.gukhan = 'word';
            span.dataset.original = decision.word; span.textContent = decision.text;
            span.tabIndex = 0; span.setAttribute('role', 'button');
            span.title = `${decision.word} · 후보 / candidates`; span.style.textDecoration = 'underline dotted';
            span.addEventListener('click', e => choose(e, decision));
            span.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') choose(e, decision); });
            wrappers.add(span); fragment.append(span); end = decision.end;
          }
          fragment.append(document.createTextNode(originals[i].slice(end))); node.replaceWith(fragment);
        });
      }
    } finally {
      observer.observe(document.body, {childList: true, subtree: true, characterData: true});
    }
  }
  function schedule() { ++generation; clearTimeout(timer); timer = setTimeout(() => render().catch(console.error), 150); }
  const observer = new MutationObserver(records => {
    if (records.some(r => !r.target.parentElement?.closest('[data-gukhan]'))) schedule();
  });
  chrome.storage.onChanged.addListener(schedule);
  schedule();
})();
