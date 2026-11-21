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
  // --- Missing glyphs. A Hanja the page's font lacks shows as an empty space or a box (tofu). The check draws the
  // character on a canvas in the element's own font: no ink at all, or the same picture as a character that no
  // font has, means missing. Where the browser draws something else for a missing glyph (Firefox
  // puts its code point in the box) the check says nothing rather than guessing. If the canvas cannot be read
  // (a privacy setting that blanks it) it also says nothing.
  const HAN = /[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF\u{20000}-\u{3134F}]/u;
  // Reference code points that no font draws. Browsers differ: some draw a box only for an assigned character that
  // no font has (the last characters of CJK Extensions G, H and I), some also for an unassigned BMP one, and
  // none draw one for noncharacters like U+FFFF, so a few of each are compared and any equal picture counts.
  const SENTINELS = ['\u0378', '\u{3134A}', '\u{323AF}', '\u{2EE5D}'];
  const glyphs = (() => {
    let ctx, usable, empties;
    const cache = new Map();
    const draw = (ch, font) => {
      ctx.clearRect(0, 0, 64, 64); ctx.font = font; ctx.fillText(ch, 8, 44);
      const data = ctx.getImageData(0, 0, 64, 64).data; let n = 0, hash = 0;
      for (let i = 3; i < data.length; i += 4) if (data[i]) { n++; hash = (hash * 31 + i * data[i]) >>> 0; }
      return {n, hash};
    };
    return function missing(ch, element) {
      try {
        if (usable === undefined) {
          const canvas = document.createElement('canvas'); canvas.width = canvas.height = 64;
          ctx = canvas.getContext('2d', {willReadFrequently: true});
          usable = !!ctx && draw('H', '32px sans-serif').n > 0;  // a blanked canvas would call everything missing
        }
        if (!usable) return false;
        const style = getComputedStyle(element), font = `${style.fontStyle} ${style.fontWeight} 32px ${style.fontFamily}`;
        const key = `${font}|${ch}`;
        if (!cache.has(key)) {
          const sentinels = SENTINELS.map(c => draw(c, font));
          const mine = draw(ch, font);
          cache.set(key, mine.n === 0 || sentinels.some(s => s.n > 0 && s.hash === mine.hash && s.n === mine.n));
        }
        return cache.get(key);
      } catch { usable = false; return false; }
    };
  })();
  const toCheck = [];  // {span, text} for words just converted
  const missingChars = new Set();
  let reportedMissing = 0;
  function checkGlyphs() {
    let budget = 300;
    for (const {span, text} of toCheck.splice(0)) {
      for (const ch of text) if (HAN.test(ch) && budget-- > 0 && glyphs(ch, span)) missingChars.add(ch);
    }
    if (missingChars.size !== reportedMissing) {
      reportedMissing = missingChars.size;
      chrome.runtime.sendMessage({type: 'glyphs', count: missingChars.size, sample: [...missingChars].slice(0, 8)}).catch?.(() => {});
    }
  }
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
    if (e.key === 'Tab' && pinned) { closePopover(true); return; }  // focus goes back to the word and Tab moves on from there
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
    const touch = matchMedia('(pointer: coarse)').matches;  // a finger needs a 44 px target (Firefox for Android)
    anchor = span; panel = document.createElement('div'); panel.dataset.gukhan = 'panel';
    style(panel, 'all:initial;position:fixed;z-index:2147483647;top:0;left:0');
    // The page can reach an open root, but a click it fires is untrusted and every handler ignores it.
    const shadow = root = panel.attachShadow({mode: 'open'});
    const box = style(document.createElement('div'),
      `box-sizing:border-box;min-width:140px;max-width:300px;max-height:min(320px,70vh);overflow:auto;padding:4px;background:${bg};color:${fg};` +
      `border:1px solid ${line};border-radius:8px;box-shadow:0 4px 18px rgba(0,0,0,.22);font:14px/1.35 system-ui,sans-serif`);
    box.setAttribute('role', 'group'); box.lang = 'ko'; box.setAttribute('aria-label', `${decision.word} · 후보 / candidates`);
    const head = style(document.createElement('div'), `padding:2px 8px 4px;font-size:12px;color:${accent}`);
    head.textContent = decision.word; head.setAttribute('aria-hidden', 'true'); box.append(head);  // the group's label says it
    const seen = new Set(), choices = [];
    // a native-word twin (form equal to the headword) is "Keep Hangul", listed once below
    for (const c of decision.candidates) if (c.form !== decision.word && !seen.has(c.form)) { seen.add(c.form); choices.push(c); }
    choices.push({form: '-', sense: '한글 유지 / Keep Hangul'});
    // 한자 풀이: the reading and meaning of each Hanja of the candidate under the pointer (or of the chosen one),
    // from the character list if one was imported; nothing is shown without it.
    const detail = style(document.createElement('div'), `padding:4px 8px 2px;font-size:12px;color:${accent};white-space:normal;display:none`);
    detail.setAttribute('role', 'status');  // read out as the pointer or focus moves between candidates
    let info = {};
    const showDetail = candidate => {
      const lines = [...(candidate?.form === '-' ? '' : candidate?.form || '')].filter(ch => info[ch]).map(ch => {
        const {readings = [], meaning = '', hun = ''} = info[ch];
        // the Korean 訓 (물 수) when the list has one; the English meaning otherwise
        return hun ? `${ch} ${hun} ${readings.join('/')}` : `${ch} ${readings.join('/')}${meaning ? ' · ' + meaning.slice(0, 40) : ''}`;
      });
      detail.textContent = lines.join('\n'); detail.style.whiteSpace = 'pre-line'; detail.style.display = lines.length ? 'block' : 'none';
    };
    const chosen = () => choices.find(c => c.form === (decision.text === decision.word ? '-' : decision.text));
    for (const candidate of choices) {
      const current = candidate.form === (decision.text === decision.word ? '-' : decision.text);
      const button = style(document.createElement('button'),
        `all:unset;box-sizing:border-box;display:block;width:100%;padding:5px 8px;border-radius:5px;cursor:pointer;${touch ? 'min-height:44px;line-height:34px;' : ''}` +
        `white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:${fg};font-weight:${current ? 600 : 400}`);
      const form = candidate.form === '-' ? '' : candidate.form;
      const note = `${candidate.domain ? `[${candidate.domain}] ` : ''}${candidate.sense || ''}`;  // [법률] for statute terms
      if (current) { const tick = document.createElement('span'); tick.textContent = '✓ '; tick.setAttribute('aria-hidden', 'true'); button.append(tick); }
      button.append(`${form}${form && note ? '  ' : ''}${note.slice(0, 40)}`);
      button.setAttribute('aria-pressed', String(current));  // the saved choice, which the ✓ shows to the eye
      if (!form) button.setAttribute('aria-label', '한글 유지 / Keep Hangul');
      button.title = note;
      button.onpointerenter = () => { button.style.background = hover; showDetail(candidate); };
      button.onpointerleave = () => { button.style.background = ''; showDetail(chosen()); };
      // a visible 2 px ring on keyboard focus (the hover tint alone is far below 3:1)
      button.onfocus = () => { button.style.background = hover; button.style.outline = `2px solid ${accent}`; button.style.outlineOffset = '-2px'; showDetail(candidate); };
      button.onblur = () => { button.style.background = ''; button.style.outline = ''; showDetail(chosen()); };
      button.onclick = async e => { if (!e.isTrusted) return; e.preventDefault(); e.stopPropagation(); closePopover(true); await save(decision, candidate.form); };
      box.append(button);
    }
    box.append(detail);
    const wanted = [...new Set(choices.flatMap(c => c.form === '-' ? [] : [...c.form].filter(ch => HAN.test(ch))))];
    if (wanted.length) {
      chrome.runtime.sendMessage({type: 'chars', chars: wanted}).then(answer => {
        if (panel && anchor === span && answer?.info) { info = answer.info; showDetail(chosen()); }
      }).catch?.(() => {});
    }
    if (choices.some(c => c.form !== '-' && [...c.form].some(ch => HAN.test(ch) && glyphs(ch, span)))) {
      const note = style(document.createElement('div'), `padding:4px 8px 2px;font-size:12px;color:${accent};white-space:normal`);
      note.textContent = '□ 이 글꼴에 없는 글자가 있습니다. Noto Serif/Sans CJK KR 같은 글꼴을 설치해 보세요. / Some characters are missing from this font and show as boxes; try a font such as Noto Serif or Noto Sans CJK KR.';
      box.append(note);
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
  // Write a converted word into its span in the reader's output style: plain text (mixed, gloss, hanja-gloss) or one
  // <ruby> pair per Hanja. The worker sends `parts`; with none, the word is just its text.
  function fill(span, decision) {
    const parts = decision.parts;
    if (!Array.isArray(parts?.ruby)) { span.textContent = typeof parts?.text === 'string' ? parts.text : decision.text; return; }
    for (const [base, reading] of parts.ruby) {
      if (!reading) { span.append(base); continue; }
      const ruby = document.createElement('ruby'), open = document.createElement('rp'), rt = document.createElement('rt'), close = document.createElement('rp');
      open.textContent = '('; rt.textContent = reading; close.textContent = ')';
      ruby.append(base, open, rt, close); span.append(ruby);
    }
  }
  // Replace `node` (a text node in the page) with words wrapped in buttons for `decisions`.
  function apply(node, text, decisions) {
    const fragment = document.createDocumentFragment(); let end = 0;
    const plain = t => { const n = document.createTextNode(t); mine.add(n); fragment.append(n); };
    for (const decision of decisions) {
      plain(text.slice(end, decision.start));
      const span = document.createElement('span'); span.dataset.gukhan = 'word';
      span.dataset.original = decision.word; fill(span, decision);
      // A screen reader says Hanja badly, so the accessible name leads with the Hangul reading (the word as the author
      // wrote it) and adds the Hanja form; lang="ko" makes it read them as Korean. The description says what Enter does.
      span.tabIndex = 0; span.lang = 'ko'; span.setAttribute('role', 'button'); span.setAttribute('aria-haspopup', 'true');
      span.setAttribute('aria-label', decision.text === decision.word ? decision.word : `${decision.word} · ${decision.text}`);
      span.setAttribute('aria-description', '후보 보기 / Show candidates');
      span.style.textDecoration = 'underline dotted'; span.style.textUnderlineOffset = '2px';
      span.addEventListener('focus', () => { span.style.outline = `2px solid ${dark() ? '#7fcab9' : '#235c53'}`; span.style.outlineOffset = '2px'; });
      span.addEventListener('blur', () => { span.style.outline = ''; span.style.outlineOffset = ''; });
      attach(span, decision);
      wrappers.add(span); toCheck.push({span, text: decision.text}); fragment.append(span); end = decision.end;
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
    checkGlyphs();
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
    if (['enabled', 'sites', 'overrides', 'lexiconInfo', 'style'].some(k => k in changes)) schedule(true);
  });
  schedule(true);
})();
