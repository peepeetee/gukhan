// SPDX-License-Identifier: Apache-2.0
(() => {
  const wrappers = new Set();
  const groups = [];  // {original, nodes}: the text node a conversion replaced, and the nodes standing in for it
  let generation = 0, timer, panel;
  const protectedSelector = 'script,style,textarea,input,select,option,pre,code,a,button,[contenteditable], [data-gukhan]';
  function restore() {
    // Put each replaced text node back whole, so a later pass sees "전기 공학" as one text again.
    for (const {original, nodes} of groups) {
      if (!nodes.every(n => n.isConnected)) continue;
      nodes[0].replaceWith(original);
      for (const n of nodes.slice(1)) n.remove();
    }
    groups.length = 0;
    for (const span of wrappers) {
      if (span.isConnected) span.replaceWith(document.createTextNode(span.dataset.original));
    }
    wrappers.clear(); closePopover();
  }
  // --- Candidate popover: a small card anchored to the word. It is position:fixed inside a shadow
  // root, so it never moves page content; hovering previews it, a click or Enter pins it and moves
  // focus in, Escape / outside click / scrolling closes it. Styles are inline (CSSOM) so strict
  // page CSP cannot block them.
  let hoverTimer, leaveTimer, anchor, pinned = false;
  const dark = () => matchMedia('(prefers-color-scheme: dark)').matches;
  function style(el, css) { el.style.cssText = css; return el; }
  function closePopover(returnFocus) {
    clearTimeout(hoverTimer); clearTimeout(leaveTimer);
    const was = anchor; panel?.remove(); panel = undefined; anchor = undefined; pinned = false;
    removeEventListener('scroll', onScroll, true); removeEventListener('resize', onScroll);
    removeEventListener('pointerdown', onOutside, true); removeEventListener('keydown', onKey, true);
    if (returnFocus && was?.isConnected) was.focus();
  }
  const onScroll = () => closePopover();
  const onOutside = e => { if (!e.composedPath().includes(panel) && !e.composedPath().includes(anchor)) closePopover(); };
  function onKey(e) {
    if (!panel) return;
    if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); closePopover(true); return; }
    if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(e.key) || !pinned) return;
    const buttons = [...panel.shadowRoot.querySelectorAll('button')];
    const at = buttons.indexOf(panel.shadowRoot.activeElement);
    const next = e.key === 'Home' ? 0 : e.key === 'End' ? buttons.length - 1 :
      (at + (e.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length;
    e.preventDefault(); e.stopPropagation(); buttons[next].focus();
  }
  async function save(decision, form) {
    const {overrides = {}} = await chrome.storage.local.get('overrides');
    overrides[decision.word] = form;
    await chrome.storage.local.set({overrides});
  }
  function openPopover(span, decision, {pin}) {
    clearTimeout(leaveTimer);
    if (panel && anchor === span) { if (pin) pinPopover(); return; }
    closePopover();
    const night = dark(), fg = night ? '#e8eeec' : '#172d2b', bg = night ? '#1f2a28' : '#ffffff',
      line = night ? '#43544f' : '#cfd8d4', hover = night ? '#2e3d39' : '#e8f1ee', accent = night ? '#7fcab9' : '#235c53';
    anchor = span; panel = document.createElement('div'); panel.dataset.gukhan = 'panel';
    style(panel, 'all:initial;position:fixed;z-index:2147483647;top:0;left:0');
    const shadow = panel.attachShadow({mode: 'open'});
    const box = style(document.createElement('div'),
      `box-sizing:border-box;min-width:140px;max-width:300px;max-height:min(320px,70vh);overflow:auto;padding:4px;background:${bg};color:${fg};` +
      `border:1px solid ${line};border-radius:8px;box-shadow:0 4px 18px rgba(0,0,0,.22);font:14px/1.35 system-ui,sans-serif`);
    box.setAttribute('role', 'group'); box.setAttribute('aria-label', `${decision.word} · 후보 / candidates`);
    const head = style(document.createElement('div'), `padding:2px 8px 4px;font-size:12px;color:${accent}`);
    head.textContent = decision.word; box.append(head);
    const seen = new Set(), choices = [];
    for (const c of decision.candidates) if (!seen.has(c.form)) { seen.add(c.form); choices.push(c); }
    choices.push({form: '-', sense: '한글 유지 / Keep Hangul'});
    for (const candidate of choices) {
      const current = candidate.form === (decision.text === decision.word ? '-' : decision.text);
      const button = style(document.createElement('button'),
        `all:unset;box-sizing:border-box;display:block;width:100%;padding:5px 8px;border-radius:5px;cursor:pointer;` +
        `white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:${fg};font-weight:${current ? 600 : 400}`);
      const form = candidate.form === '-' ? '' : candidate.form;
      button.textContent = `${current ? '✓ ' : ''}${form}${form && candidate.sense ? '  ' : ''}${(candidate.sense || '').slice(0, 40)}`;
      button.title = candidate.sense || '';
      button.onpointerenter = button.onfocus = () => { button.style.background = hover; };
      button.onpointerleave = button.onblur = () => { button.style.background = ''; };
      button.onclick = async e => { e.preventDefault(); e.stopPropagation(); closePopover(true); await save(decision, candidate.form); };
      box.append(button);
    }
    box.addEventListener('pointerenter', () => clearTimeout(leaveTimer));
    box.addEventListener('pointerleave', () => { if (!pinned) leaveTimer = setTimeout(() => closePopover(), 250); });
    shadow.append(box); document.documentElement.append(panel);
    // Anchor below the word, or above when there is no room; keep inside the viewport.
    const r = span.getBoundingClientRect(), b = box.getBoundingClientRect(), gap = 4;
    const top = r.bottom + gap + b.height <= innerHeight || r.top - gap - b.height < 0 ? r.bottom + gap : r.top - gap - b.height;
    panel.style.top = `${Math.max(0, Math.min(top, innerHeight - b.height))}px`;
    panel.style.left = `${Math.max(4, Math.min(r.left, innerWidth - b.width - 4))}px`;
    addEventListener('scroll', onScroll, true); addEventListener('resize', onScroll);
    addEventListener('pointerdown', onOutside, true); addEventListener('keydown', onKey, true);
    if (pin) pinPopover();
  }
  function pinPopover() {
    pinned = true;
    const buttons = panel.shadowRoot.querySelectorAll('button');
    (panel.shadowRoot.querySelector('button[style*="600"]') || buttons[0]).focus({preventScroll: true});
  }
  function attach(span, decision) {
    span.addEventListener('pointerenter', e => {
      if (e.pointerType !== 'mouse') return;
      clearTimeout(leaveTimer); clearTimeout(hoverTimer);
      hoverTimer = setTimeout(() => openPopover(span, decision, {pin: false}), 350);
    });
    span.addEventListener('pointerleave', () => {
      clearTimeout(hoverTimer);
      if (!pinned) leaveTimer = setTimeout(() => closePopover(), 250);
    });
    span.addEventListener('click', e => { e.preventDefault(); e.stopPropagation(); openPopover(span, decision, {pin: true}); });
    span.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') { e.preventDefault(); e.stopPropagation(); openPopover(span, decision, {pin: true}); }
    });
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
            span.tabIndex = 0; span.setAttribute('role', 'button'); span.setAttribute('aria-haspopup', 'true');
            span.setAttribute('aria-label', `${decision.text} · ${decision.word} · 후보 / candidates`);
            span.style.textDecoration = 'underline dotted'; span.style.textUnderlineOffset = '2px';
            attach(span, decision);
            wrappers.add(span); fragment.append(span); end = decision.end;
          }
          fragment.append(document.createTextNode(originals[i].slice(end)));
          groups.push({original: node, nodes: [...fragment.childNodes]}); node.replaceWith(fragment);
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
