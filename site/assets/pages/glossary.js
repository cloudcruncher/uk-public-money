/* Words explained: renders api/v1/glossary.json as one definition list. Each term has id "g-<id>" so tooltips can link to glossary.html#g-<id>. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const host = $('#glossary');
  const letters = $('#letters');
  let data;
  try { data = await U.getJSON('glossary.json'); } catch (e) { U.state(host, 'Could not load the glossary: ' + e.message, 'error'); return; }
  const terms = (data.terms || []).slice().sort((a, b) => a.term.localeCompare(b.term, 'en', { sensitivity: 'base' }));
  if (!terms.length) { U.state(host, 'No terms are published yet.'); return; }

  const byId = new Map(terms.map((t) => [t.id, t]));
  const letterOf = (t) => t.term.charAt(0).toUpperCase();
  const present = [];
  terms.forEach((t) => { const l = letterOf(t); if (present.indexOf(l) < 0) present.push(l); });

  const dl = h('dl', { class: 'glossary' });
  const seen = new Set();
  terms.forEach((t) => {
    const l = letterOf(t);
    const dt = h('dt', { id: 'g-' + t.id }, t.term);
    if (!seen.has(l)) { seen.add(l); dt.setAttribute('data-letter', l); }
    const dd = h('dd', null, h('p', null, h('strong', null, t.plain)), h('p', null, t.long));
    if (t.aliases && t.aliases.length) dd.appendChild(h('p', { class: 'small muted' }, 'Also called: ' + t.aliases.join(', ')));
    if (t.checker_only) dd.appendChild(h('p', { class: 'small muted' }, 'This term appears only in the “For checkers” sections.'));
    const rel = (t.see_also || []).filter((id) => byId.has(id));
    if (rel.length) {
      const p = h('p', { class: 'small' }, 'See also: ');
      rel.forEach((id, i) => {
        if (i) p.appendChild(document.createTextNode(', '));
        p.appendChild(h('a', { href: '#g-' + id }, byId.get(id).term));
      });
      dd.appendChild(p);
    }
    dl.append(dt, dd);
  });
  U.clear(host).appendChild(dl);

  if (letters) {
    U.clear(letters);
    const ul = h('ul', { class: 'small' });
    present.forEach((l) => {
      const first = terms.find((t) => letterOf(t) === l);
      ul.appendChild(h('li', null,h('a', { href: '#g-' + first.id }, l)));
    });
    letters.appendChild(ul);
  }

  if (location.hash.length > 1) {
    const target = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    if (target) target.scrollIntoView();
  }
});
