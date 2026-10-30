// Tax requisites lookup: pick a payment and an inspectorate, get copyable bank details.
(() => {
  const root = document.querySelector('[data-rq]');
  if (!root) return;

  const dataUrl = new URL('data/rekvizity.json', document.currentScript.src);
  const taxesBox = root.querySelector('[data-rq-taxes]');
  const groupWrap = root.querySelector('[data-rq-group-wrap]');
  const groupSelect = root.querySelector('[data-rq-group]');
  const placeWrap = root.querySelector('[data-rq-place-wrap]');
  const placeSelect = root.querySelector('[data-rq-place]');
  const card = root.querySelector('[data-rq-card]');

  const FIELDS = [
    ['name', 'Бенефициар'],
    ['unp', 'УНП бенефициара'],
    ['actualName', 'Фактический бенефициар'],
    ['actualUnp', 'УНП фактического бенефициара'],
    ['account', 'Номер счёта (IBAN)'],
    ['bank', 'Банк'],
    ['bic', 'БИК банка'],
    ['payCode', 'Код платежа'],
    ['purposeCode', 'Код назначения платежа'],
    ['category', 'Категория перевода'],
    ['priority', 'Очерёдность'],
    ['currency', 'Код валюты'],
  ];

  let data;
  let state = { tax: null, group: 0, place: 0 };

  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const tax = () => data.taxes.find((t) => t.slug === state.tax);
  const records = () => {
    const t = tax();
    return t.groups ? t.groups[state.group].records : t.records || [];
  };

  const copy = async (text, btn) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const ta = Object.assign(document.createElement('textarea'), { value: text });
      document.body.append(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    btn.classList.add('is-copied');
    const label = btn.querySelector('[data-label]');
    const prev = label ? label.textContent : null;
    if (label) label.textContent = '✓ Скопировано';
    setTimeout(() => {
      btn.classList.remove('is-copied');
      if (label) label.textContent = prev;
    }, 2000);
  };

  const fillPlaces = () => {
    const list = records();
    const regions = [...new Set(list.map((r) => r.region))];
    placeSelect.innerHTML = regions.map((reg) => {
      const opts = list.map((r, i) => (r.region === reg ? `<option value="${i}">${esc(r.title)}</option>` : '')).join('');
      return reg ? `<optgroup label="${esc(reg)}">${opts}</optgroup>` : opts;
    }).join('');
    state.place = Math.min(state.place, list.length - 1);
    placeSelect.value = String(state.place);
    placeWrap.hidden = list.length < 2;
  };

  const renderCard = () => {
    const t = tax();
    if (t.text) {
      card.innerHTML = `<h3 class="rq-card-title">${esc(t.title)}</h3><ul class="rq-codes">${t.text.map((l) => `<li>${esc(l)}</li>`).join('')}</ul>`;
      return;
    }
    const r = records()[state.place];
    const fields = FIELDS.filter(([k]) => r[k]);
    const rows = fields.map(([k, label], i) => `
      <div class="rq-line" data-row="${i}">
        <dt>${label}</dt>
        <dd><span class="${k === 'account' ? 'rq-mono' : ''}">${esc(r[k])}</span>
          <button type="button" class="rq-copy" data-copy="${esc(r[k])}" aria-label="Скопировать: ${label}"><span data-label>Скопировать</span></button></dd>
      </div>`).join('');
    const sub = t.groups ? t.groups[state.group].title : '';
    card.innerHTML = `
      <header class="rq-card-head">
        <div>
          <h3 class="rq-card-title">${esc(t.title)}</h3>
          <p class="rq-card-sub">${esc([sub, r.title].filter(Boolean).join(' · '))}</p>
        </div>
        ${r.budget ? `<span class="rq-badge">${esc(r.budget)}</span>` : ''}
      </header>
      <p class="rq-hint">Нужно несколько полей? Нажимайте «Скопировать» с зажатым <kbd>Ctrl</kbd> — поля будут добавляться к уже скопированным. <kbd>Shift</kbd> — добавить все поля между двумя нажатиями.</p>
      <dl class="rq-lines">${rows}</dl>
      <div class="rq-selbar" data-selbar hidden>
        <span>✓ Скопировано полей: <b data-sel-count>0</b></span>
        <button type="button" class="rq-sel-clear" data-sel-clear>Начать заново</button>
      </div>
      ${r.note ? `<p class="rq-note">${esc(r.note)}</p>` : ''}
      <div class="rq-actions">
        <button type="button" class="btn btn--primary btn--sm" data-copy-all><span data-label>Скопировать все реквизиты</span></button>
        <button type="button" class="btn btn--ghost btn--sm" data-copy-link><span data-label>Ссылка на эти реквизиты</span></button>
      </div>`;
    card.querySelector('[data-copy-all]').addEventListener('click', (e) => {
      const text = [`${t.title}${sub ? ' — ' + sub : ''}`, r.title, ...FIELDS.filter(([k]) => r[k]).map(([k, l]) => `${l}: ${r[k]}`)].filter(Boolean).join('\n');
      copy(text, e.currentTarget);
    });
    card.querySelector('[data-copy-link]').addEventListener('click', (e) => copy(location.href, e.currentTarget));
    setupSelection(fields, r);
  };

  // Copy buttons: a plain click copies one field; Ctrl/Cmd+click adds the field to a set
  // and Shift+click adds a range, the whole set going to the clipboard each time
  let picked = { set: new Set(), anchor: null, fields: [], record: null };

  const pickedText = () => {
    const list = [...picked.set].sort((a, b) => a - b).map((i) => picked.fields[i]);
    if (list.length === 1) return picked.record[list[0][0]];
    return list.map(([k, l]) => `${l}: ${picked.record[k]}`).join('\n');
  };

  const paintPicked = () => {
    card.querySelectorAll('[data-row]').forEach((row) => {
      const on = picked.set.has(+row.dataset.row);
      row.classList.toggle('is-picked', on);
      const label = row.querySelector('.rq-copy [data-label]');
      if (!row.querySelector('.rq-copy').classList.contains('is-copied')) label.textContent = on ? '✓ Скопировано' : 'Скопировать';
    });
    // floating contact buttons would cover the bar
    document.body.classList.toggle('rq-selecting', picked.set.size > 0);
    const bar = card.querySelector('[data-selbar]');
    if (!bar) return;
    bar.hidden = picked.set.size < 2;
    bar.querySelector('[data-sel-count]').textContent = picked.set.size;
  };

  const resetPicked = () => { picked.set.clear(); picked.anchor = null; paintPicked(); };

  const setupSelection = (fields, record) => {
    picked = { set: new Set(), anchor: null, fields, record };
    card.querySelectorAll('[data-row]').forEach((row) => {
      const i = +row.dataset.row;
      const btn = row.querySelector('.rq-copy');
      // Shift+click would otherwise highlight page text
      btn.addEventListener('mousedown', (e) => { if (e.shiftKey) e.preventDefault(); });
      btn.addEventListener('click', async (e) => {
        if (e.shiftKey) {
          const from = picked.anchor ?? i;
          for (let n = Math.min(from, i); n <= Math.max(from, i); n++) picked.set.add(n);
          picked.anchor = i;
        } else if (e.ctrlKey || e.metaKey) {
          if (picked.set.has(i)) picked.set.delete(i); else picked.set.add(i);
          picked.anchor = i;
        } else {
          picked.set.clear();
          picked.anchor = i;
          paintPicked();
          await copy(btn.dataset.copy, btn);
          return;
        }
        paintPicked();
        if (picked.set.size) {
          await copy(pickedText(), btn);
          setTimeout(paintPicked, 2050); // restore labels after the copy flash
        }
      });
    });
    card.querySelector('[data-sel-clear]').addEventListener('click', resetPicked);
    paintPicked();
  };

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && picked.set.size) resetPicked();
  });

  const syncHash = () => {
    const t = tax();
    const parts = [state.tax];
    if (t.groups) parts.push('g' + state.group);
    if (!t.text && records().length > 1) parts.push('p' + state.place);
    history.replaceState(null, '', '#' + parts.join('/'));
  };

  const render = (updateHash = true) => {
    const t = tax();
    taxesBox.querySelectorAll('.rq-tax').forEach((b) => {
      const on = b.dataset.slug === state.tax;
      b.classList.toggle('is-active', on);
      b.setAttribute('aria-selected', String(on));
    });
    groupWrap.hidden = !t.groups;
    if (t.groups) {
      groupSelect.innerHTML = t.groups.map((g, i) => `<option value="${i}">${esc(g.title)}</option>`).join('');
      groupSelect.value = String(state.group);
    }
    if (t.text) placeWrap.hidden = true;
    else fillPlaces();
    renderCard();
    if (updateHash) syncHash();
  };

  const readHash = () => {
    const [slug, ...rest] = decodeURIComponent(location.hash.slice(1)).split('/');
    if (!data.taxes.some((t) => t.slug === slug)) return false;
    state = { tax: slug, group: 0, place: 0 };
    rest.forEach((p) => {
      if (p[0] === 'g') state.group = Math.max(0, parseInt(p.slice(1), 10) || 0);
      if (p[0] === 'p') state.place = Math.max(0, parseInt(p.slice(1), 10) || 0);
    });
    const t = tax();
    if (t.groups) state.group = Math.min(state.group, t.groups.length - 1);
    return true;
  };

  taxesBox.addEventListener('click', (e) => {
    const b = e.target.closest('.rq-tax');
    if (!b || b.dataset.slug === state.tax) return;
    // keep the chosen inspectorate when switching between taxes that list the same offices
    const keep = records()[state.place]?.title;
    state.tax = b.dataset.slug;
    state.group = 0;
    const i = tax().text ? -1 : records().findIndex((r) => r.title === keep);
    state.place = i >= 0 ? i : 0;
    render();
  });
  groupSelect.addEventListener('change', () => { state.group = +groupSelect.value; render(); });
  placeSelect.addEventListener('change', () => { state.place = +placeSelect.value; renderCard(); syncHash(); });

  window.addEventListener('hashchange', () => {
    if (data && readHash()) {
      render(false);
      root.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });

  fetch(dataUrl)
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((json) => {
      data = json;
      root.querySelector('[data-rq-checked]').textContent = new Date(data.checked).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
      taxesBox.innerHTML = data.taxes.map((t) => `<button type="button" class="rq-tax" role="tab" data-slug="${t.slug}">${esc(t.title)}</button>`).join('');
      const fromHash = readHash();
      if (!fromHash) state = { tax: data.taxes[0].slug, group: 0, place: 0 };
      render(fromHash);
      if (fromHash) root.scrollIntoView({ block: 'start' });
    })
    .catch(() => {
      card.innerHTML = '<p>Не удалось загрузить справочник. Обновите страницу или посмотрите реквизиты на <a href="https://nalog.gov.by/inspectorates/payment_details/">сайте МНС</a>.</p>';
      taxesBox.innerHTML = '';
    });
})();
