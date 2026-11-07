/* Brevista CME Calendar - Design E. Plain JS, no framework, no build step. Data: conferences.json */
(function () {
  'use strict';
  var MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  var SCENES = ['panel', 'workshop', 'boardroom'];
  var POS = { panel: '50% 42%', workshop: '50% 45%', boardroom: '62% 45%' };
  var LS_KEY = 'cme_e_filters_v1';
  var FILTERS = [
    { k: 'year', label: 'Year', title: 'Filter by year', icon: '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/>' },
    { k: 'month', label: 'Month', title: 'Filter by month', icon: '<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M3 10h18M8 3v4M16 3v4"/>' },
    { k: 'city', label: 'City', title: 'Filter by city', icon: '<path d="M12 21s-7-6.2-7-11.5a7 7 0 0114 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>' },
    { k: 'spec', label: 'Specialty', title: 'Filter by specialty', icon: '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>' }
  ];
  var PIN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#5B2E9E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7-6.2-7-11.5a7 7 0 0114 0C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>';
  var CHEV_UP = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 15l6-6 6 6"/></svg>';
  var CHEV_R = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>';
  var CHEV_D = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#34195F" stroke-width="2.6" stroke-linecap="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';

  var $ = function (id) { return document.getElementById(id); };
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function norm(s) { return String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }
  function todayISO() { var d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function lsGet() { try { return JSON.parse(localStorage.getItem(LS_KEY) || '{}') || {}; } catch (e) { return {}; } }
  function lsSet(o) { try { localStorage.setItem(LS_KEY, JSON.stringify(o)); } catch (e) { /* storage unavailable */ } }
  function reduceMotion() { return window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches; }

  var all = [], meta = {}, today = (window.__CME_TODAY__ || todayISO());
  var S = { q: '', year: '', month: '', city: '', spec: '', open: undefined };
  var cur = []; // currently filtered list
  var byId = {};

  /* ---------- dates ---------- */
  function ymd(s) { return { y: +s.slice(0, 4), m: +s.slice(5, 7), d: +s.slice(8, 10) }; }
  function longDate(s) { var p = ymd(s); return MON[p.m - 1] + ' ' + p.d + ', ' + p.y; }
  function dateChip(e) {
    if (e.precision === 'tba') return e.year ? e.year + ' · dates TBA' : 'Dates TBA';
    if (e.precision === 'month') return 'Dates TBA';
    var a = ymd(e.start), b = ymd(e.end || e.start);
    if (e.start === (e.end || e.start)) return MON[a.m - 1] + ' ' + a.d;
    if (a.y === b.y && a.m === b.m) return MON[a.m - 1] + ' ' + a.d + '–' + b.d;
    var t = MON[a.m - 1] + ' ' + a.d + ' – ' + MON[b.m - 1] + ' ' + b.d;
    return a.y === b.y ? t : t + ', ' + b.y;
  }
  function place(e) { var l = (e.location || '').trim(); return !l || /to be announced/i.test(l) ? 'Location TBA' : l; }
  function verLabel(e) {
    return e.verification === 'Verified' ? 'Verified' : e.verification === 'Checked-not-announced' ? 'Checked: dates not yet announced' : 'Details pending verification';
  }

  /* ---------- data ---------- */
  function prepare(entries) {
    var out = [];
    entries.forEach(function (e) {
      var dated = e.precision === 'exact' || e.precision === 'month';
      if (dated ? !(e.end >= today) : e.status === 'Completed') return;
      e._key = dated ? e.start.slice(0, 7) : 'tba';
      e._h = norm([e.name, e.society, e.city, e.location, e.specialty].join(' '));
      out.push(e);
      byId[e.id] = e;
    });
    out.sort(function (a, b) {
      if (a._key === 'tba' && b._key !== 'tba') return 1;
      if (b._key === 'tba' && a._key !== 'tba') return -1;
      return (a.start || '9').localeCompare(b.start || '9') || a.name.localeCompare(b.name);
    });
    return out;
  }
  function matches(e, st) {
    if (st.year && String(e.year) !== st.year) return false;
    if (st.month && String(e.month) !== st.month) return false;
    if (st.city && e.city !== st.city) return false;
    if (st.spec && e.specialty !== st.spec) return false;
    if (st.q) { var toks = norm(st.q).split(/\s+/).filter(Boolean); for (var i = 0; i < toks.length; i++) if (e._h.indexOf(toks[i]) < 0) return false; }
    return true;
  }
  function options(kind) {
    var m = {};
    all.forEach(function (e) {
      var v = kind === 'year' ? e.year : kind === 'month' ? e.month : kind === 'city' ? e.city : e.specialty;
      if (v == null || v === '' || v === 'TBA') return;
      m[v] = (m[v] || 0) + 1;
    });
    var arr = Object.keys(m).map(function (k) {
      return { value: String(k), count: m[k], label: kind === 'month' ? MONTHS[+k - 1] : String(k) };
    });
    if (kind === 'year' || kind === 'month') arr.sort(function (a, b) { return +a.value - +b.value; });
    else arr.sort(function (a, b) { return a.label.localeCompare(b.label); });
    return arr;
  }

  /* ---------- rendering ---------- */
  function groupsOf(list) {
    var order = [], map = {};
    list.forEach(function (e) { if (!map[e._key]) { map[e._key] = []; order.push(e._key); } map[e._key].push(e); });
    return { order: order, map: map };
  }
  function whereSummary(items) {
    var c = items[0].city;
    if (!c || c === 'TBA') return 'Various locations';
    for (var i = 1; i < items.length; i++) if (items[i].city !== c) return 'Various locations';
    return items[0].location && !/to be announced/i.test(items[0].location) ? items[0].location : c;
  }
  // photo scene rotates by card position in the rendered list (index mod 3), never tied to a conference
  function cardHTML(e, i) {
    var sc = SCENES[i % 3];
    var chip = e.verification === 'Verified' ? '<span class="chip-v">Verified</span>' : '<span class="chip-p">Details pending</span>';
    var note = e.verification !== 'Verified' && e.notes ? '<div class="c-note">' + esc(e.notes) + '</div>' : '';
    return '<li><button type="button" class="card" data-id="' + e.id + '" aria-haspopup="dialog">' +
      '<div class="photo"><img src="img/' + sc + '.webp" width="720" height="392" alt="" loading="lazy" decoding="async" style="object-position:' + POS[sc] + '">' + chip + '</div>' +
      '<div class="c-body"><div class="c-title">' + esc(e.name) + '</div>' +
      '<div class="chips"><span>' + esc(dateChip(e)) + '</span><span>' + esc(place(e)) + '</span></div>' +
      '<div class="c-spec">' + esc(e.specialty) + '</div>' + note + '</div></button></li>';
  }
  function monthHTML(key, items, open) {
    var head, y, mon, name;
    if (key === 'tba') { mon = 'DATES'; y = 'TBA'; name = 'Dates to be announced'; }
    else { var p = key.split('-'); mon = MON[+p[1] - 1].toUpperCase(); y = p[0]; name = MONTHS[+p[1] - 1] + ' ' + p[0]; }
    var sub = whereSummary(items);
    head = '<button type="button" class="m-head" data-key="' + key + '" aria-expanded="' + open + '"' + (open ? ' aria-controls="p-' + key + '"' : '') + '>' +
      '<span class="m-date"><span>' + mon + '</span><span class="y">' + y + '</span><span class="badge" aria-label="' + items.length + ' conferences">' + items.length + '</span></span>' +
      '<span class="m-div"></span>' +
      '<span class="m-text"><span class="m-name">' + name + '</span><span class="m-sub">' + (open ? PIN : '') + esc(sub) + '</span></span>' +
      '<span class="m-btn">' + (open ? CHEV_UP : CHEV_R) + '</span></button>';
    var body = open ? '<ul class="cards" id="p-' + key + '">' + items.map(cardHTML).join('') + '</ul>' : '';
    return '<section class="month' + (open ? ' open' : '') + '" aria-label="' + esc(name) + '">' + head + body + '</section>';
  }
  function anyFilter() { return !!(S.q || S.year || S.month || S.city || S.spec); }
  function render(focusKey) {
    cur = all.filter(function (e) { return matches(e, S); });
    var g = groupsOf(cur);
    if (S.open === undefined || (S.open !== null && !g.map[S.open])) S.open = g.order.length ? g.order[0] : null;
    var host = $('months');
    if (!cur.length) {
      host.innerHTML = '<div class="empty">No conferences match' + (S.q ? ' “' + esc(S.q) + '”' : ' these filters') + '.<br>Try a different word or clear a filter.<br><button type="button" data-reset="1">Show all conferences</button></div>';
    } else {
      host.innerHTML = g.order.map(function (k) { return monthHTML(k, g.map[k], S.open === k); }).join('');
    }
    var ex = cur.filter(function (e) { return e.precision === 'exact'; }).length;
    var b = $('export'); b.disabled = !ex;
    $('exportLabel').textContent = ex ? 'Export ' + ex + ' to calendar (.ics)' : 'Nothing to export';
    $('summary').textContent = anyFilter() ? 'Showing ' + cur.length + ' of ' + all.length + ' upcoming conferences' : all.length + ' upcoming conferences';
    $('searchBox').classList.toggle('has-text', !!S.q);
    updateTiles();
    if (focusKey) {
      var btn = host.querySelector('.m-head[data-key="' + focusKey + '"]');
      if (btn) { btn.focus({ preventScroll: true }); if (S.open === focusKey) btn.closest('.month').scrollIntoView({ block: 'start', behavior: reduceMotion() ? 'auto' : 'smooth' }); }
    }
  }
  function buildTiles() {
    $('filters').innerHTML = FILTERS.map(function (f) {
      return '<button type="button" class="tile" data-f="' + f.k + '" aria-haspopup="dialog">' +
        '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#5B2E9E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + f.icon + '</svg>' +
        '<span><b></b>' + CHEV_D + '</span></button>';
    }).join('');
  }
  function updateTiles() {
    FILTERS.forEach(function (f) {
      var t = document.querySelector('.tile[data-f="' + f.k + '"]'), v = S[f.k];
      var label = v ? (f.k === 'month' ? MONTHS[+v - 1] : v) : f.label;
      t.querySelector('b').textContent = label;
      t.classList.toggle('on', !!v);
      t.setAttribute('aria-label', f.label + ': ' + (v ? label : 'all') + '. Change filter');
    });
  }
  function persist() { lsSet({ year: S.year, month: S.month, city: S.city, spec: S.spec }); }

  /* ---------- filter sheet ---------- */
  var fs = { kind: null, opts: [] };
  function openFilter(kind) {
    var f = FILTERS.filter(function (x) { return x.k === kind; })[0];
    fs.kind = kind; fs.opts = options(kind);
    $('fsTitle').textContent = f.title;
    var find = $('fsFind'); find.value = ''; find.hidden = fs.opts.length <= 12;
    paintOpts('');
    var d = $('filterSheet'); if (!d.open) d.showModal();
  }
  function paintOpts(q) {
    var n = norm(q), sel = S[fs.kind];
    var rows = [{ value: '', label: 'All', count: null }].concat(fs.opts.filter(function (o) { return !n || norm(o.label).indexOf(n) >= 0; }));
    $('fsList').innerHTML = rows.map(function (o) {
      return '<li><button type="button" class="opt" data-v="' + esc(o.value) + '" aria-pressed="' + (sel === o.value) + '"><span>' + esc(o.label) + '</span>' + (o.count != null ? '<small>' + o.count + '</small>' : '') + '</button></li>';
    }).join('');
  }

  /* ---------- detail sheet ---------- */
  var detailFor = null;
  function openDetail(id) {
    var e = byId[id]; if (!e) return; detailFor = e;
    var chip = e.verification === 'Verified' ? '<span class="chip-v" style="position:static;display:inline-block">Verified</span>' : '<span class="chip-p" style="position:static;display:inline-block">Details pending</span>';
    var rows = [['Dates', e.dates || dateChip(e)], ['Location', place(e)]];
    if (e.society) rows.push(['Society', e.society]);
    rows.push(['Specialty', e.specialty]);
    if (e.format && e.format !== 'TBA') rows.push(['Format', e.format]);
    rows.push(['Status', verLabel(e)]);
    var lv = e.verified_on || e.verified; if (lv) rows.push(['Last verified', /^\d{4}-\d\d-\d\d$/.test(lv) ? longDate(lv) : lv]);
    var html = '<h4 class="d-title" id="dsTitle">' + esc(e.name) + '</h4>' + chip +
      '<dl class="d-rows">' + rows.map(function (r) { return '<dt>' + esc(r[0]) + '</dt><dd>' + esc(r[1]) + '</dd>'; }).join('') + '</dl>' +
      (e.notes ? '<div class="d-note">' + esc(e.notes) + '</div>' : '') +
      '<div class="d-actions">' +
      (e.url ? '<a class="btn primary" href="' + esc(e.url) + '" target="_blank" rel="noopener noreferrer">Open organizer site</a>' : '') +
      (e.precision === 'exact' ? '<button type="button" class="btn ghost" id="dsIcs">Add to calendar (.ics)</button>' : '') +
      '</div>';
    $('dsBody').innerHTML = html;
    $('detailSheet').showModal();
  }

  /* ---------- ICS (date-only all-day events, DTEND exclusive = end date + 1) ---------- */
  function icsEsc(s) { return String(s == null ? '' : s).replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n'); }
  function icsDate(s) { return s.replace(/-/g, ''); }
  function icsNext(s) { var p = ymd(s), d = new Date(Date.UTC(p.y, p.m - 1, p.d + 1)); return d.getUTCFullYear() + pad(d.getUTCMonth() + 1) + pad(d.getUTCDate()); }
  function fold(line) {
    var enc = new TextEncoder(), out = [], c = '', bytes = 0;
    Array.from(line).forEach(function (ch) {
      var n = enc.encode(ch).length;
      if (bytes + n > 75) { out.push(c); c = ' '; bytes = 1; }
      c += ch; bytes += n;
    });
    out.push(c); return out.join('\r\n');
  }
  function buildICS(list) {
    var d = new Date(), stamp = d.getUTCFullYear() + pad(d.getUTCMonth() + 1) + pad(d.getUTCDate()) + 'T' + pad(d.getUTCHours()) + pad(d.getUTCMinutes()) + pad(d.getUTCSeconds()) + 'Z';
    var L = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Brevista//Global CME Calendar//EN', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', 'X-WR-CALNAME:Brevista CME Calendar'];
    list.forEach(function (e) {
      L.push('BEGIN:VEVENT', 'UID:cme-' + e.id + '-' + e.start + '@global-cme-calendar', 'DTSTAMP:' + stamp,
        'DTSTART;VALUE=DATE:' + icsDate(e.start), 'DTEND;VALUE=DATE:' + icsNext(e.end || e.start), 'TRANSP:TRANSPARENT',
        'SUMMARY:' + icsEsc(e.name));
      if (place(e) !== 'Location TBA') L.push('LOCATION:' + icsEsc(e.location));
      L.push('DESCRIPTION:' + icsEsc(e.specialty + ' · ' + verLabel(e) + (e.url ? '\n' + e.url : '') + '\nConfirm dates with the organizer.'));
      if (e.url) L.push('URL:' + e.url);
      L.push('END:VEVENT');
    });
    L.push('END:VCALENDAR');
    return L.map(fold).join('\r\n') + '\r\n';
  }
  function download(name, text) {
    var blob = new Blob([text], { type: 'text/calendar;charset=utf-8' }), url = URL.createObjectURL(blob);
    var a = document.createElement('a'); a.href = url; a.download = name; document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(url); a.remove(); }, 4000);
  }
  window.__cmeBuildICS = buildICS; // for tests

  /* ---------- events ---------- */
  function setFilter(k, v) { S[k] = v; if (S.open === null) S.open = undefined; persist(); render(); }
  function resetAll() { S.q = ''; S.year = S.month = S.city = S.spec = ''; S.open = undefined; $('q').value = ''; persist(); render(); }
  function wire() {
    var t;
    $('q').addEventListener('input', function (ev) {
      clearTimeout(t); var v = ev.target.value;
      t = setTimeout(function () { S.q = v.trim(); if (S.open === null) S.open = undefined; render(); }, 60);
    });
    $('searchBox').addEventListener('click', function (ev) { if (ev.target.closest('.clear') == null) $('q').focus(); });
    $('clearQ').addEventListener('click', function () { $('q').value = ''; S.q = ''; render(); $('q').focus(); });
    $('heroSearch').addEventListener('click', function () { var q = $('q'); q.scrollIntoView({ block: 'center', behavior: reduceMotion() ? 'auto' : 'smooth' }); q.focus({ preventScroll: true }); });
    $('viewAll').addEventListener('click', resetAll);
    $('filters').addEventListener('click', function (ev) { var b = ev.target.closest('.tile'); if (b) openFilter(b.dataset.f); });
    $('months').addEventListener('click', function (ev) {
      var h = ev.target.closest('.m-head'), c = ev.target.closest('.card'), r = ev.target.closest('[data-reset]');
      if (h) { var k = h.dataset.key; S.open = S.open === k ? null : k; render(k); }
      else if (c) openDetail(c.dataset.id);
      else if (r) resetAll();
    });
    $('export').addEventListener('click', function () {
      var ex = cur.filter(function (e) { return e.precision === 'exact'; });
      if (ex.length) download('brevista-cme-calendar-' + today + '.ics', buildICS(ex));
    });
    $('fsList').addEventListener('click', function (ev) { var b = ev.target.closest('.opt'); if (!b) return; $('filterSheet').close(); setFilter(fs.kind, b.dataset.v); });
    $('fsFind').addEventListener('input', function (ev) { paintOpts(ev.target.value); });
    $('fsClose').addEventListener('click', function () { $('filterSheet').close(); });
    $('dsClose').addEventListener('click', function () { $('detailSheet').close(); });
    $('dsBody').addEventListener('click', function (ev) { if (ev.target.id === 'dsIcs' && detailFor) download('cme-' + detailFor.id + '-' + detailFor.start + '.ics', buildICS([detailFor])); });
    ['filterSheet', 'detailSheet'].forEach(function (id) {
      $(id).addEventListener('click', function (ev) { if (ev.target === ev.currentTarget) ev.currentTarget.close(); }); // backdrop tap
    });
  }

  function init(data) {
    meta = data; all = prepare(data.entries || []);
    var saved = lsGet();
    ['year', 'month', 'city', 'spec'].forEach(function (k) {
      var v = saved[k]; if (!v) return;
      if (options(k).some(function (o) { return o.value === String(v); })) S[k] = String(v);
    });
    buildTiles(); wire(); render();
    $('foot').textContent = 'Data compiled ' + (data.asOf || '') + ' · ' + (data.count || (data.entries || []).length) + ' conferences tracked. Dates and venues can change: confirm with the organizer before you book. Only conferences with confirmed dates are exported.';
  }
  function load() {
    $('months').innerHTML = '<div class="empty" role="status">Loading conferences…</div>';
    fetch('conferences.json').then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(init).catch(function () {
      $('months').innerHTML = '<div class="empty">Could not load the conference list.<br>Check your connection and try again.<br><button type="button" id="retry">Retry</button></div>';
      $('retry').addEventListener('click', load);
    });
  }
  load();
  if ('serviceWorker' in navigator && location.protocol.indexOf('http') === 0) {
    window.addEventListener('load', function () { navigator.serviceWorker.register('sw.js').catch(function () {}); });
  }
})();
