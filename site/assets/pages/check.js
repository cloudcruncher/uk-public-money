/* Check this number: check.html#p=<provenance_id>. Renders the provenance check block step by step. */
UKPM.page(async () => {
  const U = UKPM; const { h, $ } = U;
  const host = $('#check');

  function idFromHash() {
    const p = new URLSearchParams(location.hash.replace(/^#/, ''));
    return p.get('p') || '';
  }
  function copyBtn(text) {
    return h('button', {
      type: 'button', class: 'btn',
      onclick: async (e) => {
        const b = e.currentTarget;
        try { await navigator.clipboard.writeText(text); b.textContent = 'Copied'; } catch (err) { b.textContent = 'Copy failed: select the text instead'; }
        setTimeout(() => { b.textContent = 'Copy'; }, 2000);
      },
    }, 'Copy');
  }
  function fileName(url) { try { return decodeURIComponent(new URL(url).pathname.split('/').pop()); } catch (e) { return ''; } }

  async function render() {
    const id = idFromHash();
    if (!id) {
      U.clear(host).appendChild(h('div', { class: 'empty' },
        h('p', null, 'No number selected.'),
        h('p', null, 'Every number on this site has a “Check this number” link. Follow one, or ', h('a', { href: 'claims.html' }, 'look up an official figure'), '.')));
      return;
    }
    if (!U.PROV_RE.test(id)) { U.state(host, 'That link does not contain a valid provenance id.', 'error'); return; }
    U.state(host, 'Loading the record…');
    let rec;
    try { rec = await U.prov(id); } catch (e) { U.state(host, 'Could not find this record: ' + e.message, 'error'); return; }
    const c = rec.check || {};
    U.clear(host);
    document.title = 'Check ' + id + ' · UK Public Money';

    host.appendChild(h('p', { class: 'lede' }, rec.publisher, ', ', rec.dataset, ' (', rec.vintage || rec.edition, ').'));
    host.appendChild(h('p', null, U.badge(rec.status), rec.status_note ? ' ' + rec.status_note : '',
      rec.retrieval === 'fixture' ? h('span', { class: 'small muted' }, ' · retrieved from a committed test fixture (offline build)') : null));
    if (rec.retrieval === 'fixture') {
      host.appendChild(U.note('warn', 'This record was built from a test fixture. The file details below still describe the publisher’s original file, so the check works the same way.'));
    }

    const steps = h('ol', { class: 'steps' });
    if (c.kind === 'api') {
      steps.appendChild(h('li', null, h('h3', null, 'Run the query'), h('p', null, U.ext(c.query_url, 'Open the API request')), c.json_path ? h('p', null, 'Read the value at ', h('code', null, c.json_path)) : null));
    } else {
      const dl = c.download_url || rec.source_url;
      steps.appendChild(h('li', null, h('h3', null, 'Download the publisher’s file'),
        h('p', null, U.ext(dl, fileName(dl) || 'Download file')),
        (c.landing_url || rec.landing_url) ? h('p', { class: 'small' }, 'Publisher page: ', U.ext(c.landing_url || rec.landing_url)) : null,
        h('p', { class: 'small muted' }, 'Published ', rec.publication_date || 'date not recorded', '.')));
      const sha = c.sha256 || rec.file_sha256;
      const cmd = 'shasum -a 256 "' + (fileName(dl) || '<file>') + '"';
      steps.appendChild(h('li', null, h('h3', null, 'Confirm it is the same file'),
        h('p', null, 'Run this in a terminal where you saved it:'),
        h('div', { class: 'copy-row' }, h('code', null, cmd), copyBtn(cmd)),
        h('p', null, 'It should print:'),
        h('div', { class: 'copy-row' }, h('code', null, sha), copyBtn(sha)),
        h('p', { class: 'small muted' }, 'If it prints something else, the publisher has changed the file since we read it.')));
      const loc = h('dl', { class: 'kv' });
      const kv = (k, v) => { if (v != null && v !== '') U.append(loc, [h('dt', null, k), h('dd', null, v)]); };
      kv('Sheet', c.sheet || rec.sheet);
      kv('Cell', c.cell || rec.cell_or_range);
      kv('Row label', c.row_label);
      kv('Column label', c.column_label);
      kv('Value in the file', c.published_value != null ? String(c.published_value) + (c.published_unit ? ' (' + c.published_unit + ')' : '') : null);
      steps.appendChild(h('li', null, h('h3', null, 'Find the cell'), loc));
    }
    const tr = rec.transformations || [];
    steps.appendChild(h('li', null, h('h3', null, 'What we did to it'),
      tr.length ? h('ol', { class: 'chain' }, tr.map((t) => h('li', null, t.detail || t.op))) : h('p', null, 'Nothing: the figure is shown exactly as published.')));
    const inputs = c.derived_from && c.derived_from.length ? c.derived_from : (rec.inputs || []);
    if (inputs.length) {
      steps.appendChild(h('li', null, h('h3', null, 'Check the other inputs'),
        h('p', null, 'This figure also uses these published numbers (for example the GDP deflator or GDP). Each has its own check:'),
        h('ul', null, inputs.map((pid) => h('li', null, U.checkHref(pid) ? h('a', { href: U.checkHref(pid) }, pid) : h('code', null, pid))))));
    }
    host.appendChild(steps);

    const meta = h('dl', { class: 'kv' });
    const m = (k, v) => { if (v != null && v !== '') U.append(meta, [h('dt', null, k), h('dd', null, v)]); };
    m('Provenance id', h('code', null, rec.provenance_id));
    m('Licence', rec.licence_url ? U.ext(rec.licence_url, rec.licence) : rec.licence);
    m('Retrieved', (rec.retrieved_at || '') + ' (' + (rec.retrieval || '?') + ')');
    m('Instructions', c.instructions);
    host.appendChild(h('h2', null, 'Full record'));
    host.appendChild(meta);
  }
  window.addEventListener('hashchange', async () => {
    await render();
    const t = $('#check-title'); if (t) t.focus();
  });
  await render();
});
