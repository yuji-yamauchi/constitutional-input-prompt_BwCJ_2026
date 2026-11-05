/* port.js - 参照用の受け口の面。fetch で /face/* を呼ぶだけ。
   字は textContent で入れる（HTML として解かない・書式を当てない）。端末の保存は使わない。 */
(function () {
  'use strict';

  /* ---- 文言表（字を変えない） ---- */
  var J = {
    'J-skip': '本文へスキップ',
    'J-01': '受け口（参照用）に ログイン',
    'J-02': 'この面は、受け口の係だけが 使います。本人の器では ありません。',
    'J-03': '合言葉',
    'J-04': 'ログインする',
    'J-05': 'しばらく操作がないと、自動でログアウトします（15分）。共有のパソコンで、つぎの人に 届いた写しを 見せないためです。',
    'J-06': '設定が ありません。',
    'J-07': 'ログインできませんでした。合言葉を たしかめてください。',
    'J-08': 'しばらく操作がなかったため、自動でログアウトしました。',
    'J-09': '合言葉を 入れてください。',
    'J-10': 'しばらく ログインできません。5分 たってから、もういちど ためしてください。',
    'J-11': 'いまは接続できません。時間をおいて、もういちどためしてください。',
    'J-12': '受け口（参照用）',
    'J-13': 'ここは 受け口です。本人の器では ありません。届いた 写しを 読み、人が 返事を 書きます。',
    'J-14': 'ログアウト',
    'J-15': { list: '受けた束', bundle: '束を読む', reply: '返事を書く' },
    'J-20': '受けた束',
    'J-21': '読み直す',
    'J-22': 'つなぐ合言葉を 出す',
    'J-23': 'よみこみ中…',
    'J-24': '受けた束は まだ ありません。',
    'J-25': 'よみこめませんでした。',
    'J-27': '（表示名なし）',
    'J-28': '新しい 200件だけを 出しています。',
    'J-29': { bundle: '束', items: '品目', fp: '指紋', replies: '返事' },
    'J-30': '束',
    'J-31': { sent: 'わたした時刻（器の時計）', recv: '受けた時刻（受け口の時計）' },
    'J-32': { id: '束の番号', fp: '指紋（受け口が計算した値）', count: '品目の数', receipt: '控えの番号' },
    'J-33': 'この束は 見つかりません。',
    'J-34': '意思表出文',
    'J-35': '最終版にした時刻',
    'J-36': { trouble: '困っていること', wish: 'のぞむこと', grounds: '根拠にする記録', statutes: '添える条文' },
    'J-37': { law_name: '法令名', article: '条番号', text_verbatim: '原文の写し', source_name: '取得元',
              retrieved_on: '取得日', retrieved_by: '取得した人（役）', set_version: '法令集の版' },
    'J-38': 'この束に 入っていない記録です。',
    'J-39': '名前なし',
    'J-40': '返事を書く',
    'J-41': '一覧に もどる',
    'J-42': 'この束への 返事',
    'J-43': 'まだ ありません。',
    'J-44': '原本',
    'J-47': { taken: '撮った時刻', fp: '原本の指紋' },
    'J-48': '大きく 見る',
    'J-50': '返事の相手',
    'J-51': '束の中身を ここで ひらく',
    'J-52': '返事の本文',
    'J-53': 'これは人が書きました',
    'J-54': '送った返事は 直せません。直したいときは、新しい返事を 書きます。前の返事も 残ります。',
    'J-55': '返事を送る',
    'J-56': '本文が 空です。',
    'J-57': '「これは人が書きました」を たしかめると 送れます。',
    'J-58': '4000字を こえています。',
    'J-59': '送っています…',
    'J-60': '返事を のこしました。本人が 器で 読み直すと 届きます。',
    'J-61': '送れませんでした。書いた字は そのままです。',
    'J-62': '束に もどる',
    'J-63': { title: '主語の欄', who: '誰が（役）', when: 'いつ', how: '何の手続きで' },
    'J-64': '未確認',
    'J-65': '作った時刻',
    'J-66': { title: '注記', time: '書いた時刻' },
    'J-67': { person: '本人', derived: 'Claude（派生）', mentor: 'メンター（人）', unknown: '不明' },
    'J-70': 'つなぐ合言葉',
    'J-71': '本人の器と この受け口を つなぐための、一度だけ 使える 合言葉を 作ります。本人に 手渡してください（画面を 見せる・口で 伝える・紙に 書く）。',
    'J-72': '合言葉を 作る',
    'J-74': 'この面を 閉じると、この合言葉は 二度と 出ません。',
    'J-75': '写す',
    'J-76': '写しました。',
    'J-77': '写せませんでした。字を 選んで 写してください。',
    'J-78': '作った 合言葉',
    'J-80': 'まだ ありません。',
    'J-81': '合言葉を 作れませんでした。',
    'J-82': 'とじる'
  };
  function j45(name) { return '原本の画像（' + name + '）'; }
  function j49(name) { return '原本（' + name + '）'; }
  function j73(t) { return '使えるのは 一度だけ。' + t + '（日本時間）まで。'; }
  function j26(t, name) { return t + '・' + name + '・束を読む'; }

  var IDLE_MS = 15 * 60 * 1000;
  var MAX_CHARS = 4000;
  var IMAGE_TYPES = { 'image/jpeg': 1, 'image/png': 1, 'image/webp': 1 };

  /* ---- 小さな道具 ---- */
  function $(id) { return document.getElementById(id); }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) { e.className = cls; }
    if (text !== undefined && text !== null) { e.textContent = String(text); }
    return e;
  }
  function add(parent) {
    for (var i = 1; i < arguments.length; i++) {
      if (arguments[i]) { parent.appendChild(arguments[i]); }
    }
    return parent;
  }
  function bdi(text) { return el('bdi', null, text); }
  function mono(text) { return el('span', 'mono', text); }
  function empty(node) { while (node.firstChild) { node.removeChild(node.firstChild); } }

  /* 日本時間の YYYY-MM-DD HH:MM。読めない字は空。 */
  function fmt(iso) {
    if (typeof iso !== 'string' || !iso) { return ''; }
    var d = new Date(iso);
    if (isNaN(d.getTime())) { return ''; }
    try {
      var parts = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
      }).formatToParts(d);
      var m = {};
      parts.forEach(function (p) { m[p.type] = p.value; });
      return m.year + '-' + m.month + '-' + m.day + ' ' + m.hour + ':' + m.minute;
    } catch (e) {
      return iso.slice(0, 16).replace('T', ' ');
    }
  }
  function jstIso(d) {
    var j = new Date(d.getTime() + 9 * 3600 * 1000);
    return j.toISOString().slice(0, 19) + '+09:00';
  }
  function chars(s) { return Array.from(s).length; }

  /* ---- 通信 ---- */
  function api(method, path, body) {
    var opt = { method: method, credentials: 'same-origin', cache: 'no-store', headers: {} };
    if (body !== undefined) {
      opt.headers['Content-Type'] = 'application/json';
      opt.body = JSON.stringify(body);
    }
    return fetch(path, opt).then(function (r) {
      return r.text().then(function (t) {
        var data = null;
        try { data = t ? JSON.parse(t) : null; } catch (e) { data = null; }
        return { status: r.status, data: data };
      });
    });
  }

  /* ---- 状態 ---- */
  var S = { view: 'boot', loggedIn: false, bundleId: null, bundle: null, attestedAt: null, sending: false, lockTimer: null };
  var idleTimer = null;
  var returnFocus = null;

  function applyStatic() {
    var nodes = document.querySelectorAll('[data-j]');
    Array.prototype.forEach.call(nodes, function (n) {
      var v = J[n.getAttribute('data-j')];
      if (typeof v === 'string') { n.textContent = v; }
    });
    $('pair-close').setAttribute('aria-label', J['J-82']);
    $('zoom-close').setAttribute('aria-label', J['J-82']);
  }

  /* ---- 画面の切り替え ---- */
  function show(view) {
    S.view = view;
    ['login', 'list', 'bundle', 'reply'].forEach(function (v) { $('v-' + v).hidden = (v !== view); });
    var names = J['J-15'];
    $('crumb').textContent = names[view] || '';
    $('btn-logout').hidden = (view === 'login');
    var focusTarget = null;
    if (view === 'list') { focusTarget = $('h-list'); }
    if (view === 'reply') { focusTarget = $('h-reply-ctx'); }
    if (view === 'login') { focusTarget = $('pw'); }
    if (focusTarget) { try { focusTarget.focus({ preventScroll: true }); } catch (e) { /* 何もしない */ } }
    window.scrollTo(0, 0);
  }

  /* 画面の中の字を全部消す（ログアウト・時間切れ） */
  function wipe() {
    empty($('list-rows'));
    $('list-status').textContent = '';
    $('list-more').hidden = true;
    empty($('bundle-body'));
    $('bundle-status').textContent = '';
    empty($('reply-ctx'));
    empty($('reply-fold-body'));
    $('reply-fold').open = false;
    resetReplyForm();
    closePair();
    closeZoom();
    S.bundle = null;
    S.bundleId = null;
  }

  function goLogin(timedOut) {
    S.loggedIn = false;
    stopIdle();
    wipe();
    $('login-timeout').hidden = !timedOut;
    $('login-err').hidden = true;
    $('pw').value = '';
    $('btn-login').disabled = false;
    show('login');
  }

  /* 401 が返ったら時間切れとして扱う */
  function expired(res) {
    if (res && res.status === 401 && S.loggedIn) { goLogin(true); return true; }
    return false;
  }

  /* ---- 無操作の時計 ---- */
  function resetIdle() {
    if (!S.loggedIn) { return; }
    if (idleTimer) { clearTimeout(idleTimer); }
    idleTimer = setTimeout(function () {
      api('POST', '/face/logout').then(function () {}, function () {});
      goLogin(true);
    }, IDLE_MS);
  }
  function stopIdle() { if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; } }
  ['click', 'keydown', 'scroll', 'touchstart', 'pointerdown'].forEach(function (ev) {
    window.addEventListener(ev, resetIdle, { capture: true, passive: true });
  });

  /* ---- 起動 ---- */
  function showUnconfigured() {
    stopIdle();
    document.body.setAttribute('data-state', 'unconfigured');
    empty(document.body);
    var p = el('p', 'unconfigured', J['J-06']);
    p.setAttribute('data-j', 'J-06');
    document.body.appendChild(p);
  }
  function showConnectError() {
    document.body.setAttribute('data-state', 'error');
    empty(document.body);
    document.body.appendChild(el('p', 'unconfigured', J['J-11']));
  }

  function boot() {
    applyStatic();
    api('GET', '/face/status').then(function (res) {
      if (!res.data || (res.status >= 500 && res.status !== 503)) { showConnectError(); return; }
      if (res.data.configured === false || res.status === 503) { showUnconfigured(); return; }
      document.body.setAttribute('data-state', 'ready');
      if (res.data.logged_in) {
        S.loggedIn = true;
        resetIdle();
        openList();
      } else {
        goLogin(false);
      }
    }, showConnectError);
  }

  /* ---- (a) ログイン ---- */
  function onLogin(ev) {
    ev.preventDefault();
    var pwEl = $('pw');
    var pw = pwEl.value;
    var errBox = $('login-err');
    errBox.hidden = true;
    $('login-timeout').hidden = true;
    if (pw === '') { errBox.textContent = J['J-09']; errBox.hidden = false; return; }
    var btn = $('btn-login');
    btn.disabled = true;
    api('POST', '/face/login', { passphrase: pw }).then(function (res) {
      pwEl.value = '';
      if (res.status === 200) {
        S.loggedIn = true;
        resetIdle();
        openList();
        return;
      }
      if (res.status === 503) { showUnconfigured(); return; }
      if (res.status === 423) {
        errBox.textContent = J['J-10'];
        errBox.hidden = false;
        if (S.lockTimer) { clearTimeout(S.lockTimer); }
        S.lockTimer = setTimeout(function () { btn.disabled = false; }, 5 * 60 * 1000);
        return;
      }
      errBox.textContent = (res.status === 401) ? J['J-07'] : J['J-11'];
      errBox.hidden = false;
      btn.disabled = false;
    }, function () {
      pwEl.value = '';
      errBox.textContent = J['J-11'];
      errBox.hidden = false;
      btn.disabled = false;
    });
  }

  function doLogout() {
    api('POST', '/face/logout').then(function () {}, function () {});
    goLogin(false);
  }

  /* ---- (b) 一覧 ---- */
  function openList() {
    wipeBundleOnly();
    show('list');
    var status = $('list-status');
    var rows = $('list-rows');
    empty(rows);
    $('list-more').hidden = true;
    status.textContent = J['J-23'];
    api('GET', '/face/bundles').then(function (res) {
      if (expired(res)) { return; }
      if (res.status !== 200 || !res.data) { status.textContent = J['J-25']; return; }
      var list = res.data.bundles || [];
      status.textContent = '';
      if (list.length === 0) { status.textContent = J['J-24']; return; }
      list.forEach(function (b) { rows.appendChild(listRow(b)); });
      $('list-more').hidden = !res.data.truncated;
    }, function () { status.textContent = J['J-25']; });
  }

  function listRow(b) {
    var btn = el('button', 'rec-item');
    btn.type = 'button';
    var name = b.display_name ? b.display_name : J['J-27'];
    var when = fmt(b.received_at);
    btn.setAttribute('aria-label', j26(when, name));
    var top = el('div', 'rec-title');
    top.appendChild(document.createTextNode(when + ' ／ '));
    top.appendChild(bdi(name));
    var w = J['J-29'];
    var meta = el('div', 'rec-meta');
    add(meta,
      add(el('span'), document.createTextNode(w.bundle + ' '), mono(String(b.bundle_id).slice(0, 8))),
      add(el('span'), document.createTextNode(w.items + ' ' + b.item_count)),
      add(el('span'), document.createTextNode(w.fp + ' '), mono(String(b.fingerprint).slice(0, 16))),
      add(el('span'), document.createTextNode(w.replies + ' ' + b.reply_count)));
    add(btn, top, meta);
    btn.addEventListener('click', function () { openBundle(b.bundle_id, false); });
    return btn;
  }

  function wipeBundleOnly() {
    empty($('bundle-body'));
    empty($('reply-ctx'));
    empty($('reply-fold-body'));
    $('reply-fold').open = false;
    resetReplyForm();
    S.bundle = null;
  }

  /* ---- (c) 束を読む ---- */
  function kv(label, valueNode) {
    var d = el('div', 'kv');
    add(d, el('span', 'k', label), valueNode);
    return d;
  }
  function plainNode(text) { return el('span', null, text); }
  function nameLine(name) { return add(el('div', 'kv'), bdi(name)); }

  function openBundle(id, showResult) {
    S.bundleId = id;
    wipeBundleOnly();
    show('bundle');
    var status = $('bundle-status');
    var body = $('bundle-body');
    empty(body);
    status.textContent = J['J-23'];
    api('GET', '/face/bundles/' + encodeURIComponent(id)).then(function (res) {
      if (expired(res)) { return; }
      if (res.status === 404) { status.textContent = J['J-33']; body.appendChild(backButton()); return; }
      if (res.status !== 200 || !res.data) { status.textContent = J['J-25']; body.appendChild(backButton()); return; }
      status.textContent = '';
      S.bundle = res.data;
      renderBundle(body, res.data, showResult);
    }, function () { status.textContent = J['J-25']; });
  }

  function backButton() {
    var row = el('div', 'btnrow');
    var b = el('button', 'btn btn-second', J['J-41']);
    b.type = 'button';
    b.addEventListener('click', openList);
    row.appendChild(b);
    return row;
  }

  function renderBundle(body, data, showResult) {
    var b = data.bundle || {};
    var sender = b.sender || {};
    var card = el('div', 'card');
    card.appendChild(el('h2', null, J['J-30']));
    var nm = sender.display_name ? sender.display_name : J['J-27'];
    card.appendChild(nameLine(nm));
    var t = J['J-31'];
    card.appendChild(kv(t.sent, plainNode(fmt(b.created_at))));
    card.appendChild(kv(t.recv, plainNode(fmt(data.received_at))));
    var n = J['J-32'];
    card.appendChild(kv(n.id, mono(String(b.bundle_id))));
    card.appendChild(kv(n.fp, mono(String(data.fingerprint))));
    card.appendChild(kv(n.count, plainNode(String((b.items || []).length))));
    card.appendChild(kv(n.receipt, mono(String(data.receipt_id))));
    var row = el('div', 'btnrow');
    var wr = el('button', 'btn btn-main', J['J-40']);
    wr.type = 'button';
    wr.addEventListener('click', openReply);
    var bk = el('button', 'btn btn-second', J['J-41']);
    bk.type = 'button';
    bk.addEventListener('click', openList);
    add(row, wr, bk);
    card.appendChild(row);
    body.appendChild(card);

    renderItems(body, b);

    var rcard = el('div', 'card');
    rcard.appendChild(el('h2', null, J['J-42']));
    var resultBox = null;
    if (showResult) {
      resultBox = el('div', 'note calm', J['J-60']);
      resultBox.setAttribute('role', 'status');
      rcard.appendChild(resultBox);
    }
    var reps = data.replies || [];
    if (reps.length === 0) {
      rcard.appendChild(el('p', 'small', J['J-43']));
    } else {
      reps.forEach(function (r) { rcard.appendChild(replyRow(r)); });
    }
    body.appendChild(rcard);
    if (resultBox) { nudgeIntoView(resultBox); }
  }

  /* 見えていれば動かない・見えなければ 1 回だけ寄せる */
  function nudgeIntoView(node) {
    var r = node.getBoundingClientRect();
    var h = window.innerHeight || document.documentElement.clientHeight;
    if (r.top < 0 || r.bottom > h) { node.scrollIntoView({ block: 'nearest' }); }
  }

  function tagClassFor(label) {
    if (label === J['J-67'].mentor || label.indexOf('人（') === 0) { return 'tag tag-mentor'; }
    return 'tag tag-unknown';
  }

  function replyRow(r) {
    var item = el('div', 'rec-item');
    var title = el('div', 'rec-title');
    var label = r.author_label || J['J-67'].unknown;
    add(title, el('span', null, fmt(r.written_at)), el('span', tagClassFor(label), label), mono(String(r.reply_id).slice(0, 8)));
    item.appendChild(title);
    item.appendChild(el('div', 'rec-text', r.text));
    return item;
  }

  /* 品目。items の順・欄の順を変えない。字のまま出す。 */
  function renderItems(container, bundle) {
    var items = Array.isArray(bundle.items) ? bundle.items : [];
    var recMap = {};
    var recNames = {};
    var statementGrounds = [];
    items.forEach(function (x) { if (x && x.kind === 'record') { recNames[x.item_id] = x.record_name; } });
    items.forEach(function (it) {
      if (it && it.kind === 'statement') {
        var c = statementCard(it, recNames, statementGrounds);
        container.appendChild(c);
      } else if (it && it.kind === 'record') {
        var rc = recordCard(it);
        recMap[it.item_id] = rc;
        container.appendChild(rc);
      }
    });
    // 根拠の釦は、全部の記録のカードが出来てから結ぶ
    statementGrounds.forEach(function (g) {
      g.btn.addEventListener('click', function () {
        var target = recMap[g.id];
        if (target) { target.scrollIntoView({ block: 'start' }); target.focus({ preventScroll: true }); }
      });
    });
  }

  function itemHead(titleText, tagText, tagCls, extraNodes) {
    var head = el('div', 'item-head');
    head.appendChild(el('h2', null, titleText));
    if (tagText !== null) { head.appendChild(el('span', tagCls, tagText)); }
    (extraNodes || []).forEach(function (n) { head.appendChild(n); });
    return head;
  }

  function sub(text, nodes) {
    var d = el('div', 'sub');
    d.appendChild(el('span', null, text));
    (nodes || []).forEach(function (n) { d.appendChild(n); });
    return d;
  }
  function longbox(text) { return el('div', 'longbox', text); }

  function statementCard(it, recNames, groundsOut) {
    var card = el('div', 'card');
    card.setAttribute('data-kind', 'statement');
    var fin = el('span', 'small', J['J-35'] + ' ' + fmt(it.finalized_at));
    card.appendChild(itemHead(J['J-34'], J['J-67'].person, 'tag tag-person', [fin]));
    card.appendChild(longbox(it.text));
    var sec = (it.sections && typeof it.sections === 'object') ? it.sections : {};
    var lab = J['J-36'];
    if (sec.trouble !== undefined && sec.trouble !== null) {
      card.appendChild(sub(lab.trouble));
      card.appendChild(longbox(sec.trouble));
    }
    if (sec.wish !== undefined && sec.wish !== null) {
      card.appendChild(sub(lab.wish));
      card.appendChild(longbox(sec.wish));
    }
    if (Array.isArray(sec.grounds)) {
      card.appendChild(sub(lab.grounds));
      var list = el('div', 'ground-list');
      sec.grounds.forEach(function (gid) {
        if (Object.prototype.hasOwnProperty.call(recNames, gid)) {
          var nm = recNames[gid] ? recNames[gid] : J['J-39'];
          var b = el('button', 'linkbtn body-size');
          b.type = 'button';
          b.appendChild(bdi(nm));
          list.appendChild(b);
          groundsOut.push({ id: gid, btn: b });
        } else {
          list.appendChild(el('span', 'small', J['J-38']));
        }
      });
      card.appendChild(list);
    }
    if (Array.isArray(sec.statutes)) {
      card.appendChild(sub(lab.statutes));
      sec.statutes.forEach(function (st) { card.appendChild(statuteBox(st || {})); });
    }
    return card;
  }

  function statuteBox(st) {
    var box = el('div', 'statute');
    var f = J['J-37'];
    ['law_name', 'article', 'text_verbatim', 'source_name', 'retrieved_on', 'retrieved_by', 'set_version'].forEach(function (k) {
      var v = (st[k] === undefined || st[k] === null) ? '' : st[k];
      if (k === 'text_verbatim') {
        box.appendChild(el('div', 'small', f[k]));
        box.appendChild(longbox(v));
      } else {
        box.appendChild(kv(f[k], bdi(v)));
      }
    });
    return box;
  }

  function recordCard(it) {
    var card = el('div', 'card');
    card.setAttribute('data-kind', 'record');
    card.tabIndex = -1;
    var parts = (it.parts && typeof it.parts === 'object') ? it.parts : {};
    var name = it.record_name ? it.record_name : J['J-39'];
    var sf = parts.subject_fields;
    var tagCls = (sf && sf.author_role) ? 'tag tag-other' : 'tag tag-unknown';
    var head = el('div', 'item-head');
    var h = el('h2');
    h.appendChild(bdi(name));
    head.appendChild(h);
    var tg = el('span', tagCls);
    if (sf && sf.author_role) { tg.appendChild(document.createTextNode('他者（')); tg.appendChild(bdi(sf.author_role)); tg.appendChild(document.createTextNode('）')); }
    else { tg.textContent = J['J-67'].unknown; }
    head.appendChild(tg);
    card.appendChild(head);

    if (parts.original) { card.appendChild(originalBlock(parts.original, name)); }
    if (sf) { card.appendChild(subjectBlock(sf)); }
    if (parts.derived) { card.appendChild(derivedBlock(parts.derived)); }
    if (Array.isArray(parts.annotations)) { card.appendChild(annotationsBlock(parts.annotations)); }
    return card;
  }

  function originalBlock(o, name) {
    var blk = el('div', 'blk');
    blk.appendChild(sub(J['J-44']));
    var mt = (typeof o.media_type === 'string') ? o.media_type : '';
    if (Object.prototype.hasOwnProperty.call(IMAGE_TYPES, mt) && typeof o.bytes_base64 === 'string') {
      var wrap = el('div', 'img-wrap');
      var imgBtn = el('button', 'img-btn');
      imgBtn.type = 'button';
      var img = document.createElement('img');
      img.alt = j45(name);
      img.src = 'data:' + mt + ';base64,' + o.bytes_base64;
      imgBtn.appendChild(img);
      imgBtn.addEventListener('click', function (ev) { openZoom(name, mt, o.bytes_base64, ev.currentTarget); });
      wrap.appendChild(imgBtn);
      blk.appendChild(wrap);
      var zb = el('button', 'linkbtn', J['J-48']);
      zb.type = 'button';
      zb.addEventListener('click', function (ev) { openZoom(name, mt, o.bytes_base64, ev.currentTarget); });
      blk.appendChild(zb);
    } else {
      var p = el('p', 'small');
      p.appendChild(document.createTextNode('この形式は、この面では 表示しません（形式: '));
      p.appendChild(bdi(mt));
      p.appendChild(document.createTextNode('）。'));
      blk.appendChild(p);
    }
    var lab = J['J-47'];
    if (o.taken_at) { blk.appendChild(kv(lab.taken, plainNode(fmt(o.taken_at)))); }
    blk.appendChild(kv(lab.fp, mono(String(o.sha256 || '').slice(0, 16))));
    return blk;
  }

  function subjectBlock(sf) {
    var blk = el('div', 'blk');
    var lab = J['J-63'];
    var extra = [];
    if (sf.confirmed_by_person === false) { extra.push(el('span', 'tag tag-unconfirmed', J['J-64'])); }
    blk.appendChild(sub(lab.title, extra));
    blk.appendChild(kv(lab.who, bdi(sf.author_role === undefined ? '' : sf.author_role)));
    blk.appendChild(kv(lab.when, bdi(sf.written_at === undefined ? '' : sf.written_at)));
    blk.appendChild(kv(lab.how, bdi(sf.procedure === undefined ? '' : sf.procedure)));
    return blk;
  }

  function derivedBlock(d) {
    var blk = el('div', 'blk');
    blk.appendChild(sub(d.label, [el('span', 'tag tag-derived', J['J-67'].derived)]));
    blk.appendChild(kv(J['J-65'], plainNode(fmt(d.generated_at))));
    blk.appendChild(longbox(d.markdown));
    return blk;
  }

  function annotationsBlock(list) {
    var blk = el('div', 'blk');
    var lab = J['J-66'];
    blk.appendChild(sub(lab.title));
    list.forEach(function (a) {
      var item = el('div', 'rec-item');
      var title = el('div', 'rec-title');
      add(title, el('span', 'tag tag-person', J['J-67'].person), el('span', 'small', lab.time + ' ' + fmt(a.written_at)));
      item.appendChild(title);
      item.appendChild(longbox(a.text));
      blk.appendChild(item);
    });
    return blk;
  }

  /* ---- 原本を大きく見る面 ---- */
  function openZoom(name, mt, b64, opener) {
    returnFocus = opener || null;
    var title = $('zoom-title');
    title.textContent = '';
    title.appendChild(document.createTextNode('原本（'));
    title.appendChild(bdi(name));
    title.appendChild(document.createTextNode('）'));
    var body = $('zoom-body');
    empty(body);
    var img = document.createElement('img');
    img.className = 'zoom-img';
    img.alt = j45(name);
    img.src = 'data:' + mt + ';base64,' + b64;
    body.appendChild(img);
    $('modal-zoom').hidden = false;
    $('zoom-close').focus();
  }
  function closeZoom() {
    if ($('modal-zoom').hidden) { return; }
    $('modal-zoom').hidden = true;
    empty($('zoom-body'));
    restoreFocus();
  }
  function restoreFocus() {
    if (returnFocus && document.contains(returnFocus)) { try { returnFocus.focus(); } catch (e) { /* 何もしない */ } }
    returnFocus = null;
  }

  /* ---- (d) 返事を書く ---- */
  function resetReplyForm() {
    $('reply-text').value = '';
    $('reply-attest').checked = false;
    S.attestedAt = null;
    S.sending = false;
    $('reply-err').hidden = true;
    $('btn-send').textContent = J['J-55'];
    updateReplyState();
  }

  function replyState() {
    var text = $('reply-text').value;
    var blank = text.trim() === '';
    var checked = $('reply-attest').checked;
    var over = chars(text) > MAX_CHARS;
    return { blank: blank, checked: checked, over: over, ok: (!blank && checked && !over) };
  }
  function updateReplyState() {
    var s = replyState();
    var box = $('reply-reasons');
    empty(box);
    if (s.blank) { box.appendChild(el('div', null, J['J-56'])); }
    if (!s.checked) { box.appendChild(el('div', null, J['J-57'])); }
    if (s.over) { box.appendChild(el('div', null, J['J-58'])); }
    $('btn-send').disabled = !(s.ok && !S.sending);
  }

  function openReply() {
    var data = S.bundle;
    if (!data) { return; }
    resetReplyForm();
    show('reply');
    var b = data.bundle || {};
    var ctx = $('reply-ctx');
    empty(ctx);
    var sender = b.sender || {};
    var nm = sender.display_name ? sender.display_name : J['J-27'];
    var n = J['J-32'];
    ctx.appendChild(nameLine(nm));
    ctx.appendChild(kv(n.id, mono(String(b.bundle_id).slice(0, 8))));
    ctx.appendChild(kv(J['J-31'].recv, plainNode(fmt(data.received_at))));
    ctx.appendChild(kv(n.count, plainNode(String((b.items || []).length))));
    empty($('reply-fold-body'));
    $('reply-fold').open = false;
    $('reply-fold').dataset.loaded = '';
  }

  function onFoldToggle() {
    var fold = $('reply-fold');
    if (!fold.open || fold.dataset.loaded === '1' || !S.bundle) { return; }
    fold.dataset.loaded = '1';
    renderItems($('reply-fold-body'), S.bundle.bundle || {});
  }

  function onAttestChange() {
    S.attestedAt = $('reply-attest').checked ? jstIso(new Date()) : null;
    updateReplyState();
  }

  function onSend() {
    var s = replyState();
    if (!s.ok || S.sending) { return; }
    S.sending = true;
    var btn = $('btn-send');
    btn.disabled = true;
    btn.textContent = J['J-59'];
    var errBox = $('reply-err');
    errBox.hidden = true;
    var text = $('reply-text').value;
    var attestedAt = S.attestedAt || jstIso(new Date());
    var id = S.bundleId;
    api('POST', '/face/bundles/' + encodeURIComponent(id) + '/replies',
        { text: text, human_attestation: true, attested_at: attestedAt }).then(function (res) {
      if (expired(res)) { return; }
      S.sending = false;
      btn.textContent = J['J-55'];
      if (res.status === 201) {
        resetReplyForm();
        openBundle(id, true);
        return;
      }
      failSend();
    }, function () {
      S.sending = false;
      btn.textContent = J['J-55'];
      failSend();
    });
  }
  function failSend() {
    var errBox = $('reply-err');
    errBox.textContent = J['J-61'];
    errBox.hidden = false;
    $('reply-attest').checked = false;   // 送り直すときに、もう一度 人が確かめる
    S.attestedAt = null;
    updateReplyState();
  }

  function leaveReplyToBundle() {
    resetReplyForm();
    show('bundle');
  }

  /* ---- (e) つなぐ合言葉 ---- */
  var pairCode = null;

  function openPair(ev) {
    returnFocus = ev && ev.currentTarget ? ev.currentTarget : null;
    resetPair();
    $('modal-pair').hidden = false;
    $('pair-close').focus();
    loadPairList();
  }
  function resetPair() {
    pairCode = null;
    $('pair-code').textContent = '';
    $('pair-result').hidden = true;
    $('pair-err').hidden = true;
    $('pair-copy-msg').textContent = '';
    $('pair-expiry').textContent = '';
    $('btn-pair-make').disabled = false;
    empty($('pair-list'));
  }
  function closePair() {
    if ($('modal-pair').hidden) { return; }
    resetPair();
    $('modal-pair').hidden = true;
    restoreFocus();
  }
  function makePair() {
    var btn = $('btn-pair-make');
    btn.disabled = true;
    $('pair-err').hidden = true;
    api('POST', '/face/pairings').then(function (res) {
      if (expired(res)) { return; }
      if (res.status !== 201 || !res.data || !res.data.code) {
        var e = $('pair-err');
        e.textContent = J['J-81'];
        e.hidden = false;
        btn.disabled = false;
        return;
      }
      pairCode = res.data.code;
      $('pair-code').textContent = pairCode;
      $('pair-expiry').textContent = j73(fmt(res.data.expires_at));
      $('pair-copy-msg').textContent = '';
      $('pair-result').hidden = false;
      loadPairList();
    }, function () {
      var e = $('pair-err');
      e.textContent = J['J-81'];
      e.hidden = false;
      btn.disabled = false;
    });
  }
  function loadPairList() {
    var box = $('pair-list');
    api('GET', '/face/pairings').then(function (res) {
      if (expired(res)) { return; }
      empty(box);
      var rows = (res.status === 200 && res.data && res.data.pairings) ? res.data.pairings : [];
      if (rows.length === 0) { box.appendChild(el('p', 'small', J['J-80'])); return; }
      rows.forEach(function (r) {
        var item = el('div', 'rec-item');
        var title = el('div', 'rec-title');
        add(title, el('span', null, fmt(r.created_at)), el('span', 'small', r.status));
        item.appendChild(title);
        box.appendChild(item);
      });
    }, function () { /* 一覧が読めなくても面は使える */ });
  }
  function copyPair() {
    var msg = $('pair-copy-msg');
    if (!pairCode) { return; }
    var done = function () { msg.textContent = J['J-76']; };
    var fail = function () {
      msg.textContent = J['J-77'];
      try {
        var r = document.createRange();
        r.selectNodeContents($('pair-code'));
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(r);
      } catch (e) { /* 何もしない */ }
    };
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(pairCode).then(done, fail);
      } else { fail(); }
    } catch (e) { fail(); }
  }

  /* ---- 面の共通: Esc・背景・Tab の輪 ---- */
  function bindModal(overlayId, closeFn, closeBtnId) {
    var ov = $(overlayId);
    ov.addEventListener('click', function (ev) { if (ev.target === ov) { closeFn(); } });
    $(closeBtnId).addEventListener('click', closeFn);
  }
  document.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') {
      if (!$('modal-zoom').hidden) { closeZoom(); return; }
      if (!$('modal-pair').hidden) { closePair(); return; }
    }
    if (ev.key === 'Tab') {
      var open = !$('modal-zoom').hidden ? $('modal-zoom') : (!$('modal-pair').hidden ? $('modal-pair') : null);
      if (!open) { return; }
      var f = open.querySelectorAll('button:not([disabled])');
      if (f.length === 0) { return; }
      var first = f[0], last = f[f.length - 1];
      if (ev.shiftKey && document.activeElement === first) { ev.preventDefault(); last.focus(); }
      else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
    }
  });

  /* ---- 結ぶ ---- */
  function wire() {
    $('login-form').addEventListener('submit', onLogin);
    $('btn-logout').addEventListener('click', doLogout);
    $('btn-refresh').addEventListener('click', openList);
    $('btn-pair').addEventListener('click', openPair);
    $('btn-pair-make').addEventListener('click', makePair);
    $('btn-pair-copy').addEventListener('click', copyPair);
    bindModal('modal-pair', closePair, 'pair-close');
    bindModal('modal-zoom', closeZoom, 'zoom-close');
    $('reply-text').addEventListener('input', updateReplyState);
    $('reply-attest').addEventListener('change', onAttestChange);
    $('btn-send').addEventListener('click', onSend);
    $('btn-reply-back').addEventListener('click', leaveReplyToBundle);
    $('reply-fold').addEventListener('toggle', onFoldToggle);
  }

  var started = false;
  function start() { if (started) { return; } started = true; wire(); boot(); }
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', start); } else { start(); }
})();
