// SPDX-License-Identifier: Apache-2.0
(() => {
  if (globalThis.__gukhanLoaded) return;  // injected again into an open page after a registered load
  globalThis.__gukhanLoaded = true;
  const wrappers = new Set();
  const groups = [];  // {original, nodes}: the text node a conversion replaced, and the nodes standing in for it
  let generation = 0, timer, panel;
  const protectedSelector = 'script,style,noscript,textarea,input,select,option,pre,code,kbd,samp,a,button,[contenteditable],[role="textbox"],[data-gukhan]';
  const mine = new WeakSet();  // the plain text pieces this script created around converted words
  // A page can hold any number of text nodes (infinite scroll, a hostile page), so the work is bounded and lazy:
  // a text node is converted only once its element has come within `MARGIN` px of the viewport, at most
  // `perPass` nodes per pass, and no more than `total` nodes are examined on one page. Beyond that the page
  // is left alone and the popup says so. `limits` in storage may lower the numbers (the tests do).
  const LIMITS = {perPass: 500, total: 20000, watch: 50000}, MARGIN = 800;
  let examined = 0, watchedCount = 0, capped = false;
  let checked = new WeakMap();  // text node -> the text that was sent and had nothing to convert
  const inView = new WeakSet(), watching = new WeakSet();
  const io = typeof IntersectionObserver === 'function' ? new IntersectionObserver(entries => {
    let any = false;
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      inView.add(entry.target); io.unobserve(entry.target); watching.delete(entry.target); any = true;
    }
    if (any) schedule(false);
  }, {rootMargin: `${MARGIN}px 0px`}) : null;
  function reportCapped(value) {
    if (value === capped) return;
    capped = value; chrome.runtime.sendMessage({type: 'capped', capped: value}).catch?.(() => {});
  }
  function restoreGroup(group) {
    // Put the replaced text node back whole, so a later pass sees "전기 공학" as one text again.
    if (group.nodes.every(n => n.isConnected)) {
      group.nodes[0].replaceWith(group.original);
      for (const n of group.nodes.slice(1)) n.remove();
    }
  }
  function restoreAll() {
    groups.forEach(restoreGroup); groups.length = 0;
    for (const span of wrappers) {
      if (span.isConnected) span.replaceWith(document.createTextNode(span.dataset.original));
    }
    wrappers.clear(); closePopover();
  }
  // --- Candidate popover: a small card anchored to the word. It is position:fixed inside a shadow
  // root, so it never moves page content; hovering previews it, a click or Enter pins it and moves
  // focus in, Escape / outside click / scrolling closes it. Styles are inline (CSSOM) so strict
  // page CSP cannot block them.
  let hoverTimer, leaveTimer, anchor, root, pinned = false;  // root: the card's shadow root
  const dark = () => matchMedia('(prefers-color-scheme: dark)').matches;
  function style(el, css) { el.style.cssText = css; return el; }
  function closePopover(returnFocus) {
    clearTimeout(hoverTimer); clearTimeout(leaveTimer);
    const was = anchor; panel?.remove(); panel = root = undefined; anchor = undefined; pinned = false;
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
    const buttons = [...root.querySelectorAll('button')];
    const at = buttons.indexOf(root.activeElement);
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
    // The page can reach an open root, but a click it fires is untrusted and every handler ignores it.
    const shadow = root = panel.attachShadow({mode: 'open'});
    const box = style(document.createElement('div'),
      `box-sizing:border-box;min-width:140px;max-width:300px;max-height:min(320px,70vh);overflow:auto;padding:4px;background:${bg};color:${fg};` +
      `border:1px solid ${line};border-radius:8px;box-shadow:0 4px 18px rgba(0,0,0,.22);font:14px/1.35 system-ui,sans-serif`);
    box.setAttribute('role', 'group'); box.setAttribute('aria-label', `${decision.word} · 후보 / candidates`);
    const head = style(document.createElement('div'), `padding:2px 8px 4px;font-size:12px;color:${accent}`);
    head.textContent = decision.word; box.append(head);
    const seen = new Set(), choices = [];
    // a native-word twin (form equal to the headword) is "Keep Hangul", listed once below
    for (const c of decision.candidates) if (c.form !== decision.word && !seen.has(c.form)) { seen.add(c.form); choices.push(c); }
    choices.push({form: '-', sense: '한글 유지 / Keep Hangul'});
    for (const candidate of choices) {
      const current = candidate.form === (decision.text === decision.word ? '-' : decision.text);
      const button = style(document.createElement('button'),
        `all:unset;box-sizing:border-box;display:block;width:100%;padding:5px 8px;border-radius:5px;cursor:pointer;` +
        `white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:${fg};font-weight:${current ? 600 : 400}`);
      const form = candidate.form === '-' ? '' : candidate.form;
      const note = `${candidate.domain ? `[${candidate.domain}] ` : ''}${candidate.sense || ''}`;  // [법률] for statute terms
      button.textContent = `${current ? '✓ ' : ''}${form}${form && note ? '  ' : ''}${note.slice(0, 40)}`;
      button.title = note;
      button.onpointerenter = button.onfocus = () => { button.style.background = hover; };
      button.onpointerleave = button.onblur = () => { button.style.background = ''; };
      button.onclick = async e => { if (!e.isTrusted) return; e.preventDefault(); e.stopPropagation(); closePopover(true); await save(decision, candidate.form); };
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
    const buttons = root.querySelectorAll('button');
    (root.querySelector('button[style*="600"]') || buttons[0]).focus({preventScroll: true});
  }
  function attach(span, decision) {
    // Only the reader's own input counts: a script on the page can dispatch events, but not trusted ones.
    span.addEventListener('pointerenter', e => {
      if (!e.isTrusted || e.pointerType !== 'mouse') return;
      clearTimeout(leaveTimer); clearTimeout(hoverTimer);
      hoverTimer = setTimeout(() => openPopover(span, decision, {pin: false}), 350);
    });
    span.addEventListener('pointerleave', () => {
      clearTimeout(hoverTimer);
      if (!pinned) leaveTimer = setTimeout(() => closePopover(), 250);
    });
    span.addEventListener('click', e => { if (!e.isTrusted) return; e.preventDefault(); e.stopPropagation(); openPopover(span, decision, {pin: true}); });
    span.addEventListener('keydown', e => {
      if (!e.isTrusted) return;
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') { e.preventDefault(); e.stopPropagation(); openPopover(span, decision, {pin: true}); }
    });
  }
  // Text nodes with Hangul that are not ours, not inside protected elements, and near the viewport.
  // Elements not yet near it are watched; they come back through the IntersectionObserver.
  function freshNodes(room) {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {acceptNode(node) {
      return !mine.has(node) && checked.get(node) !== node.data && node.parentElement && !node.parentElement.closest(protectedSelector) &&
        /[가-힣]/.test(node.data) && node.data.length <= 20000 ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
    }});
    const nodes = []; let more = false;
    while (walker.nextNode()) {
      const node = walker.currentNode, element = node.parentElement;
      if (io && !inView.has(element)) {
        if (!watching.has(element) && watchedCount < LIMITS.watch) { io.observe(element); watching.add(element); watchedCount++; }
        continue;
      }
      if (nodes.length >= room) { more = true; break; }
      nodes.push(node);
    }
    return {nodes, more};
  }
  async function convertAll(texts) {
    const results = [];
    for (let offset = 0; offset < texts.length; offset += 50) {
      const response = await chrome.runtime.sendMessage({type: 'convert', texts: texts.slice(offset, offset + 50)});
      if (!response?.results) return;
      results.push(...response.results);
    }
    return results;
  }
  // Replace `node` (a text node in the page) with words wrapped in buttons for `decisions`.
  function apply(node, text, decisions) {
    const fragment = document.createDocumentFragment(); let end = 0;
    const plain = t => { const n = document.createTextNode(t); mine.add(n); fragment.append(n); };
    for (const decision of decisions) {
      plain(text.slice(end, decision.start));
      const span = document.createElement('span'); span.dataset.gukhan = 'word';
      span.dataset.original = decision.word; span.textContent = decision.text;
      span.tabIndex = 0; span.setAttribute('role', 'button'); span.setAttribute('aria-haspopup', 'true');
      span.setAttribute('aria-label', `${decision.text} · ${decision.word} · 후보 / candidates`);
      span.style.textDecoration = 'underline dotted'; span.style.textUnderlineOffset = '2px';
      attach(span, decision);
      wrappers.add(span); fragment.append(span); end = decision.end;
    }
    plain(text.slice(end));
    groups.push({original: node, nodes: [...fragment.childNodes]}); node.replaceWith(fragment);
  }
  async function enabled() {
    const s = await chrome.storage.local.get(['enabled', 'sites', 'limits']);
    for (const key of Object.keys(LIMITS)) if (Number.isInteger(s.limits?.[key]) && s.limits[key] > 0) LIMITS[key] = s.limits[key];
    return !!(s.enabled && s.sites?.[location.hostname]);
  }
  // Everything below changes the page only in one synchronous step, with the observer off, so the
  // reader never sees Hangul flash back between a restore and the next conversion.
  async function render(full) {
    if (!document.body) return;  // an XML or SVG document has no body to convert
    const run = full ? ++generation : generation;
    if (!await enabled()) { if (run === generation) { observer.disconnect(); restoreAll(); watch(); } return; }
    if (full) checked = new WeakMap();
    const base = full ? groups.length : examined;  // nodes already examined; a full pass converts the groups again
    const {nodes, more} = freshNodes(Math.max(0, Math.min(LIMITS.perPass, LIMITS.total - base)));
    const items = nodes.map(node => ({node, text: node.data}));
    if (full) for (const group of groups) items.push({group, text: group.original.data});
    const atTotal = more && base + nodes.length >= LIMITS.total;
    const results = await convertAll(items.map(i => i.text));
    if (!results || run !== generation) return;
    observer.disconnect();
    try {
      if (full) { for (const group of groups) restoreGroup(group); groups.length = 0; closePopover(); }
      items.forEach((item, i) => {
        const node = item.group ? item.group.original : item.node;
        if (!item.group && results[i].length === 0 && node.isConnected && node.data === item.text) checked.set(node, item.text);
        if (!results[i].length || (!item.group && (!node.isConnected || node.data !== item.text))) return;
        if (item.group && !node.isConnected) return;
        apply(node, item.text, results[i]);
      });
    } finally { watch(); }
    examined = (full ? 0 : examined) + items.length;
    reportCapped(atTotal || (watchedCount >= LIMITS.watch));
    if (more && !atTotal) schedule(false);  // the next slice of nodes near the viewport
    else if (full) schedule(false);  // pick up anything the page added while we were converting
  }
  function watch() { if (document.body) observer.observe(document.body, {childList: true, subtree: true, characterData: true}); }
  let running = false, again = false, fullPending = false;
  function schedule(full) {
    fullPending ||= full;
    if (timer) return;  // a run is already queued; a busy page must not starve it by resetting the delay
    timer = setTimeout(async () => {
      timer = undefined;
      if (running) { again = true; return; }
      running = true;
      try {
        do { again = false; const f = fullPending; fullPending = false; await render(f); } while (again || fullPending);
      } catch (e) { console.error(e); } finally { running = false; }
    }, 150);
  }
  const observer = new MutationObserver(records => {
    if (records.some(r => !r.target.parentElement?.closest('[data-gukhan]'))) schedule(false);
  });
  chrome.storage.onChanged.addListener(changes => {
    // Only settings that change what the page shows; unrelated writes must not redraw it.
    if (['enabled', 'sites', 'overrides', 'lexiconInfo'].some(k => k in changes)) schedule(true);
  });
  schedule(true);
})();
