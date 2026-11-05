/* app.js - 器の画面。外への通信は自分の配信元の /api だけ。
   字は textContent で入れる（HTML として解かない）。差し込む字は bdi で包む。
   端末の保存は画面の設定 5 つ（左を畳んだか・右を畳んだか・右の幅・右の選び・③の「いっしょに いる 人」の切替）だけ。 */
/* 置き物の絵（キャラの絵と名）の入り切り。false にすると絵も名の字も全部出ない（body に data-figures="0" が付き、CSS でも隠す）。 */
var BRAND_FIGURES = true;

(function () {
  'use strict';

  /* ================================================================
     文言表（番号は data-w に残す。字は替えない）
     ================================================================ */
  var noteKako = '過去のことを話す義務はありません。話したいときだけ、話したいことだけ。話さなくても、この先の準備には何も欠けません。';
  var DERIVED_LABEL = '派生（Claude が読み取った写し。原本が正）';

  var W = {
    'W-01': 'Constitutional Input Prompt',
    'W-02': '自己の意思表出としてのプロンプトを。誰もが立てる場所を、ここに。',
    'W-03': 'しばらく操作がなかったため、あなたの記録を守るために自動でログアウトしました。',
    'W-05': '合言葉',
    'W-06': 'ログインする',
    'W-07': '合言葉は、この器を用意した人から受け取ります。',
    'W-08': '※この画面は、しばらく操作がないと自動でログアウトします（15分）。見はるためではありません。共有のパソコンで、つぎの人に あなたの記録を見せないためです。',
    'W-09': 'いまは接続できません。時間をおいて、もういちどためしてください。',
    'W-10': '合言葉を 入れてください。',
    'W-11': 'ログインできませんでした。合言葉を たしかめてください。',
    'W-23': '画面を読み直す',
    'W-24': 'チャットを開く',
    'W-26': '左の帯を とじる・ひらく',
    'W-27a': 'ログイン中',
    'W-28a': 'ログアウト',
    'W-29': 'v0.3.2 / 2026-11-06',
    'W-31': '本文へスキップ',
    'W-32a': 'れんしゅう',
    'W-32b': 'じぶんの記録',
    'W-32c': 'まとめる・わたす',
    'N-home': 'ホーム',
    'N-renshu': '書く れんしゅう',
    'N-hikidashi': '自分の記録（引き出し）',
    'N-kiroku': '記録の一覧・書き出す・けす',
    'N-seiri': 'いまの のぞみを まとめる',
    'N-watasu': '人に わたす',
    'PROMISE-LINK': '器の約束',
    'DEMO': 'この入口の応答は 録画用に記録した物です',
    'DEMO-PLACEHOLDER': 'この入口の応答は 仮の物です（Claude を 呼んでいません。どの入力にも 同じ字が 返ります）',
    'UNCONF': '設定が ありません。',
    'W-40': 'きょうの気分',
    'W-41': 'きょうは、どんな気分？',
    'W-42': 'Claude から話しかけることは ありません。よぶのは、あなたです。',
    'W-43': '（えらばなくても だいじょうぶ）',
    'W-46': '器の約束を読む',
    'W-47': 'はじめる',
    'W-48': '一度に 書く量',
    'W-49': '今日はしない',
    'W-60': 'こんにちは。',
    'W-61a': 'あなたの記録は、あなたのものです。',
    'W-61b': ' なにをつかうか、なにをのこすかは、あなたがきめます。',
    'W-62': 'とどいた返事',
    'W-63': 'とどいた返事は ありません。',
    'W-64': '聞き役の しくみに いま つながりません。',
    'W-70': 'これは、ほかの人が あなたについて 書いた記録の 写しです。原本（写真）が 正です。',
    'W-80': '記録の一覧',
    'W-81': 'ここにあるのは、あなたが のこしたものと、あなたが 入れたものだけです。数は、あったことの 数です。',
    'W-82': 'のこしたやりとり （聞き役との やりとりで、あなたが のこすと きめたもの）',
    'W-83': 'まだ ありません。',
    'W-84': 'ひらくとよみこみます…',
    'W-85': 'よみこめませんでした。',
    'W-86': 'じかんの流れ （器の中の記録を、時間の順に）',
    'W-87': 'あなたの器の中の記録を、時間の順に ならべます。見えるのは あなただけです。',
    'W-90': '書き出す・けす',
    'W-91': 'あなたの器の中身（写真の原本・写し・注記・主語の欄・印と条件・意思表出文・控え・返事）を、いつでも ぜんぶ 手もとに 書き出せます。',
    'W-92': 'ぜんぶ書き出す',
    'W-93': '器の中身をけす',
    'W-94': 'ほんとうに けす（もどせません）',
    'W-94b': 'けしました',
    'W-95': '「けす」で消えるのは、あなたの器の中身です。人に わたした 写しは、ここからは 消えません。控えを のこすかは、けす前に えらべます。',
    'W-100': '自分の記録（引き出し） （ほかの人が あなたについて 書いた記録）',
    'W-101': '写真で 入れた記録は、あなたの器に のこります。写真を 入れずに「なにを・どこに 持っているか」だけ 控えることも できます。',
    'W-102': '記録の名前（例：通知表）',
    'W-103': 'ある場所（例：家のファイル）',
    'W-104': 'メモ（任意）',
    'W-105': '控えに たす',
    'W-106': '写真なしの 控え',
    'W-107': 'まだ ありません。',
    'W-108': 'この行をけす',
    'W-120': '聞き役との やりとり',
    'W-121': '下の えらぶところで、書く れんしゅう・いまの のぞみの まとめ・過去のことを 話す場 を きりかえます。見えるのは、あなただけです。',
    'W-122': '見る やりとりを えらぶ',
    'W-123a': '書く れんしゅう',
    'W-123b': 'いまの のぞみを まとめる',
    'W-123c': '過去のことを 話す場',
    'W-124': 'チャットの枠を とじる・ひらく',
    'W-125': { renshu: '書く れんしゅう', seiri: 'いまの のぞみを まとめる', kako: '過去のことを 話す場' },
    'W-126': 'このやりとりが見える人: あなただけ。',
    'W-130': 'ここに 書きます（Alt+Enterで送信）',
    'W-131a': 'チャットだけ表示しています',
    'W-131b': '本文を出す',
    'W-132': 'ドラッグで幅をかえる',
    'W-133': '…かんがえています',
    'W-134': '送信',
    'W-136': '聞き役の Claude に 送ります。のこすかどうかは、おわるときに あなたが きめます。',
    'W-138': '※ Claude は、あなたの文を そのまま 読み返し、問いを 返すだけです。書きかえ・助言は しません。',
    'W-139': 'まだ やりとりは ありません。',
    'W-141': 'Claude（聞き役）',
    'W-142': 'つながりませんでした。すこし待って、もういちどためせます。',
    'W-151': '見える人について',
    'W-152': 'このやりとりは、あなただけが 見られます。人に 見せたいときは「人に わたす」から、えらんだ物の 写しを わたします。わたしても、ここの中身は 動きません。',
    'W-153': 'ここに 書いた字は、送信の釦を 押したときに、聞き役の Claude に 送られます。',
    'W-160': '器の約束（Claude への 指示の 全文）',
    'W-161': 'これは 聞き役の Claude に わたしている 指示の 全文です。あなたに かくれて 別の指示が うごくことは ありません。',
    'W-162a': '版: ',
    'W-162b': ' ・ 決めた日: ',
    'W-163': '指示の 全文を いま 読みこめません。',
    'W-171': 'とじる',
    'W-172': 'いっしょに いる 人が います'
  };

  /* 文言表に無い字（仮置き） */
  var L = {
    gateBlank: W['W-10'],
    readerLabels: { reader: '写真を 文字に 写す役', listener: '聞き役', arranger: '並べ役' },
    condGroups: [
      { key: 'amount', label: '一度に 書く量', opts: ['すくなめ', 'ふつう', 'おおめ'] },
      { key: 'split', label: '区切り方', opts: ['区切らない', '文ごと', '段ごと'] },
      { key: 'ease', label: 'ことばの やさしさ', opts: ['やさしい', 'ふつう'] },
      { key: 'length', label: '長さ', opts: ['みじかく', 'ながく'] },
      { key: 'input', label: '入力の形', opts: ['文字', 'えらぶ形の たすけ'], soon: '声から文字（じゅんび中）' }
    ],
    condShort: { amount: '量', split: '区切り', ease: 'やさしさ', length: '長さ', input: '入力' },
    moods: [
      { name: 'すこしずつ 区切って', role: '書き方の条件の組', desc: '一度に 書く量を すくなく、区切りを 入れます。', patch: { amount: 'すくなめ', split: '文ごと' }, amount: 'すくなめ' },
      { name: 'やさしい ことばで', role: '書き方の条件の組', desc: '問いの ことばを やさしく します。', patch: { ease: 'やさしい' }, amount: 'ふつう' },
      { name: 'えらぶ形で たすけて', role: '書き方の条件の組', desc: 'えらぶ形の たすけを 使います。', patch: { input: 'えらぶ形の たすけ' }, amount: 'ふつう' },
      { name: 'いつもの まま', role: '書き方の条件の組', desc: '条件を 変えません。', patch: {}, amount: 'ふつう' }
    ],
    doRead: 'ここで 止める',
    keepGoing: 'つづける',
    contOrStop: 'つづけますか。 ここで 止めますか。',
    yourText: 'あなたの文',
    marks: [['残った', '残った'], ['一部', '一部'], ['残らなかった', '残らなかった'], ['なし', '印を つけない']],
    markDone: function (mark, cond) { return mark === 'なし' ? '印を のこしました（印なし・' + cond + '）。' : '印を のこしました（' + mark + '・' + cond + '）。'; },
    markFail: '印を のこせませんでした。もういちど ためせます。',
    keepAsk: 'この やりとりを のこしますか。',
    keepNo: 'のこさない',
    keepYes: 'のこす',
    keepYesSoon: 'のこす 機能は、いまは まだ 使えません。',
    noKey: '鍵が 設定されていません。',
    kakoLocal: 'ここに 書いた字は、Claude には 送られません。この画面の中だけに あります。',
    kakoEnd: 'おわる',
    kakoAsk: 'いまの 話を、あなたの記録に のこしますか？',
    seiriState: '書いた字は「困っていること」の 欄に 足されます。Claude へは 送られません。',
    seiriAdded: '「困っていること」の 欄に 足しました。',
    seiriGo: 'まとめの 画面へ',
    arrangeBtn: 'Claude に 並べて もらう',
    stAdopt: '添える',
    conditionsTitle: '書き方の条件',
    countsTitle: '条件ごとの 回数',
    countsNote: '数は、あったことの 数です。あなたに 数は つきません。',
    noPhoto: '写真なしで 控える',
    colMarks: ['残った', '一部', '残らなかった'],
    chooseFile: '写真を えらぶ・撮る',
    insertTitle: '記録を 入れる',
    insertedTitle: '入れた 記録',
    sendConfirm: 'この写真を 読み取るため Claude に 送ります。送らずに 保存だけも できます。',
    sendDo: '送って 読み取る',
    saveOnly: '保存だけに する',
    cancel: 'やめる',
    badType: 'この形の写真は 入れられません。',
    tooBig: '5 MB を こえています。',
    savedOnly: '保存しました（原本だけ）。',
    savedAndRead: '保存しました。写しも できました。',
    savedNoRead: '保存しました。写しは 作れませんでした。',
    readyName: '記録の名前',
    unnamed: '名前なし',
    viewOrig: '原本を 見る',
    viewDerived: '写しを 見る',
    redo: '写しを 作り直す',
    delDerived: '写しを けす',
    delRecord: 'この記録を けす',
    askDel: 'ほんとうに けす（もどせません）',
    addNote: '注記を たす',
    addNoteDo: 'たす',
    subjTitle: '主語の欄',
    subjWho: '誰が（役）',
    subjWhen: 'いつ',
    subjHow: '何の手続きで',
    subjEdit: '主語の欄を 入れる・直す',
    subjKeep: 'ひかえる',
    subjOk: 'これで あっている',
    unconfirmed: '未確認',
    origFp: '原本の指紋',
    noteTag: '本人',
    tagDerived: 'Claude（派生）',
    tagMentor: 'メンター（人）',
    tagUnknown: '不明',
    tagPerson: '本人',
    bindDo: '記録に 綴じる',
    discardDo: '捨てる',
    askDiscard: 'ほんとうに 捨てる（もどせません）',
    reread: '読み直す',
    promiseDoes: ['問いを 返す', 'あなたの文を 一字も 変えずに 読み返す', '「続けますか・ここで止めますか」を きく', '写真を 文字に 写す（あなたが 送ると 決めたときだけ）', '法令集の 中から 条文の 候補を 原文のまま 出す（いまの のぞみを まとめる ときだけ）'],
    promiseDoesnt: ['書きかえ', 'まとめ直し・言いかえ', 'よしあしを 決めること・段を つけること', 'あなたについての 見立て', '助言・はげましの 文', '条文が あなたに 当てはまるかを 言うこと', '体や こころの ことの 助言', 'あなたの記録を 書きかえること', '印や 回数に さわること', '返事を 書くこと'],
    promiseSendTitle: '送る前に 見えます',
    promiseSend: '写真を Claude に送る前に、送る物と「送らない」選びを 出します。チャットに 書いた字は、送信の釦を 押したときだけ 送られます。',
    promiseDoesTitle: 'Claude が すること',
    promiseDoesntTitle: 'Claude が しないこと',
    promiseFullTitle: '指示の全文',
    exportDone: '書き出しました。',
    exportFail: '書き出せませんでした。',
    exportSave: '手もとに 保存する',
    countLabels: { originals: '原本', derived: '写し', annotations: '注記', subject_fields: '主語の欄', marks: '印', statements: '意思表出文', handoffs: '控え', replies: '返事' },
    keepReceipts: '控えを のこす',
    dropReceipts: '控えを のこさない',
    claudeTitle: 'Claude に 送ったもの',
    claudeKinds: { reader: '写真の読み取り', listener: '聞き役のやりとり', arranger: '並べる' },
    timelineTitle: 'ぜんぶの記録（時間の順）',
    kinds: { record: '記録', note: '注記', reply: '返事', statement: '意思表出文', handoff: '控え' },
    saved: 'ひかえました。',
    pairTitle: 'つなぐ',
    pairLabel: '受け口の合言葉',
    pairDo: 'つなぐ',
    pairFail: 'つなげませんでした。合言葉を たしかめてください。',
    pairedWith: 'つないでいる 受け口',
    notPaired: 'まだ つないでいません。',
    chooseTitle: 'わたす物を えらぶ',
    checkTitle: 'わたす前に たしかめる',
    giveDo: 'わたす',
    giveNote: 'わたすのは 写しです。あなたの器の 中身は 動きません。',
    giveAt: 'この束の 日時',
    needStmt: '最終版の 意思表出文を えらんでください。',
    giveFail: 'わたせませんでした。器の中身は そのままです。',
    giveDone: 'わたしました。この束の 指紋は、下の 控えの 指紋と 同じです。つぎの束は、わたす物を えらびなおすと 作られます。',
    giveTo: '送り先',
    giveNone: 'わたす物が まだ えらばれていません。',
    stmtFinal: '意思表出文（最終版）',
    receiptTitle: '控え',
    receiptNo: '控えの番号',
    receiptAt: '受けた日時',
    receiptFp: '束の指紋',
    receiptPort: '受け口の名',
    same: '同じ',
    diff: '控えの指紋が 束の指紋と ちがいます。',
    pastTitle: 'わたした 控え',
    pastItems: '中身の数',
    partNames: { original: '原本', derived: '写し', subject_fields: '主語の欄', annotations: '注記' },
    stTitle: '意思表出文',
    stTrouble: '困っていること',
    stWish: 'のぞむこと',
    stGrounds: '根拠にする 記録',
    stStatutes: '添える 条文',
    drop: '外す',
    stDrop: 'この欄を 外す',
    stRestore: '外した欄を もどす',
    stPickRecords: '記録を えらぶ',
    stPickLaws: '条文を えらぶ',
    stSave: 'ひかえる',
    stDraftTag: '案',
    stFinal: 'これを 最終版に する',
    stFinalTitle: '最終版',
    stFinalDone: '最終版に しました。',
    stArrangeConfirm: 'Claude に 送る物',
    stSendDo: 'この内容で 送る',
    stNoSend: '送らない',
    stDropped: '法令集の 原文と 一致しなかったので、出しません。',
    stPrev: 'これまでの 意思表出文',
    stNew: '新しく まとめる',
    stOpen: 'ひらく',
    lawSource: '出典',
    lawName: '法令名',
    lawArticle: '条番号',
    lawText: '原文の写し',
    lawSrcName: '取得元',
    lawOn: '取得日',
    lawBy: '取得した人',
    lawVer: '法令集の版',
    lawNone: '法令集に 条文が ありません。',
    lawAttach: '添える',
    done: 'とじる',
    arrangeFail: '案を 出せませんでした。'
  };

  /* ================================================================
     小さな道具
     ================================================================ */
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
  function clear(node) { while (node.firstChild) { node.removeChild(node.firstChild); } }
  function btn(label, cls, fn) {
    var b = el('button', 'btn ' + (cls || ''), label);
    b.type = 'button';
    if (fn) { b.addEventListener('click', fn); }
    return b;
  }
  function linkbtn(label, fn, cls) {
    var b = el('button', 'linkbtn' + (cls ? ' ' + cls : ''), label);
    b.type = 'button';
    if (fn) { b.addEventListener('click', fn); }
    return b;
  }
  function tag(text, kind) { return el('span', 'tag tag-' + kind, text); }
  function line(text, cls) { return el('p', cls || 'empty', text); }
  function listOf(x) {
    if (Array.isArray(x)) { return x; }
    if (x && typeof x === 'object') {
      var keys = ['items', 'records', 'statements', 'law', 'laws', 'handoffs', 'replies'];
      for (var i = 0; i < keys.length; i++) { if (Array.isArray(x[keys[i]])) { return x[keys[i]]; } }
    }
    return [];
  }
  function later(fn, ms) { return setTimeout(fn, ms); }
  function lsGet(k) { try { return window.localStorage.getItem(k); } catch (e) { return null; } }
  /* ---- ブランド層: 置き物の絵（背景の絵＋名の字）と nav の小さな絵 ---- */
  var FIG_NAMES = { teku: 'てくちゃん', kiro: 'きろちゃん', koto: 'ことちゃん', mana: 'まなちゃん' };
  function figure(who, sizeCls) {
    if (!BRAND_FIGURES) { return null; }
    var f = el('div', 'figure fig-' + who + ' ' + sizeCls);
    var img = el('span', 'fig-img'); img.setAttribute('aria-hidden', 'true');
    f.appendChild(img);
    f.appendChild(el('span', 'fig-name', FIG_NAMES[who]));
    return f;
  }
  /* 見た目の層: ②③の場面と札（背景の絵だけ・字なし）。kind=02/03, state=empty|filled|seat-empty|seat-taken */
  function board(kind, state, sizeCls) {
    if (!BRAND_FIGURES) { return null; }
    var b = el('div', 'board board-' + kind + '-' + state + ' ' + sizeCls);
    b.setAttribute('aria-hidden', 'true');
    b.appendChild(el('span', 'board-img'));
    return b;
  }
  function emptyWithFigure(who, sizeCls, text) {
    var p = line(text);
    var f = figure(who, sizeCls);
    if (!f) { return p; }
    var row = el('div', 'empty-fig');
    add(row, f, p);
    return row;
  }
  var SVG_HEAD = '<svg viewBox="0 0 20 20" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">';
  var NAV_ICONS = {
    home: '<circle cx="10" cy="10" r="3.6" fill="#FDEFC4"/><path d="M10 2.2v2M10 15.8v2M2.2 10h2M15.8 10h2M4.5 4.5l1.4 1.4M14.1 14.1l1.4 1.4M15.5 4.5l-1.4 1.4M5.9 14.1l-1.4 1.4"/>',
    renshu: '<rect x="3.5" y="3" width="10" height="14" rx="2" fill="#D6EBF8"/><path d="M6.5 7.5h4M6.5 10.5h3"/><path d="M11.8 15.6l.5-2.3 5-5 1.8 1.8-5 5z" fill="#FDEFC4"/>',
    hikidashi: '<path d="M8 6.5V5a2 2 0 0 1 4 0v1.5"/><rect x="4.5" y="6.5" width="11" height="11" rx="3.5" fill="#C6DDC9"/><rect x="7" y="11.5" width="6" height="4" rx="1.5" fill="#FDEFC4"/>',
    kiroku: '<rect x="3.5" y="3" width="13" height="14" rx="2.5" fill="#EAF1E4"/><path d="M6 7.2l1.2 1.2 2-2.2M6 12.2l1.2 1.2 2-2.2M11.5 7.5h3M11.5 12.5h3"/>',
    seiri: '<path d="M10 17.5V10M6.5 17.5h7"/><path d="M10 11C10 7.5 7.5 5.5 4 5.5c0 3.5 2.3 5.5 6 5.5z" fill="#C6DDC9"/><path d="M10 9.5c0-3 2.2-5 6-5 0 3.2-2.4 5-6 5z" fill="#A8D5BA"/>',
    watasu: '<path d="M6.5 18C5 14 14 13.5 13 9.5S6.5 6.5 10 2" stroke="#FDEFC4" stroke-width="5"/><path d="M6.5 18C5 14 14 13.5 13 9.5S6.5 6.5 10 2"/>'
  };
  function paintSvg(holder, src) {
    /* HTML として解くと <svg> は自動で図形の名前空間になる（宣言の URL を字として持たない）。字は上の固定の表だけ。 */
    var doc = new DOMParser().parseFromString(SVG_HEAD + src + '</svg>', 'text/html');
    var svg = doc.body.firstChild;
    if (!svg) { return; }
    clear(holder);
    holder.appendChild(document.importNode(svg, true));
  }
  function paintNavIcons() {
    var btns = document.querySelectorAll('#nav .nav-btn');
    Array.prototype.forEach.call(btns, function (b) {
      var holder = b.querySelector('.ico');
      var src = NAV_ICONS[b.getAttribute('data-view')];
      if (!holder || !src) { return; }
      paintSvg(holder, src);
    });
    var dot = document.getElementById('btn-reload');
    if (dot) { paintSvg(dot, NAV_ICONS.home); }
  }

  function lsSet(k, v) { try { window.localStorage.setItem(k, v); } catch (e) { /* 使えない端末では覚えない */ } }

  /* 日本時間の表示（5.10）。読めない字は空。直せないときは世界標準時の切り出し。 */
  function jstParts(iso) {
    if (typeof iso !== 'string' || !iso) { return null; }
    var d = new Date(iso);
    if (isNaN(d.getTime())) { return null; }
    try {
      var parts = new Intl.DateTimeFormat('en-GB', {
        timeZone: 'Asia/Tokyo', year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hourCycle: 'h23'
      }).formatToParts(d);
      var m = {};
      parts.forEach(function (p) { m[p.type] = p.value; });
      return { y: m.year, mo: m.month, d: m.day, h: m.hour, mi: m.minute, utc: false };
    } catch (e) {
      var s = d.toISOString();
      return { y: s.slice(0, 4), mo: s.slice(5, 7), d: s.slice(8, 10), h: s.slice(11, 13), mi: s.slice(14, 16), utc: true };
    }
  }
  function fmtDate(iso) { var p = jstParts(iso); return p ? p.y + '-' + p.mo + '-' + p.d + (p.utc ? '（世界標準時）' : '') : ''; }
  function fmtTime(iso) { var p = jstParts(iso); return p ? p.mo + '-' + p.d + ' ' + p.h + ':' + p.mi + (p.utc ? '（世界標準時）' : '') : ''; }
  function fmtDT(iso) { var p = jstParts(iso); return p ? p.y + '-' + p.mo + '-' + p.d + ' ' + p.h + ':' + p.mi + (p.utc ? '（世界標準時）' : '') : ''; }

  /* 最小の書式（6.4）: 太字・コード・見出しを太字に。ほかは字のまま。 */
  function inlineFmt(s, parent) {
    var re = /(\*\*[^*\n]+\*\*|`[^`\n]+`)/g;
    var last = 0, m;
    while ((m = re.exec(s)) !== null) {
      if (m.index > last) { parent.appendChild(document.createTextNode(s.slice(last, m.index))); }
      var tok = m[0];
      if (tok.charAt(0) === '`') { parent.appendChild(el('code', null, tok.slice(1, -1))); }
      else { parent.appendChild(el('strong', null, tok.slice(2, -2))); }
      last = m.index + tok.length;
    }
    if (last < s.length) { parent.appendChild(document.createTextNode(s.slice(last))); }
  }
  function mini(text, parent) {
    var lines = String(text === null || text === undefined ? '' : text).split('\n');
    lines.forEach(function (ln, i) {
      var h = /^#{1,6}\s+(.*)$/.exec(ln);
      if (h) {
        var b = el('strong');
        inlineFmt(h[1], b);
        parent.appendChild(b);
      } else {
        inlineFmt(ln, parent);
      }
      if (i < lines.length - 1) { parent.appendChild(document.createTextNode('\n')); }
    });
    return parent;
  }

  /* 2 段の釦（1 回目で字が替わり 6 秒で戻る・2 回目で実行） */
  function twoStep(button, label2, action) {
    var label1 = button.textContent;
    var armed = false, timer = null;
    function reset() { armed = false; button.textContent = label1; if (timer) { clearTimeout(timer); timer = null; } }
    button.addEventListener('click', function (ev) {
      if (!armed) {
        armed = true; button.textContent = label2;
        timer = later(reset, 6000);
        ev.stopImmediatePropagation();
        return;
      }
      reset();
      action();
    });
    return button;
  }

  /* ================================================================
     状態・通信
     ================================================================ */
  var IDLE_MS = 15 * 60 * 1000;
  var KEEPALIVE_MS = 4 * 60 * 1000;
  var MAX_BYTES = 5 * 1024 * 1024;
  var CALL_MS = 60000;
  var DEFAULT_COND = { amount: 'ふつう', split: '区切らない', ease: 'ふつう', length: 'みじかく', input: '文字' };

  var S = null;
  function freshState() {
    return {
      status: null, loggedIn: false, view: 'home', rail: 'renshu',
      cond: copy(DEFAULT_COND),
      chat: { renshu: [], seiri: [], kako: [] },
      drafts: { renshu: '', seiri: '', kako: '' },
      sending: false,
      urls: [],
      seat: false,
      stmt: newStmt(),
      recNames: {},
      hand: { stmtId: null, sel: {} },
      laws: {},
      mood: { open: false, pick: null, amount: 'ふつう' }
    };
  }
  function newStmt() {
    return { id: null, sections: { trouble: '', wish: '', grounds: [], statutes: [] }, hidden: {}, draft: null, text: '', finalized_at: null, dropped: false };
  }
  function copy(o) { return JSON.parse(JSON.stringify(o)); }

  var ui = { leftMin: false, railMin: false, railW: 0, sel: 'renshu', seat: false };
  var idleTimer = null, lastPing = 0, bootBusy = false;

  function api(method, path, body, ms) {
    var opt = { method: method, credentials: 'same-origin', headers: {} };
    var ctl = null, timer = null;
    if (typeof AbortController !== 'undefined') {
      ctl = new AbortController();
      opt.signal = ctl.signal;
      timer = setTimeout(function () { ctl.abort(); }, ms || CALL_MS);
    }
    if (body !== undefined) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
    return fetch(path, opt).then(function (r) {
      return r.text().then(function (t) {
        if (timer) { clearTimeout(timer); }
        var data = null;
        if (t) { try { data = JSON.parse(t); } catch (e) { data = null; } }
        if (r.ok) { return data; }
        var err = new Error('api');
        err.status = r.status; err.code = data && data.error; err.detail = data && data.detail; err.data = data;
        if (r.status === 401 && path !== '/api/login') { onUnauthorized(data); }
        throw err;
      });
    }, function () {
      if (timer) { clearTimeout(timer); }
      var e = new Error('net'); e.status = 0; e.detail = W['W-09'];
      throw e;
    });
  }
  function errText(e) { return (e && e.status !== 0 && e.detail) ? e.detail : W['W-09']; }

  /* ================================================================
     骨: 起動・入口・ログアウト
     ================================================================ */
  function fillStatic() {
    var n = document.querySelectorAll('[data-w]'), i, k, v;
    for (i = 0; i < n.length; i++) {
      k = n[i].getAttribute('data-w'); v = W[k];
      if (typeof v === 'string') { n[i].textContent = v; }
    }
    n = document.querySelectorAll('[data-w-title]');
    for (i = 0; i < n.length; i++) { v = W[n[i].getAttribute('data-w-title')]; if (typeof v === 'string') { n[i].setAttribute('title', v); } }
    n = document.querySelectorAll('[data-w-label]');
    for (i = 0; i < n.length; i++) { v = W[n[i].getAttribute('data-w-label')]; if (typeof v === 'string') { n[i].setAttribute('aria-label', v); } }
  }

  function setState(name) { document.body.setAttribute('data-state', name); }

  function showGate(expired) {
    $('shell').hidden = true;
    $('unconf').hidden = true;
    $('gate').hidden = false;
    $('gate-timeout').hidden = !expired;
    $('gate-err').hidden = true;
    $('gate-pw').value = '';
    setState('ready');
    try { $('gate-pw').focus(); } catch (e) { /* 何もしない */ }
  }

  function wipeScreen() {
    S.loggedIn = false;
    if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; }
    S.urls.forEach(function (u) { try { URL.revokeObjectURL(u); } catch (e) { /* 何もしない */ } });
    clear($('main')); clear($('rail-body')); clear($('modal-root')); $('crumb').textContent = '';
    $('shell').hidden = true;
    document.body.classList.remove('chat-only');
    var keepStatus = S.status;
    S = freshState();
    S.status = keepStatus ? { configured: keepStatus.configured, logged_in: false, claude: keepStatus.claude, demo_mode: keepStatus.demo_mode, port_paired: false } : null;
  }

  function onUnauthorized(data) {
    if (!S || !S.loggedIn) { return; }
    var expired = !!(data && data.expired);
    wipeScreen();
    showGate(expired);
  }

  async function doLogout(expired) {
    try { await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' }); } catch (e) { /* 閉じるだけ */ }
    if (!S.loggedIn) { return; }
    ui.seat = false; saveUi();   /* 同席の切替は端末に残さない（次に開く人のため） */
    wipeScreen();
    showGate(!!expired);
  }

  function resetIdle() {
    if (!S || !S.loggedIn) { return; }
    if (idleTimer) { clearTimeout(idleTimer); }
    idleTimer = later(function () { doLogout(true); }, IDLE_MS);
  }
  function onActivity() {
    if (!S || !S.loggedIn) { return; }
    resetIdle();
    var now = Date.now();
    if (now - lastPing > KEEPALIVE_MS) {
      lastPing = now;
      fetch('/api/status', { credentials: 'same-origin' }).catch(function () { /* 何もしない */ });
    }
  }

  async function refreshStatus() {
    try {
      var st = await api('GET', '/api/status');
      S.status = st;
      return st;
    } catch (e) { return S.status; }
  }

  async function boot() {
    fillStatic();
    S = freshState();
    loadUi();
    var st;
    try { st = await api('GET', '/api/status'); }
    catch (e) {
      setState('ready'); $('gate').hidden = false;
      var ge = $('gate-err'); ge.textContent = W['W-09']; ge.hidden = false;
      return;
    }
    S.status = st;
    $('demo-band').hidden = !st.demo_mode; $('demo-band').textContent = st.demo_placeholder ? W['DEMO-PLACEHOLDER'] : W['DEMO'];
    if (!st.configured) { $('gate').hidden = true; $('unconf').hidden = false; setState('ready'); return; }
    if (st.logged_in) { await enterApp(); } else { showGate(false); }
  }

  async function onGateSubmit(ev) {
    ev.preventDefault();
    if (bootBusy) { return; }
    var pw = $('gate-pw').value;
    var err = $('gate-err');
    err.hidden = true; $('gate-timeout').hidden = true;
    if (!pw) { err.textContent = W['W-10']; err.hidden = false; return; }
    bootBusy = true; $('gate-go').disabled = true;
    try {
      await api('POST', '/api/login', { passphrase: pw });
      $('gate-pw').value = '';
      await enterApp();
    } catch (e) {
      err.textContent = (e.status === 401 || e.status === 400 || e.status === 423 || e.status === 503) && e.detail ? e.detail : (e.status === 0 ? W['W-09'] : W['W-11']);
      err.hidden = false;
    } finally { bootBusy = false; $('gate-go').disabled = false; }
  }

  async function enterApp() {
    var st = await refreshStatus();
    if (!st || !st.logged_in) { showGate(false); return; }
    $('demo-band').hidden = !st.demo_mode; $('demo-band').textContent = st.demo_placeholder ? W['DEMO-PLACEHOLDER'] : W['DEMO'];
    S.loggedIn = true;
    $('gate').hidden = true;
    $('unconf').hidden = true;
    $('shell').hidden = false;
    setState('ready');
    ui.sel = (['renshu', 'seiri', 'kako'].indexOf(ui.sel) >= 0) ? ui.sel : 'renshu';
    S.rail = ui.sel;
    $('rail-sel').value = S.rail;
    initLayout();
    buildTier(S.rail);
    showView('home');
    resetIdle();
    lastPing = Date.now();
    /* 受け口へ取りに行くのは、本人が「読み直す」を押したときだけ（渡す操作なしには外へ出ない決まり）。
       器を開いたときは、器の中に在る返事を出すだけ。 */
  }

  /* ================================================================
     骨: 配置（左の帯・右の帯・小さい画面）
     ================================================================ */
  function isSmall() { return window.innerWidth <= 900; }
  function loadUi() {
    try {
      var j = JSON.parse(lsGet('cip_ui') || '{}');
      ui.leftMin = j.leftMin === true; ui.railMin = j.railMin === true;
      ui.railW = (typeof j.railW === 'number' && j.railW >= 300) ? j.railW : 0;
      ui.sel = typeof j.sel === 'string' ? j.sel : 'renshu';
      ui.seat = j.seat === true;
    } catch (e) { /* 既定のまま */ }
  }
  function saveUi() { lsSet('cip_ui', JSON.stringify({ leftMin: ui.leftMin, railMin: ui.railMin, railW: ui.railW, sel: ui.sel, seat: ui.seat })); }
  function chatOnly() { return isSmall() && ui.leftMin && !ui.railMin; }
  function applyLayout() {
    $('left').classList.toggle('side-min', ui.leftMin);
    $('rail').classList.toggle('rail-min', ui.railMin);
    if (ui.railW >= 300 && !isSmall()) {
      var cap = Math.floor(window.innerWidth * 0.6);
      $('rail').style.setProperty('--railw', Math.min(ui.railW, cap) + 'px');
    } else { $('rail').style.removeProperty('--railw'); }
    document.body.classList.toggle('chat-only', chatOnly());
  }
  function initLayout() {
    if (isSmall()) { ui.leftMin = true; ui.railMin = false; }   // スマホは A（左を畳む・右を開く）から始める
    applyLayout();
  }
  function scrollLogBottom() { var lg = $('tier-log'); if (lg) { lg.scrollTop = lg.scrollHeight; } }

  /* ================================================================
     面（modal）
     ================================================================ */
  var modalStack = [];
  function openModal(title, bodyNode, opts) {
    opts = opts || {};
    var prev = document.activeElement;
    var ov = el('div', 'overlay');
    ov.setAttribute('role', 'dialog'); ov.setAttribute('aria-modal', 'true'); ov.setAttribute('aria-label', title);
    var m = el('div', 'modal' + (opts.cls ? ' ' + opts.cls : ''));
    var head = el('div', 'modal-head');
    add(head, el('h2', null, title));
    var x = el('button', 'modal-close', '×'); x.type = 'button'; x.setAttribute('aria-label', W['W-171']); x.title = W['W-171'];
    head.appendChild(x);
    var body = el('div', 'modal-body');
    if (bodyNode) { body.appendChild(bodyNode); }
    add(m, head, body); ov.appendChild(m);
    var handle = { overlay: ov, body: body, closed: false };
    handle.close = function () {
      if (handle.closed) { return; }
      handle.closed = true;
      if (ov.parentNode) { ov.parentNode.removeChild(ov); }
      var i = modalStack.indexOf(handle); if (i >= 0) { modalStack.splice(i, 1); }
      if (opts.onClose) { opts.onClose(); }
      try { if (prev && prev.focus && document.body.contains(prev)) { prev.focus(); } } catch (e) { /* 何もしない */ }
    };
    x.addEventListener('click', handle.close);
    ov.addEventListener('mousedown', function (ev) { if (ev.target === ov) { handle.close(); } });
    $('modal-root').appendChild(ov);
    modalStack.push(handle);
    var f = opts.focus || x;
    try { f.focus(); } catch (e) { /* 何もしない */ }
    return handle;
  }
  function closeAllModals() { modalStack.slice().forEach(function (h) { h.close(); }); }

  /* ================================================================
     画面の切替
     ================================================================ */
  var VIEWS = {
    home: renderHome, renshu: renderRenshu, hikidashi: renderHikidashi,
    kiroku: renderKiroku, seiri: renderSeiri, watasu: renderWatasu
  };

  function showView(name, keepScroll) {
    if (!VIEWS[name]) { name = 'home'; }
    S.view = name;
    var btns = document.querySelectorAll('#nav .nav-btn');
    for (var i = 0; i < btns.length; i++) {
      var on = btns[i].getAttribute('data-view') === name;
      if (on) { btns[i].setAttribute('aria-current', 'page'); $('crumb').textContent = W['N-' + name]; }
      else { btns[i].removeAttribute('aria-current'); }
    }
    var host = $('main');
    clear(host);
    VIEWS[name](host);
    if (!keepScroll) { host.scrollTop = 0; window.scrollTo(0, 0); }
  }

  function goView(name) {
    if (chatOnly()) { ui.railMin = true; saveUi(); applyLayout(); }
    showView(name);
  }

  function section(accent) {
    var s = el('section', 'view');
    if (accent) { s.setAttribute('data-accent', accent); }
    return s;
  }
  function card(titleText, extra) {
    var c = el('div', 'card' + (extra ? ' ' + extra : ''));
    if (titleText) { c.appendChild(el('h2', null, titleText)); }
    return c;
  }
  function cardHead(titleText) {
    var head = el('div', 'card-head');
    head.appendChild(el('h2', null, titleText));
    return head;
  }

  /* ================================================================
     home
     ================================================================ */
  function renderHome(host) {
    var sec = section('home');
    // 挨拶（W-60・W-61）
    var g = card(null, 'greet');
    var gb = el('div', 'greet-body');
    gb.appendChild(el('h2', null, W['W-60']));
    var gp = el('p');
    add(gp, el('strong', null, W['W-61a']), document.createTextNode(W['W-61b']));
    gb.appendChild(gp);
    g.appendChild(gb);
    g.appendChild(figure('teku', 'fig-hero'));
    sec.appendChild(g);
    // 聞き役につながらないとき
    if (S.status && S.status.claude === 'no_key') {
      sec.appendChild(el('div', 'note', W['W-64']));
    }
    // 気分の面（A への任意の入口）
    sec.appendChild(buildMood());
    // とどいた返事
    var rc = card(null);
    var head = cardHead(W['W-62']);
    head.appendChild(linkbtn(L.reread, function () { rereadReplies(); }, 'body-size'));
    rc.appendChild(head);
    var body = el('div'); body.id = 'replies-body';
    rc.appendChild(body);
    sec.appendChild(rc);
    host.appendChild(sec);
    loadRepliesInto(body);
  }

  function buildMood() {
    var c = card(null);
    var scene = el('button', 'scene-btn', W['W-40']);
    scene.type = 'button';
    scene.setAttribute('aria-expanded', S.mood.open ? 'true' : 'false');
    c.appendChild(scene);
    var face = el('div', 'mood');
    face.hidden = !S.mood.open;
    scene.addEventListener('click', function () {
      S.mood.open = !S.mood.open; face.hidden = !S.mood.open;
      scene.setAttribute('aria-expanded', S.mood.open ? 'true' : 'false');
    });
    add(face, el('h3', null, W['W-41']), el('p', 'tiny', W['W-42']));
    var skip = linkbtn(W['W-43'], function () { S.mood.pick = null; S.mood.amount = 'ふつう'; S.cond = copy(DEFAULT_COND); paintMood(); refreshCondBar(); }, 'body-size');
    face.appendChild(skip);
    var cards = el('div', 'mood-cards');
    var cardEls = [];
    L.moods.forEach(function (m, idx) {
      var b = el('button', 'mood-card'); b.type = 'button';
      add(b, el('div', 'pic'), el('div', 'nm', m.name), el('div', 'rl', m.role), el('div', 'ds', m.desc));
      b.setAttribute('aria-pressed', 'false');
      b.addEventListener('click', function () { S.mood.pick = idx; S.mood.amount = m.amount; paintMood(); });
      cards.appendChild(b); cardEls.push(b);
    });
    face.appendChild(cards);
    face.appendChild(linkbtn(W['W-46'], openPromise, 'body-size'));
    var row = el('div', 'mood-row');
    var go = btn(W['W-47'], 'btn-main', function () {
      var cond = copy(DEFAULT_COND);
      if (S.mood.pick !== null) { var p = L.moods[S.mood.pick].patch; Object.keys(p).forEach(function (k) { cond[k] = p[k]; }); }
      cond.amount = S.mood.amount;
      S.cond = cond; refreshCondBar();
      openRail('renshu');
    });
    var pick = el('div', 'numpick');
    pick.appendChild(el('span', null, W['W-48']));
    var amountBtns = [];
    L.condGroups[0].opts.forEach(function (o) {
      var b = el('button', 'chip-btn', o); b.type = 'button';
      b.addEventListener('click', function () { S.mood.amount = o; paintMood(); });
      pick.appendChild(b); amountBtns.push([o, b]);
    });
    var no = btn(W['W-49'], 'btn-second', function () { S.mood.open = false; face.hidden = true; scene.setAttribute('aria-expanded', 'false'); });
    add(row, go, pick, no);
    face.appendChild(row);
    c.appendChild(face);
    function paintMood() {
      cardEls.forEach(function (b, i) { b.setAttribute('aria-pressed', S.mood.pick === i ? 'true' : 'false'); });
      amountBtns.forEach(function (p) { p[1].setAttribute('aria-pressed', S.mood.amount === p[0] ? 'true' : 'false'); });
    }
    paintMood();
    return c;
  }

  function openRail(tier) {
    ui.railMin = false;
    if (isSmall()) { ui.leftMin = true; }
    ui.sel = tier; S.rail = tier; $('rail-sel').value = tier;
    saveUi(); applyLayout(); buildTier(tier);
    var ta = $('tier-in'); if (ta) { ta.focus(); }
  }

  async function loadRepliesInto(box) {
    if (!box) { return; }
    clear(box); box.appendChild(el('p', 'loading', 'よみこみ中…'));
    var rows;
    try { rows = listOf(await api('GET', '/api/replies')); }
    catch (e) { if (S.loggedIn) { clear(box); box.appendChild(el('div', 'err', W['W-85'])); } return; }
    if (!S.loggedIn || !document.body.contains(box)) { return; }
    clear(box);
    rows = rows.filter(function (r) { return r.disposition === 'unread'; });
    rows.sort(function (a, b) { return String(b.written_at || '').localeCompare(String(a.written_at || '')); });
    if (!rows.length) { box.appendChild(line(W['W-63'])); return; }
    rows.forEach(function (r) { box.appendChild(replyItem(r, box)); });
  }

  function replyItem(r, box) {
    var it = el('div', 'rec-item');
    var t = el('div', 'rec-title');
    t.appendChild(bdi(r.port_name || ''));
    var label = r.author_label === L.tagMentor ? L.tagMentor : L.tagUnknown;
    t.appendChild(tag(label, label === L.tagMentor ? 'mentor' : 'unknown'));
    it.appendChild(t);
    it.appendChild(el('div', 'rec-meta', fmtDT(r.written_at)));
    var body = el('div', 'rec-text'); mini(r.text, body); it.appendChild(body);
    var row = el('div', 'btnrow');
    var status = el('div', 'status');
    var bind = btn(L.bindDo, 'btn-second', async function () {
      bind.disabled = true;
      try { await api('POST', '/api/replies/' + encodeURIComponent(r.reply_id) + '/bind', {}); loadRepliesInto(box); }
      catch (e) { bind.disabled = false; status.textContent = errText(e); }
    });
    var drop = twoStep(btn(L.discardDo, 'btn-second'), L.askDiscard, async function () {
      try { await api('POST', '/api/replies/' + encodeURIComponent(r.reply_id) + '/discard', {}); loadRepliesInto(box); }
      catch (e) { status.textContent = errText(e); }
    });
    add(row, bind, drop);
    add(it, row, status);
    return it;
  }

  async function rereadReplies() {
    var box = $('replies-body');
    if (!box) { return; }
    try { await api('POST', '/api/replies/refresh', {}); }
    catch (e) {
      if (S.loggedIn && document.body.contains(box)) {
        loadRepliesInto(box).then(function () { box.insertBefore(el('div', 'err', errText(e)), box.firstChild); });
      }
      return;
    }
    loadRepliesInto(box);
  }

  /* ================================================================
     renshu（A）
     ================================================================ */
  function condText(cond) {
    return L.condGroups.map(function (g) { return cond[g.key]; }).filter(Boolean).join('／');
  }

  function renderRenshu(host) {
    var sec = section('a');
    var c1 = card(L.conditionsTitle);
    L.condGroups.forEach(function (g) {
      c1.appendChild(el('div', 'field-label', g.label));
      var row = el('div', 'chips');
      g.opts.forEach(function (o) {
        var b = el('button', 'chip-btn', o); b.type = 'button';
        b.setAttribute('aria-pressed', S.cond[g.key] === o ? 'true' : 'false');
        b.addEventListener('click', function () {
          S.cond[g.key] = o;
          Array.prototype.forEach.call(row.querySelectorAll('.chip-btn'), function (x) { x.setAttribute('aria-pressed', x.textContent === o ? 'true' : 'false'); });
          refreshCondBar();
        });
        row.appendChild(b);
      });
      if (g.soon) { var s = el('button', 'chip-btn', g.soon); s.type = 'button'; s.disabled = true; row.appendChild(s); }
      c1.appendChild(row);
    });
    sec.appendChild(c1);
    var c2 = card(L.countsTitle);
    var box = el('div'); box.id = 'summary-box'; c2.appendChild(box);
    c2.appendChild(line(L.countsNote, 'tiny'));
    sec.appendChild(c2);
    host.appendChild(sec);
    loadSummary(box);
  }

  function parseKey(key) {
    var map = {};
    String(key).split('|').forEach(function (p) { var i = p.indexOf('='); if (i > 0) { map[p.slice(0, i)] = p.slice(i + 1); } });
    return map;
  }

  async function loadSummary(box) {
    clear(box); box.appendChild(el('p', 'loading', 'よみこみ中…'));
    var data;
    try { data = await api('GET', '/api/practice/summary'); }
    catch (e) { if (S.loggedIn && document.body.contains(box)) { clear(box); box.appendChild(el('div', 'err', W['W-85'])); } return; }
    if (!S.loggedIn || !document.body.contains(box)) { return; }
    clear(box);
    var src = (data && data.summary) ? data.summary : (data || {});
    var keys = Object.keys(src);
    if (!keys.length) { box.appendChild(emptyWithFigure('mana', 'fig-72', W['W-83'])); return; }
    var wrap = el('div', 'tablewrap'); var tb = el('table', 'counts');
    var thead = el('thead'); var hr = el('tr');
    hr.appendChild(el('th', null, '使った条件'));
    L.colMarks.forEach(function (m) { hr.appendChild(el('th', null, m)); });
    thead.appendChild(hr); tb.appendChild(thead);
    var tbody = el('tbody');
    keys.forEach(function (k) {
      var map = parseKey(k);
      var parts = L.condGroups.map(function (g) { return map[g.key] ? L.condShort[g.key] + ' ' + map[g.key] : ''; }).filter(Boolean);
      var tr = el('tr');
      var td = el('td'); td.appendChild(bdi(parts.join('・') || k)); tr.appendChild(td);
      L.colMarks.forEach(function (m) { tr.appendChild(el('td', 'n', String((src[k] && src[k][m]) || 0))); });
      tbody.appendChild(tr);
    });
    tb.appendChild(tbody); wrap.appendChild(tb); box.appendChild(wrap);
  }

  /* ================================================================
     hikidashi（B）
     ================================================================ */
  function renderHikidashi(host) {
    var sec = section('b');
    var scene2 = el('div', 'board-slot');
    sec.appendChild(scene2);
    var scene2First = board('02', 'empty', 'board-scene');   /* 先に空の場面を出す（読み込み後に数で差し替え＝段がずれない） */
    if (scene2First) { scene2.appendChild(scene2First); }
    sec.appendChild(el('div', 'note calm', noteKako));
    // 記録を入れる
    var c1 = card(W['W-100']);
    c1.appendChild(el('p', null, W['W-101']));
    c1.appendChild(el('h3', null, L.insertTitle));
    var fin = el('input'); fin.type = 'file'; fin.accept = 'image/*'; fin.hidden = true;
    var pick = btn(L.chooseFile, 'btn-second', function () { fin.click(); });
    var info = el('div', 'status'); info.setAttribute('role', 'status');
    fin.addEventListener('change', function () {
      var f = fin.files && fin.files[0];
      fin.value = '';
      if (!f) { return; }
      info.textContent = '';
      if (['image/jpeg', 'image/png', 'image/webp', 'image/svg+xml'].indexOf(f.type) < 0) { info.textContent = L.badType; return; }
      if (f.size > MAX_BYTES) { info.textContent = L.tooBig; return; }
      openSendFlow({ file: f, onDone: function (msg) { info.textContent = msg; loadRecordsInto(listBox); } });
    });
    add(c1, fin, el('div', 'btnrow'), info);
    c1.querySelector('.btnrow').appendChild(pick);
    sec.appendChild(c1);
    // 入れた記録
    var c2 = card(L.insertedTitle);
    var tile2 = el('div', 'fig-slot');
    c2.appendChild(tile2);
    var listBox = el('div'); c2.appendChild(listBox);
    listBox.onCount = function (n) {
      clear(scene2); clear(tile2);
      var sc = board('02', n ? 'filled' : 'empty', 'board-scene');
      if (sc) { scene2.appendChild(sc); }
      var tl = n ? board('02', 'filled', 'board-120') : null;
      if (tl) { tile2.appendChild(tl); }
    };
    sec.appendChild(c2);
    // 写真なしの控え
    var c3 = card(W['W-106']);
    var catBox = el('div');
    buildCatalog(c3, catBox);
    sec.appendChild(c3);
    host.appendChild(sec);
    loadRecordsInto(listBox);
    loadCatalogInto(catBox);
  }

  async function postRecord(name, file) {
    var b64 = await new Promise(function (resolve, reject) {
      var fr = new FileReader();
      fr.onload = function () { var s = String(fr.result); resolve(s.slice(s.indexOf(',') + 1)); };
      fr.onerror = function () { reject(new Error('read')); };
      fr.readAsDataURL(file);
    });
    return api('POST', '/api/records', { record_name: name, media_type: file.type, data_base64: b64 }, 120000);
  }

  /* 送る前の確かめの面。既定の釦は「保存だけに する」。 */
  function openSendFlow(opts) {
    var isNew = !!opts.file;
    var url = isNew ? URL.createObjectURL(opts.file) : '/api/records/' + encodeURIComponent(opts.recordId) + '/original';
    if (isNew) { S.urls.push(url); }
    var form = el('form');
    var img = el('img', 'thumb'); img.src = url; img.alt = '';
    form.appendChild(img);
    form.appendChild(el('p', null, L.sendConfirm));
    var nameIn = null;
    if (isNew) {
      var lab = el('label', 'field-label', L.readyName); lab.setAttribute('for', 'send-name');
      nameIn = el('input', 'field'); nameIn.id = 'send-name'; nameIn.type = 'text'; nameIn.maxLength = 200;
      nameIn.value = (opts.file.name || '').replace(/\.[^.]*$/, '');
      add(form, lab, nameIn);
    }
    var st = el('div', 'status'); st.setAttribute('role', 'status');
    var noKey = S.status && S.status.claude === 'no_key';
    var row = el('div', 'btnrow');
    var save = el('button', 'btn btn-second', L.saveOnly); save.type = 'submit';
    var send = btn(L.sendDo, 'btn-main btn-send');
    var cancel = linkbtn(L.cancel, function () { h.close(); }, 'body-size');
    send.disabled = !!noKey;
    if (!isNew) { save.hidden = true; }
    add(row, send, save, cancel);
    add(form, row, st);
    if (noKey) { form.appendChild(el('div', 'err', L.noKey)); }
    var h = openModal(L.sendDo, form, { cls: 'narrow', focus: isNew ? save : cancel,
      onClose: function () { if (isNew) { try { URL.revokeObjectURL(url); } catch (e) { /* 何もしない */ } } } });

    function lock(on) { save.disabled = on; send.disabled = on || !!noKey; cancel.disabled = on; }
    async function run(doSend) {
      lock(true);
      st.textContent = doSend ? W['W-133'] : '';
      var rid = opts.recordId, saved = false;
      try {
        if (isNew) {
          var nm = nameIn.value.trim() || L.unnamed;
          var r = await postRecord(nm, opts.file);
          rid = r.record_id; saved = true;
        }
        if (doSend) {
          try {
            await api('POST', '/api/records/' + encodeURIComponent(rid) + '/derive', { confirm_send: true }, 120000);
            h.close(); opts.onDone(isNew ? L.savedAndRead : '');
          } catch (e2) {
            h.close(); opts.onDone((saved ? L.savedNoRead + ' ' : '') + errText(e2));
          }
        } else { h.close(); opts.onDone(L.savedOnly); }
      } catch (e) { lock(false); st.textContent = errText(e); }
    }
    form.addEventListener('submit', function (ev) { ev.preventDefault(); if (isNew) { run(false); } });
    send.addEventListener('click', function () { run(true); });
  }

  async function loadRecordsInto(box) {
    if (!box) { return; }
    clear(box); box.appendChild(el('p', 'loading', 'よみこみ中…'));
    var rows;
    try { rows = listOf(await api('GET', '/api/records')); }
    catch (e) { if (S.loggedIn && document.body.contains(box)) { clear(box); box.appendChild(el('div', 'err', W['W-85'])); } return; }
    if (!S.loggedIn || !document.body.contains(box)) { return; }
    clear(box);
    if (box.onCount) { box.onCount(rows.length); }
    if (!rows.length) {
      var et = board('02', 'empty', 'board-160');
      if (!et) { box.appendChild(emptyWithFigure('kiro', 'fig-72', W['W-83'])); return; }
      var erow = el('div', 'empty-fig');
      add(erow, et);
      var ek = figure('kiro', 'fig-72');
      if (ek) { erow.appendChild(ek); }
      erow.appendChild(line(W['W-83']));
      box.appendChild(erow);
      return;
    }
    rows.forEach(function (r) { box.appendChild(recordItem(r, box)); });
  }

  function authorTag(rec) {
    if (rec.kind === 'reply') {
      return rec.author_label === L.tagMentor ? tag(L.tagMentor, 'mentor') : tag(L.tagUnknown, 'unknown');
    }
    var role = rec.subject && rec.subject.author_role;
    return role ? tag('他者（' + role + '）', 'other') : tag(L.tagUnknown, 'unknown');
  }

  function recordItem(rec, box) {
    var it = el('div', 'rec-item');
    var t = el('div', 'rec-title');
    t.appendChild(bdi(rec.record_name || L.unnamed));
    t.appendChild(authorTag(rec));
    if (rec.has_derived) { t.appendChild(tag(L.tagDerived, 'derived')); }
    if (rec.kind !== 'reply' && !(rec.subject && rec.subject.confirmed_by_person)) { t.appendChild(tag(L.unconfirmed, 'unconfirmed')); }
    it.appendChild(t);
    var meta = el('div', 'rec-meta');
    meta.appendChild(el('span', null, fmtDate(rec.imported_at)));
    if (rec.sha256) {
      var sp = el('span'); sp.appendChild(document.createTextNode(L.origFp + ' ')); sp.appendChild(el('span', 'mono', rec.sha256.slice(0, 16))); meta.appendChild(sp);
    }
    it.appendChild(meta);
    var again = function () { loadRecordsInto(box); };

    if (rec.kind === 'reply') {
      var bd = el('div', 'rec-text'); mini(rec.body, bd); it.appendChild(bd);
      subjectView(it, rec.subject);
      var rrow = el('div', 'btnrow');
      var rdel = twoStep(btn(L.delRecord, 'btn-second'), L.askDel, async function () {
        try { await api('DELETE', '/api/records/' + encodeURIComponent(rec.record_id)); again(); } catch (e) { it.appendChild(el('div', 'err', errText(e))); }
      });
      rrow.appendChild(rdel); it.appendChild(rrow);
      return it;
    }

    // 主語の欄 3 つ
    subjectView(it, rec.subject);
    it.appendChild(subjectEditor(rec, again));

    // 釦
    var row = el('div', 'btnrow');
    var err = el('div', 'status');
    add(row, btn(L.viewOrig, 'btn-second', function () { openOriginal(rec); }));
    if (rec.has_derived) { row.appendChild(btn(L.viewDerived, 'btn-second', function () { openDerived(rec); })); }
    var redo = btn(L.redo, 'btn-second', function () {
      openSendFlow({ recordId: rec.record_id, onDone: function (msg) { again(); if (msg) { err.textContent = msg; } } });
    });
    redo.disabled = !!(S.status && S.status.claude === 'no_key');
    row.appendChild(redo);
    if (rec.has_derived) {
      row.appendChild(twoStep(btn(L.delDerived, 'btn-second'), L.askDel, async function () {
        try { await api('DELETE', '/api/records/' + encodeURIComponent(rec.record_id) + '/derived'); again(); } catch (e) { err.textContent = errText(e); }
      }));
    }
    row.appendChild(twoStep(btn(L.delRecord, 'btn-second'), L.askDel, async function () {
      try { await api('DELETE', '/api/records/' + encodeURIComponent(rec.record_id)); again(); } catch (e) { err.textContent = errText(e); }
    }));
    it.appendChild(row);
    it.appendChild(err);

    // 注記（古い順）
    var notes = (rec.annotations || []).slice().sort(function (a, b) { return String(a.written_at).localeCompare(String(b.written_at)); });
    notes.forEach(function (n) {
      var nr = el('div', 'blk');
      var nh = el('div', 'rec-meta'); nh.appendChild(tag(L.noteTag, 'person')); nh.appendChild(document.createTextNode(' ' + fmtDT(n.written_at)));
      var nb = el('div', 'rec-text'); nb.textContent = n.text;
      add(nr, nh, nb); it.appendChild(nr);
    });
    var nf = el('details', 'fold');
    nf.appendChild(el('summary', null, L.addNote));
    var ta = el('textarea', 'field'); ta.rows = 3; ta.maxLength = 4000; ta.setAttribute('aria-label', L.addNote);
    var nst = el('div', 'status');
    var nd = btn(L.addNoteDo, 'btn-second', async function () {
      if (!ta.value.trim()) { return; }
      nd.disabled = true;
      try { await api('POST', '/api/records/' + encodeURIComponent(rec.record_id) + '/annotations', { text: ta.value }); again(); }
      catch (e) { nd.disabled = false; nst.textContent = errText(e); }
    });
    add(nf, ta, el('div', 'btnrow'), nst);
    nf.querySelector('.btnrow').appendChild(nd);
    it.appendChild(nf);
    return it;
  }

  function kv(k, v) {
    var d = el('div', 'kv');
    d.appendChild(el('span', 'k', k));
    var s = el('span'); s.appendChild(bdi(v || '—')); d.appendChild(s);
    return d;
  }
  function subjectView(it, s) {
    s = s || {};
    var box = el('div', 'blk');
    var h = el('div', 'rec-meta', L.subjTitle + ' ');
    if (!s.confirmed_by_person) { h.appendChild(tag(L.unconfirmed, 'unconfirmed')); }
    add(box, h, kv(L.subjWho, s.author_role), kv(L.subjWhen, s.written_at), kv(L.subjHow, s.procedure));
    it.appendChild(box);
  }
  function subjectEditor(rec, again) {
    var s = rec.subject || {};
    var f = el('details', 'fold');
    f.appendChild(el('summary', null, L.subjEdit));
    var grid = el('div');
    var ins = {};
    [['author_role', L.subjWho], ['written_at', L.subjWhen], ['procedure', L.subjHow]].forEach(function (p) {
      var lab = el('label', 'field-label', p[1]);
      var inp = el('input', 'field'); inp.type = 'text'; inp.maxLength = 200; inp.value = s[p[0]] || '';
      var id = 'sj-' + rec.record_id + '-' + p[0]; inp.id = id; lab.setAttribute('for', id);
      ins[p[0]] = inp; add(grid, lab, inp);
    });
    var st = el('div', 'status');
    function save(confirmed) {
      return api('PUT', '/api/records/' + encodeURIComponent(rec.record_id) + '/subject', {
        author_role: ins.author_role.value, written_at: ins.written_at.value, procedure: ins.procedure.value, confirmed_by_person: confirmed
      }).then(again, function (e) { st.textContent = errText(e); });
    }
    var row = el('div', 'btnrow');
    add(row, btn(L.subjKeep, 'btn-second', function () { save(false); }), btn(L.subjOk, 'btn-mint', function () { save(true); }));
    add(f, grid, row, st);
    return f;
  }

  function openOriginal(rec) {
    var img = el('img', 'modal-img'); img.alt = '';
    var msg = el('div', 'err', W['W-85']); msg.hidden = true;
    img.addEventListener('error', function () { img.hidden = true; msg.hidden = false; });
    img.src = '/api/records/' + encodeURIComponent(rec.record_id) + '/original';
    var wrap = el('div'); add(wrap, img, msg);
    openModal(L.viewOrig, wrap, { cls: 'wide-img' });
  }

  async function openDerived(rec) {
    var wrap = el('div'); wrap.appendChild(el('p', 'loading', 'よみこみ中…'));
    var h = openModal(L.viewDerived, wrap);
    var d;
    try { d = await api('GET', '/api/records/' + encodeURIComponent(rec.record_id)); }
    catch (e) { clear(wrap); wrap.appendChild(el('div', 'err', W['W-85'])); return; }
    clear(wrap);
    wrap.appendChild(tag((d.derived_meta && d.derived_meta.label) || DERIVED_LABEL, 'derived'));
    wrap.appendChild(el('div', 'note calm', W['W-70']));
    wrap.lastChild.style.marginTop = '8px';
    var md = d.derived_markdown || '';
    var secs = [], cur = { title: null, lines: [] };
    md.split('\n').forEach(function (ln) {
      var m = /^#{1,2}\s+(.*)$/.exec(ln);
      if (m) { if (cur.title !== null || cur.lines.join('').trim()) { secs.push(cur); } cur = { title: m[1], lines: [] }; }
      else { cur.lines.push(ln); }
    });
    if (cur.title !== null || cur.lines.join('').trim()) { secs.push(cur); }
    secs.forEach(function (s) {
      var c = el('div', 'rec-item');
      if (s.title !== null) { c.appendChild(el('div', 'rec-title', s.title)); }
      var b = el('div', 'rec-text'); mini(s.lines.join('\n').replace(/^\n+|\n+$/g, ''), b); c.appendChild(b);
      wrap.appendChild(c);
    });
    if (!secs.length) { wrap.appendChild(line(W['W-83'])); }
    return h;
  }

  /* 写真なしの控え */
  function buildCatalog(c3, catBox) {
    var g = el('div', 'grid2');
    var names = {};
    [['name', W['W-102'], 'x'], ['place', W['W-103'], 'x']].forEach(function (p) {
      var d = el('div'); var lab = el('label', 'field-label', p[1]); var inp = el('input', 'field'); inp.type = 'text'; inp.maxLength = 200;
      inp.id = 'cat-' + p[0]; lab.setAttribute('for', inp.id); names[p[0]] = inp; add(d, lab, inp); g.appendChild(d);
    });
    c3.appendChild(g);
    var lab = el('label', 'field-label', W['W-104']); var memo = el('textarea', 'field'); memo.rows = 2; memo.maxLength = 4000; memo.id = 'cat-memo'; lab.setAttribute('for', memo.id);
    add(c3, lab, memo);
    var st = el('div', 'status');
    var go = btn(W['W-105'], 'btn-second', async function () {
      if (!names.name.value.trim()) { return; }
      go.disabled = true;
      try {
        await api('POST', '/api/catalog', { name: names.name.value, place: names.place.value, memo: memo.value });
        names.name.value = ''; names.place.value = ''; memo.value = ''; st.textContent = '';
        loadCatalogInto(catBox);
      } catch (e) { st.textContent = errText(e); }
      go.disabled = false;
    });
    var row = el('div', 'btnrow'); row.appendChild(go);
    add(c3, row, st, el('h3', null, W['W-106']), catBox);
  }
  async function loadCatalogInto(box) {
    clear(box);
    var rows;
    try { rows = listOf(await api('GET', '/api/catalog')); }
    catch (e) { if (S.loggedIn && document.body.contains(box)) { box.appendChild(el('div', 'err', W['W-85'])); } return; }
    if (!S.loggedIn || !document.body.contains(box)) { return; }
    clear(box);
    if (!rows.length) { box.appendChild(line(W['W-107'])); return; }
    rows.forEach(function (r) {
      var it = el('div', 'rec-item');
      var t = el('div', 'rec-title'); t.appendChild(bdi(r.name)); it.appendChild(t);
      if (r.place) { var pm = el('div', 'rec-meta'); pm.appendChild(bdi(r.place)); it.appendChild(pm); }
      if (r.memo) { it.appendChild(el('div', 'rec-text', r.memo)); }
      var row = el('div', 'btnrow');
      row.appendChild(btn(W['W-108'], 'btn-second', async function () {
        try { await api('DELETE', '/api/catalog/' + encodeURIComponent(r.id)); loadCatalogInto(box); } catch (e) { it.appendChild(el('div', 'err', errText(e))); }
      }));
      it.appendChild(row); box.appendChild(it);
    });
  }

  /* ================================================================
     kiroku
     ================================================================ */
  function renderKiroku(host) {
    var sec = section();
    var c1 = card(W['W-80']); c1.appendChild(el('p', null, W['W-81'])); sec.appendChild(c1);
    var c2 = card(L.timelineTitle); c2.appendChild(el('p', 'tiny', W['W-87']));
    var tl = el('div'); c2.appendChild(tl); sec.appendChild(c2);
    var c3 = card(W['W-82']); c3.appendChild(line(W['W-83'])); sec.appendChild(c3);
    var c4 = card(L.claudeTitle); var cl = el('div'); c4.appendChild(cl); sec.appendChild(c4);
    var c5 = card(W['W-90']); buildExport(c5); sec.appendChild(c5);
    host.appendChild(sec);
    loadTimeline(tl);
    loadClaudeLog(cl);
  }

  async function loadTimeline(box) {
    clear(box); box.appendChild(el('p', 'loading', W['W-84']));
    var results = await Promise.all([
      api('GET', '/api/records').then(listOf, function () { return null; }),
      api('GET', '/api/handoffs').then(listOf, function () { return []; }),
      api('GET', '/api/statements').then(listOf, function () { return []; })
    ]);
    if (!S.loggedIn || !document.body.contains(box)) { return; }
    clear(box);
    if (results[0] === null) { box.appendChild(el('div', 'err', W['W-85'])); return; }
    var rows = [];
    results[0].forEach(function (r) {
      if (r.kind === 'reply') { rows.push({ at: r.imported_at, kind: 'reply', who: authorTag(r), title: r.record_name, go: 'hikidashi' }); }
      else {
        rows.push({ at: r.imported_at, kind: 'record', who: authorTag(r), title: r.record_name, go: 'hikidashi' });
        (r.annotations || []).forEach(function (n) { rows.push({ at: n.written_at, kind: 'note', who: tag(L.noteTag, 'person'), title: n.text, go: 'hikidashi' }); });
      }
    });
    results[1].forEach(function (h) {
      var b = h.bundle || {};
      rows.push({ at: b.created_at, kind: 'handoff', who: tag(L.tagPerson, 'person'), title: (h.receipt && h.receipt.port_name) || h.bundle_id, go: 'watasu' });
    });
    results[2].forEach(function (s) {
      rows.push({ at: s.finalized_at || s.updated_at || s.created_at, kind: 'statement', who: tag(L.tagPerson, 'person'), title: (s.text || (s.sections && s.sections.trouble) || L.stTitle), go: 'seiri' });
    });
    rows.sort(function (a, b) { return String(b.at || '').localeCompare(String(a.at || '')); });
    if (!rows.length) { box.appendChild(line(W['W-83'])); return; }
    rows.forEach(function (r) {
      var b = el('button', 'rec-item'); b.type = 'button';
      var t = el('div', 'rec-title');
      add(t, el('span', 'mono', fmtDate(r.at)), tag(L.kinds[r.kind], 'unknown'), r.who);
      var tt = el('div', 'rec-text'); tt.appendChild(bdi(String(r.title).slice(0, 80)));
      add(b, t, tt);
      b.addEventListener('click', function () { goView(r.go); });
      box.appendChild(b);
    });
  }

  async function loadClaudeLog(box) {
    clear(box);
    var rows;
    try { rows = listOf(await api('GET', '/api/claude_log')); }
    catch (e) { if (S.loggedIn && document.body.contains(box)) { box.appendChild(el('div', 'err', W['W-85'])); } return; }
    if (!S.loggedIn || !document.body.contains(box)) { return; }
    if (!rows.length) { box.appendChild(line(W['W-83'])); return; }
    rows.slice().reverse().forEach(function (r) {
      var it = el('div', 'rec-item');
      var t = el('div', 'rec-title');
      add(t, el('span', 'mono', fmtTime(r.at)), el('span', null, L.claudeKinds[r.kind] || r.kind));
      var m = el('div', 'rec-meta'); m.appendChild(bdi(String(r.what || '')));
      add(it, t, m); box.appendChild(it);
    });
  }

  function buildExport(c) {
    c.appendChild(el('p', null, W['W-91']));
    var out = el('div'); out.setAttribute('role', 'status');
    var ex = btn(W['W-92'], 'btn-second', async function () {
      ex.disabled = true; clear(out);
      try {
        var r = await api('POST', '/api/export', {}, 120000);
        var res = el('div', 'result');
        res.appendChild(el('div', null, L.exportDone));
        var cnt = el('div', 'rec-meta');
        Object.keys(L.countLabels).forEach(function (k) {
          var s = el('span', null, L.countLabels[k] + ' ' + ((r.counts && r.counts[k]) || 0)); cnt.appendChild(s);
        });
        res.appendChild(cnt);
        var a = el('a', 'linkbtn body-size', L.exportSave);
        a.href = '/api/export/' + encodeURIComponent(r.file); a.setAttribute('download', r.file);
        res.appendChild(a);
        out.appendChild(res);
        res.scrollIntoView({ block: 'nearest' });
      } catch (e) { out.appendChild(el('div', 'err', L.exportFail)); }
      ex.disabled = false;
    });
    c.appendChild(el('div', 'btnrow')); c.lastChild.appendChild(ex);
    c.appendChild(out);
    // 器の中身をけす（2 段・6 秒）
    c.appendChild(el('h3', null, W['W-93']));
    var keep = el('div', 'chips');
    var choice = 'drop';
    var kb = el('button', 'chip-btn', L.dropReceipts); kb.type = 'button'; kb.setAttribute('aria-pressed', 'true');
    var kb2 = el('button', 'chip-btn', L.keepReceipts); kb2.type = 'button'; kb2.setAttribute('aria-pressed', 'false');
    kb.addEventListener('click', function () { choice = 'drop'; kb.setAttribute('aria-pressed', 'true'); kb2.setAttribute('aria-pressed', 'false'); });
    kb2.addEventListener('click', function () { choice = 'keep'; kb2.setAttribute('aria-pressed', 'true'); kb.setAttribute('aria-pressed', 'false'); });
    add(keep, kb, kb2);
    c.appendChild(keep);
    var done = el('div', 'status'); done.setAttribute('role', 'status');
    var wipe = twoStep(btn(W['W-93'], 'btn-second'), W['W-94'], async function () {
      try {
        await api('DELETE', '/api/vault', { confirm: '消します', keep_receipts: choice === 'keep' });
        done.textContent = W['W-94b'];
        later(function () { if (S.loggedIn) { showView('kiroku', true); } }, 2500);
      } catch (e) { done.textContent = errText(e); }
    });
    var row = el('div', 'btnrow'); row.appendChild(wipe);
    add(c, row, done, el('p', 'tiny', W['W-95']));
  }

  /* ================================================================
     seiri（C）
     ================================================================ */
  var ST_FIELDS = [['trouble', 'stTrouble'], ['wish', 'stWish'], ['grounds', 'stGrounds'], ['statutes', 'stStatutes']];

  function stPayload() {
    var s = S.stmt, o = { trouble: '', wish: '', grounds: [], statute_ids: [] };
    if (!s.hidden.trouble) { o.trouble = s.sections.trouble; }
    if (!s.hidden.wish) { o.wish = s.sections.wish; }
    if (!s.hidden.grounds) { o.grounds = s.sections.grounds.slice(); }
    if (!s.hidden.statutes) { o.statute_ids = s.sections.statutes.slice(); }
    return o;
  }
  function absorb(r) {
    if (!r || typeof r !== 'object') { return; }
    var s = r.statement && typeof r.statement === 'object' ? r.statement : r;
    if (s.item_id) { S.stmt.id = s.item_id; } else if (s.id) { S.stmt.id = s.id; }
    if (s.finalized_at !== undefined) { S.stmt.finalized_at = s.finalized_at; }
    if (typeof s.text === 'string' && s.finalized_at) { S.stmt.text = s.text; }
    if (s.draft && typeof s.draft === 'object') { S.stmt.draft = s.draft; }
    var dn = (typeof r.dropped_ids === 'number') ? r.dropped_ids : ((r.dropped_ids && r.dropped_ids.length) || 0);
    if (dn > 0 || r.dropped_statutes) { S.stmt.dropped = true; }
  }
  async function saveStatement() {
    var body = { sections: stPayload() };
    var r;
    if (S.stmt.id) { r = await api('PUT', '/api/statements/' + encodeURIComponent(S.stmt.id), body); }
    else { r = await api('POST', '/api/statements', body); }
    absorb(r);
    return r;
  }
  function draftText() {
    var d = S.stmt.draft;
    if (!d) { return ''; }
    return d.text || d.draft_text || '';
  }

  function renderSeiri(host) {
    var sec = section('c');
    var seatScene = el('div', 'board-slot');
    sec.appendChild(seatScene);
    var seatTile = null;
    S.seat = ui.seat;
    var info = el('div', 'status'); info.setAttribute('role', 'status');
    var c = card(null);
    var ch = cardHead(L.stTitle);
    var seatBtn = el('button', 'linkbtn body-size seat-toggle', W['W-172']);
    seatBtn.type = 'button';
    seatBtn.setAttribute('aria-pressed', S.seat ? 'true' : 'false');
    function paintSeat() {
      var st = S.seat ? 'seat-taken' : 'seat-empty';
      clear(seatScene);
      var sc = board('03', st, 'board-scene');
      if (sc) { seatScene.appendChild(sc); }
      if (seatTile) {
        clear(seatTile);
        var tl = board('03', st, 'board-160');
        if (tl) { seatTile.appendChild(tl); }
      }
    }
    seatBtn.addEventListener('click', function () {
      S.seat = !S.seat; ui.seat = S.seat;
      seatBtn.setAttribute('aria-pressed', S.seat ? 'true' : 'false');
      saveUi(); paintSeat();
    });
    ch.appendChild(seatBtn);
    ch.appendChild(linkbtn(L.stNew, function () { S.stmt = newStmt(); showView('seiri', true); }, 'body-size'));
    c.appendChild(ch);
    var stFig = el('div', 'fig-slot');
    stFig.onEmpty = function () { seatTile = el('div'); stFig.appendChild(seatTile); paintSeat(); };
    c.appendChild(stFig);
    paintSeat();
    var fieldsBox = el('div');
    c.appendChild(fieldsBox);
    var restoreRow = el('div', 'btnrow');
    c.appendChild(restoreRow);
    var row = el('div', 'btnrow');
    var save = btn(L.stSave, 'btn-second', async function () {
      save.disabled = true; info.textContent = '';
      try { await saveStatement(); info.textContent = L.saved; } catch (e) { info.textContent = errText(e); }
      save.disabled = false;
    });
    var noKey = S.status && S.status.claude === 'no_key';
    var arr = btn(L.arrangeBtn, 'btn-main', function () { arrangeFlow(info, draftBox, finalBox); });
    arr.disabled = !!noKey;
    add(row, save, arr);
    c.appendChild(row);
    if (noKey) { c.appendChild(el('div', 'err', L.noKey)); }
    c.appendChild(info);
    sec.appendChild(c);

    var draftBox = el('div'); sec.appendChild(draftBox);
    var finalBox = el('div'); sec.appendChild(finalBox);
    var prevCard = card(L.stPrev); var prevBox = el('div'); prevCard.appendChild(prevBox); sec.appendChild(prevCard);
    host.appendChild(sec);

    function paintFields() {
      clear(fieldsBox); clear(restoreRow);
      ST_FIELDS.forEach(function (f) {
        var key = f[0];
        if (S.stmt.hidden[key]) { return; }
        var blk = el('div', 'blk');
        var head = el('div', 'card-head');
        head.appendChild(el('h3', null, L[f[1]]));
        head.appendChild(linkbtn(L.stDrop, function () { S.stmt.hidden[key] = true; paintFields(); }));
        blk.appendChild(head);
        if (key === 'trouble' || key === 'wish') {
          var ta = el('textarea', 'field'); ta.rows = 4; ta.maxLength = 4000; ta.value = S.stmt.sections[key];
          ta.setAttribute('aria-label', L[f[1]]);
          ta.addEventListener('input', function () { S.stmt.sections[key] = ta.value; });
          blk.appendChild(ta);
        } else if (key === 'grounds') {
          var gl = el('div'); blk.appendChild(gl);
          paintGrounds(gl);
          blk.appendChild(btn(L.stPickRecords, 'btn-second', function () { pickRecords(function () { paintGrounds(gl); }); }));
        } else {
          var sl = el('div'); blk.appendChild(sl);
          paintStatutes(sl);
          blk.appendChild(btn(L.stPickLaws, 'btn-second', function () { pickLaws(function () { paintStatutes(sl); }); }));
        }
        fieldsBox.appendChild(blk);
      });
      var hiddenKeys = Object.keys(S.stmt.hidden).filter(function (k) { return S.stmt.hidden[k]; });
      if (hiddenKeys.length) {
        restoreRow.appendChild(linkbtn(L.stRestore, function () { S.stmt.hidden = {}; paintFields(); }, 'body-size'));
      }
    }
    paintFields();
    paintDraft(draftBox, finalBox);
    paintFinal(finalBox);
    loadPrevStatements(prevBox, prevCard, stFig, function () { paintFields(); paintDraft(draftBox, finalBox); paintFinal(finalBox); });
  }

  async function loadPrevStatements(box, cardEl, figSlot, repaint) {
    var rows;
    try { rows = listOf(await api('GET', '/api/statements')); } catch (e) { rows = []; }
    if (!S.loggedIn || !document.body.contains(box)) { return; }
    if (!rows.length) {
      cardEl.hidden = true;
      if (figSlot.onEmpty) { figSlot.onEmpty(); }
      var kf = figure('koto', 'fig-56');
      if (kf) { figSlot.appendChild(kf); }
      return;
    }
    rows.forEach(function (s) {
      var it = el('div', 'rec-item');
      var t = el('div', 'rec-title');
      t.appendChild(bdi(String((s.text || (s.sections && s.sections.trouble) || L.stTitle)).slice(0, 60)));
      t.appendChild(s.finalized_at ? tag(L.stFinalTitle, 'person') : tag(L.stDraftTag, 'draft'));
      it.appendChild(t);
      it.appendChild(el('div', 'rec-meta', fmtDT(s.finalized_at || s.updated_at || s.created_at || '')));
      var row = el('div', 'btnrow');
      row.appendChild(btn(L.stOpen, 'btn-second', function () {
        var sec = s.sections || {};
        S.stmt = newStmt();
        S.stmt.id = s.item_id || s.id || null;
        S.stmt.sections = { trouble: sec.trouble || '', wish: sec.wish || '', grounds: (sec.grounds || []).slice(), statutes: (sec.statute_ids || []).slice() };
        S.stmt.finalized_at = s.finalized_at || null;
        S.stmt.text = s.text || '';
        S.stmt.draft = s.draft || null;
        showView('seiri');
      }));
      it.appendChild(row); box.appendChild(it);
    });
  }

  function paintGrounds(box) {
    clear(box);
    var ids = S.stmt.sections.grounds;
    if (!ids.length) { box.appendChild(line(W['W-83'])); return; }
    ids.forEach(function (id) {
      var r = el('div', 'kv'); r.appendChild(bdi(S.recNames && S.recNames[id] ? S.recNames[id] : id));
      r.appendChild(linkbtn(L.drop, function () { S.stmt.sections.grounds = S.stmt.sections.grounds.filter(function (x) { return x !== id; }); paintGrounds(box); }));
      box.appendChild(r);
    });
  }
  function paintStatutes(box) {
    clear(box);
    var ids = S.stmt.sections.statutes;
    if (!ids.length) { box.appendChild(line(W['W-83'])); return; }
    ids.forEach(function (id) {
      var law = S.laws[id];
      var r = el('div', 'kv');
      var nm = linkbtn(law ? (law.law_name + ' ' + law.article) : id, function () { openLaw(id); }, 'body-size');
      r.appendChild(nm);
      r.appendChild(linkbtn(L.drop, function () { S.stmt.sections.statutes = S.stmt.sections.statutes.filter(function (x) { return x !== id; }); paintStatutes(box); }));
      box.appendChild(r);
    });
  }

  async function pickRecords(done) {
    var wrap = el('div'); wrap.appendChild(el('p', 'loading', W['W-84']));
    var h = openModal(L.stPickRecords, wrap);
    var rows;
    try { rows = listOf(await api('GET', '/api/records')); } catch (e) { clear(wrap); wrap.appendChild(el('div', 'err', W['W-85'])); return; }
    clear(wrap);
    var chosen = S.stmt.sections.grounds.slice();
    if (!rows.length) { wrap.appendChild(line(W['W-83'])); }
    rows.forEach(function (r) {
      S.recNames[r.record_id] = r.record_name;
      var lab = el('label', 'pick');
      var cb = el('input'); cb.type = 'checkbox'; cb.checked = chosen.indexOf(r.record_id) >= 0;
      cb.addEventListener('change', function () {
        chosen = chosen.filter(function (x) { return x !== r.record_id; });
        if (cb.checked) { chosen.push(r.record_id); }
      });
      var sp = el('span'); sp.appendChild(bdi(r.record_name || L.unnamed));
      add(lab, cb, sp); wrap.appendChild(lab);
    });
    var row = el('div', 'btnrow');
    add(row, btn(L.done, 'btn-mint', function () { S.stmt.sections.grounds = chosen; h.close(); done(); }));
    wrap.appendChild(row);
  }

  async function fetchLaw(id) {
    if (S.laws[id] && S.laws[id].text_verbatim !== undefined) { return S.laws[id]; }
    var d = await api('GET', '/api/law/' + encodeURIComponent(id));
    S.laws[id] = d; return d;
  }
  function lawBody(law) {
    var w = el('div');
    var sr = el('div', 'rec-meta', L.lawSource);
    w.appendChild(sr);
    w.appendChild(kv(L.lawName, law.law_name)); w.appendChild(kv(L.lawArticle, law.article));
    w.appendChild(kv(L.lawOn, law.retrieved_on)); w.appendChild(kv(L.lawSrcName, law.source_name));
    w.appendChild(kv(L.lawBy, law.retrieved_by)); if (law.set_version) { w.appendChild(kv(L.lawVer, law.set_version)); }
    w.appendChild(el('div', 'field-label', L.lawText));
    w.appendChild(el('div', 'longbox', law.text_verbatim));
    return w;
  }
  async function openLaw(id) {
    var wrap = el('div'); wrap.appendChild(el('p', 'loading', W['W-84']));
    openModal(L.stStatutes, wrap);
    try { var law = await fetchLaw(id); clear(wrap); wrap.appendChild(lawBody(law)); }
    catch (e) { clear(wrap); wrap.appendChild(el('div', 'err', W['W-85'])); }
  }
  async function pickLaws(done) {
    var wrap = el('div'); wrap.appendChild(el('p', 'loading', W['W-84']));
    var h = openModal(L.stPickLaws, wrap);
    var rows;
    try { rows = listOf(await api('GET', '/api/law')); } catch (e) { clear(wrap); wrap.appendChild(el('div', 'err', W['W-85'])); return; }
    clear(wrap);
    if (!rows.length) { wrap.appendChild(line(L.lawNone)); return; }
    var chosen = S.stmt.sections.statutes.slice();
    rows.forEach(function (r) {
      var id = r.id || r.law_id;
      S.laws[id] = S.laws[id] || r;
      var box = el('div', 'pick');
      var cb = el('input'); cb.type = 'checkbox'; cb.checked = chosen.indexOf(id) >= 0;
      cb.setAttribute('aria-label', (r.law_name || '') + ' ' + (r.article || ''));
      cb.addEventListener('change', function () {
        chosen = chosen.filter(function (x) { return x !== id; });
        if (cb.checked) { chosen.push(id); }
      });
      var info = el('div');
      var nm = linkbtn((r.law_name || id) + ' ' + (r.article || ''), function () { openLaw(id); }, 'body-size');
      info.appendChild(nm);
      add(box, cb, info); wrap.appendChild(box);
    });
    wrap.appendChild(el('div', 'btnrow')); wrap.lastChild.appendChild(btn(L.done, 'btn-mint', function () { S.stmt.sections.statutes = chosen; h.close(); done(); }));
  }

  /* Claude に並べてもらう（確かめの面を先に） */
  async function arrangeFlow(info, draftBox, finalBox) {
    info.textContent = '';
    try { await saveStatement(); } catch (e) { info.textContent = errText(e); return; }
    var recs = [];
    try { recs = listOf(await api('GET', '/api/records')); } catch (e) { /* 一覧が無くても確かめの面は出す */ }
    var byId = {}; recs.forEach(function (r) { byId[r.record_id] = r; });
    var wrap = el('div');
    wrap.appendChild(el('p', null, 'この内容を Claude に 送ります。送らずに やめることも できます。'));
    var p = stPayload();
    wrap.appendChild(el('h3', null, L.stTrouble)); wrap.appendChild(el('div', 'longbox', p.trouble || '—'));
    wrap.appendChild(el('h3', null, L.stWish)); wrap.appendChild(el('div', 'longbox', p.wish || '—'));
    wrap.appendChild(el('h3', null, L.stGrounds + '（写しの文字）'));
    if (!p.grounds.length) { wrap.appendChild(line('—')); }
    p.grounds.forEach(function (id) {
      var r = byId[id]; var d = el('div', 'kv'); d.appendChild(bdi(r ? (r.record_name || L.unnamed) : id));
      if (r && !r.has_derived) { d.appendChild(el('span', 'k', '（写しが ないので 送る字は ありません）')); }
      wrap.appendChild(d);
    });
    wrap.appendChild(el('h3', null, '法令集の 見出し'));
    wrap.appendChild(line('法令名と条番号だけ。原文は 送りません。', 'tiny'));
    var st = el('div', 'status');
    var row = el('div', 'btnrow');
    var go = btn(L.stSendDo, 'btn-main btn-send');
    var no = btn(L.stNoSend, 'btn-second', function () { h.close(); });
    add(row, go, no); add(wrap, row, st);
    var h = openModal(L.stArrangeConfirm, wrap, { focus: no });
    go.addEventListener('click', async function () {
      go.disabled = true; no.disabled = true; st.textContent = W['W-133'];
      try {
        var r = await api('POST', '/api/statements/' + encodeURIComponent(S.stmt.id) + '/arrange', { confirm_send: true, include_records: S.stmt.sections.grounds.slice() }, 120000);
        absorb(r);
        h.close();
        paintDraft(draftBox, finalBox); paintFinal(finalBox);
        if (draftBox.firstChild) { draftBox.scrollIntoView({ block: 'nearest' }); }
      } catch (e) { go.disabled = false; no.disabled = false; st.textContent = errText(e) || L.arrangeFail; }
    });
  }

  function paintDraft(box, finalBox) {
    clear(box);
    var d = S.stmt.draft;
    if (!d) { return; }
    var c = card(null);
    var head = cardHead(L.stDraftTag);
    head.firstChild.textContent = '';
    head.firstChild.appendChild(tag(L.stDraftTag, 'draft'));
    c.appendChild(head);
    var dt = el('div', 'longbox'); dt.textContent = draftText();
    c.appendChild(dt);
    var ids = d.statute_ids || [];
    var objs = Array.isArray(d.statutes) ? d.statutes : [];
    if (!objs.length && ids.length) { objs = ids.map(function (id) { return { id: id }; }); }
    objs.forEach(function (o) {
      var id = o.id || o.law_id;
      var sc = el('div', 'rec-item');
      var holder = el('div');
      sc.appendChild(holder);
      (async function () {
        try { var law = (o.text_verbatim !== undefined) ? o : await fetchLaw(id); holder.appendChild(lawBody(law)); }
        catch (e) { holder.appendChild(el('div', 'err', W['W-85'])); }
      })();
      var rw = el('div', 'btnrow');
      rw.appendChild(btn(L.lawAttach, 'btn-second', function () {
        if (S.stmt.sections.statutes.indexOf(id) < 0) { S.stmt.sections.statutes.push(id); }
        showView('seiri', true);
      }));
      sc.appendChild(rw); c.appendChild(sc);
    });
    if (S.stmt.dropped) { c.appendChild(el('div', 'msg sys', L.stDropped)); c.lastChild.style.maxWidth = 'none'; }
    box.appendChild(c);
  }

  function paintFinal(box) {
    clear(box);
    var c = card(L.stFinalTitle);
    if (S.stmt.finalized_at) {
      var h = el('div', 'rec-meta'); h.appendChild(tag(L.tagPerson, 'person')); h.appendChild(document.createTextNode(' ' + fmtDT(S.stmt.finalized_at)));
      c.appendChild(h);
      c.appendChild(el('div', 'longbox', S.stmt.text));
      box.appendChild(c);
      return;
    }
    var ta = el('textarea', 'field'); ta.rows = 5; ta.maxLength = 8000; ta.value = S.stmt.text || draftText(); ta.setAttribute('aria-label', L.stFinalTitle);
    ta.addEventListener('input', function () { S.stmt.text = ta.value; });
    var st = el('div', 'status');
    var go = btn(L.stFinal, 'btn-mint', async function () {
      var text = ta.value;
      if (!text.trim()) { return; }
      go.disabled = true;
      try {
        if (!S.stmt.id) { await saveStatement(); }
        var r = await api('POST', '/api/statements/' + encodeURIComponent(S.stmt.id) + '/finalize', { text: text, sections: stPayload() });
        absorb(r);
        if (!S.stmt.finalized_at) { S.stmt.finalized_at = new Date().toISOString(); }
        S.stmt.text = text;
        paintFinal(box);
      } catch (e) { go.disabled = false; st.textContent = errText(e); }
    });
    var row = el('div', 'btnrow'); row.appendChild(go);
    add(c, ta, row, st);
    box.appendChild(c);
  }

  /* ================================================================
     watasu（渡す口）
     ================================================================ */
  var PARTS = ['original', 'derived', 'subject_fields', 'annotations'];

  function renderWatasu(host) {
    var sec = section();
    // つなぐ
    var c1 = card(L.pairTitle);
    var pairInfo = el('div', 'status');
    var paired = el('div');
    function paintPaired() {
      clear(paired);
      if (S.status && S.status.port_paired) {
        var r = el('div', 'kv'); r.appendChild(el('span', 'k', L.pairedWith));
        var b = el('span'); b.appendChild(bdi((S.status && S.status.port_name) || '')); r.appendChild(b);
        paired.appendChild(r);
      } else { paired.appendChild(line(L.notPaired)); }
    }
    paintPaired();
    var lab = el('label', 'field-label', L.pairLabel); lab.setAttribute('for', 'pair-code');
    var inp = el('input', 'field'); inp.type = 'password'; inp.id = 'pair-code'; inp.autocomplete = 'off'; inp.maxLength = 128;
    var pb = btn(L.pairDo, 'btn-mint', async function () {
      if (!inp.value.trim()) { return; }
      pb.disabled = true; pairInfo.textContent = '';
      try {
        var r = await api('POST', '/api/pair', { pairing_code: inp.value });
        inp.value = '';
        S.status.port_paired = true; S.status.port_name = r && r.port_name;
        paintPaired(); refreshPreview();
      } catch (e) { pairInfo.textContent = e.status === 0 ? W['W-09'] : L.pairFail; }
      pb.disabled = false;
    });
    var prow = el('div', 'btnrow'); prow.appendChild(pb);
    add(c1, paired, lab, inp, prow, pairInfo);
    sec.appendChild(c1);

    // わたす物を えらぶ
    var c2 = card(L.chooseTitle);
    var chooseBox = el('div'); c2.appendChild(chooseBox);
    sec.appendChild(c2);

    // たしかめる
    var c3 = card(L.checkTitle);
    var checkBox = el('div'); c3.appendChild(checkBox);
    c3.appendChild(el('p', 'tiny', L.giveNote));
    var resultBox = el('div'); resultBox.setAttribute('role', 'status');
    var give = btn(L.giveDo, 'btn-main btn-send');
    give.disabled = true;
    var grow = el('div', 'btnrow'); grow.appendChild(give);
    add(c3, grow, resultBox);
    sec.appendChild(c3);

    // 控え
    var c4 = card(L.pastTitle); var pastBox = el('div'); c4.appendChild(pastBox); sec.appendChild(c4);
    host.appendChild(sec);

    var data = { recs: [], stmts: [] };
    var pv = null, pvSeq = 0;

    function chosenItems() {
      var recs = [];
      Object.keys(S.hand.sel).forEach(function (id) {
        var parts = PARTS.filter(function (p) { return S.hand.sel[id][p]; });
        if (parts.length) { recs.push({ record_id: id, parts: parts }); }
      });
      return recs;
    }
    function toName(r) { return r.record_name || L.unnamed; }

    /* 束を作って見せる（送らない）。指紋・中身・送り先・日時を、わたす前に見せる。 */
    async function refreshPreview() {
      var seq = ++pvSeq;
      pv = null; give.disabled = true;
      clear(checkBox);
      var recs = chosenItems();
      if (!S.hand.stmtId) {
        checkBox.appendChild(line(recs.length ? L.needStmt : L.giveNone));
        return;
      }
      checkBox.appendChild(el('p', 'loading', W['W-84']));
      var r;
      try { r = await api('POST', '/api/handoffs/preview', { statement_id: S.hand.stmtId, records: recs }); }
      catch (e) {
        if (seq !== pvSeq || !S.loggedIn) { return; }
        clear(checkBox);
        checkBox.appendChild(el('div', 'err', (e.status === 0 || !e.detail) ? W['W-85'] : e.detail));
        return;
      }
      if (seq !== pvSeq || !S.loggedIn || !document.body.contains(checkBox)) { return; }
      pv = r; clear(checkBox);
      listOf(r.items).forEach(function (row) {
        var d = el('div', 'kv');
        d.appendChild(bdi(row.name || ''));
        if (row.parts && row.parts.length) { d.appendChild(el('span', 'k', row.parts.join('・'))); }
        checkBox.appendChild(d);
      });
      var to = el('div', 'kv'); to.appendChild(el('span', 'k', L.giveTo));
      var tn = el('span'); tn.appendChild(bdi((r.recipient && r.recipient.port_name) || '—')); to.appendChild(tn);
      checkBox.appendChild(to);
      checkBox.appendChild(kv(L.giveAt, fmtDT(r.created_at)));
      var fp = el('div', 'kv'); fp.appendChild(el('span', 'k', L.receiptFp)); fp.appendChild(el('span', 'mono', String(r.fingerprint || '').slice(0, 16)));
      checkBox.appendChild(fp);
      var fold = el('details', 'fold'); fold.appendChild(el('summary', null, L.receiptFp));
      fold.appendChild(el('div', 'mono', String(r.fingerprint || ''))); checkBox.appendChild(fold);
      give.disabled = !(S.status && S.status.port_paired);
    }

    function paintChoose() {
      clear(chooseBox);
      chooseBox.appendChild(el('h3', null, L.stmtFinal));
      var fin = data.stmts.filter(function (s) { return s.finalized_at; });
      if (!fin.length) { chooseBox.appendChild(line(W['W-83'])); }
      fin.forEach(function (s) {
        var id = s.item_id || s.id;
        var lb = el('label', 'pick'); var cb = el('input'); cb.type = 'checkbox'; cb.checked = S.hand.stmtId === id;
        cb.addEventListener('change', function () { S.hand.stmtId = cb.checked ? id : null; paintChoose(); refreshPreview(); });
        var sp = el('span'); sp.appendChild(bdi(String(s.text || '').slice(0, 60))); add(lb, cb, sp); chooseBox.appendChild(lb);
      });
      chooseBox.appendChild(el('h3', null, L.insertedTitle));
      var recs = data.recs.filter(function (r) { return r.kind !== 'reply'; });
      if (!recs.length) { chooseBox.appendChild(line(W['W-83'])); }
      recs.forEach(function (r) {
        var blk = el('div', 'rec-item'); var t = el('div', 'rec-title'); t.appendChild(bdi(toName(r))); blk.appendChild(t);
        var row = el('div', 'btnrow');
        PARTS.forEach(function (p) {
          if (p === 'derived' && !r.has_derived) { return; }
          if (p === 'annotations' && !(r.annotations && r.annotations.length)) { return; }
          if (p === 'subject_fields' && !(r.subject && (r.subject.author_role || r.subject.written_at || r.subject.procedure))) { return; }
          var lb = el('label', 'pick'); var cb = el('input'); cb.type = 'checkbox';
          cb.checked = !!(S.hand.sel[r.record_id] && S.hand.sel[r.record_id][p]);
          cb.addEventListener('change', function () { S.hand.sel[r.record_id] = S.hand.sel[r.record_id] || {}; S.hand.sel[r.record_id][p] = cb.checked; refreshPreview(); });
          add(lb, cb, el('span', null, L.partNames[p])); row.appendChild(lb);
        });
        blk.appendChild(row); chooseBox.appendChild(blk);
      });
    }
    function paintPast(rows) {
      clear(pastBox);
      if (!rows.length) { pastBox.appendChild(line(W['W-83'])); return; }
      rows.forEach(function (h) { pastBox.appendChild(pastItem(h)); });
    }
    async function loadAll() {
      var rr = await Promise.all([
        api('GET', '/api/records').then(listOf, function () { return []; }),
        api('GET', '/api/statements').then(listOf, function () { return []; }),
        api('GET', '/api/handoffs').then(listOf, function () { return null; })
      ]);
      if (!S.loggedIn || !document.body.contains(chooseBox)) { return; }
      data.recs = rr[0]; data.stmts = rr[1];
      paintChoose(); refreshPreview();
      if (rr[2] === null) { clear(pastBox); pastBox.appendChild(el('div', 'err', W['W-85'])); } else { paintPast(rr[2]); }
    }

    give.addEventListener('click', async function () {
      if (!pv) { return; }
      give.disabled = true; clear(resultBox);
      var body = { statement_id: S.hand.stmtId, records: chosenItems(), bundle_id: pv.bundle_id, created_at: pv.created_at, expected_fingerprint: pv.fingerprint };
      var box;
      try {
        var r = await api('POST', '/api/handoffs', body, 120000);
        var rc = r.receipt || {};
        var okSend = rc.status === 'confirmed' || rc.status === 'unconfirmed';
        if (!okSend) { box = el('div', 'err'); box.textContent = L.giveFail; }
        else {
          box = el('div', 'result');
          box.appendChild(el('h3', null, L.receiptTitle));
          box.appendChild(kv(L.receiptNo, rc.receipt_id));
          box.appendChild(kv(L.receiptAt, fmtDT(rc.received_at)));
          box.appendChild(kv(L.receiptPort, rc.port_name));
          var fpRow = el('div', 'kv'); fpRow.appendChild(el('span', 'k', L.receiptFp));
          fpRow.appendChild(el('span', 'mono', String(r.fingerprint || '').slice(0, 16)));
          fpRow.appendChild(rc.status === 'confirmed' ? tag(L.same, 'same') : el('span', 'err', L.diff));
          box.appendChild(fpRow);
          var fold = el('details', 'fold'); fold.appendChild(el('summary', null, L.receiptFp));
          fold.appendChild(el('div', 'mono', String(r.fingerprint || ''))); box.appendChild(fold);
        }
        resultBox.appendChild(box);
        try { paintPast(listOf(await api('GET', '/api/handoffs'))); } catch (e2) { /* 控えの一覧は あとで読める */ }
        if (okSend) {
          /* 送れた束の指紋を、確かめの枠にそのまま残す（新しい束を作って別の指紋を見せない決まり）。
             えらび直したときだけ refreshPreview が走り、新しい束になる。 */
          pv = null; give.disabled = true;
          S.hand.sel = {}; S.hand.stmtId = null; paintChoose();
          checkBox.appendChild(line(L.giveDone));
        }
        /* 上の枠を描き直した後に寄せる（描き直しで箱が下へずれるのを防ぐ） */
        requestAnimationFrame(function () { box.scrollIntoView({ block: 'nearest' }); });
        if (okSend) { return; }
      } catch (e) {
        box = el('div', 'err');
        box.textContent = (e.status === 409 || e.status === 400 || e.status === 404 || e.status === 413) && e.detail ? e.detail : L.giveFail;
        resultBox.appendChild(box);
        box.scrollIntoView({ block: 'nearest' });
      }
      refreshPreview();
    });
    paintChoose();
    refreshPreview();
    loadAll();
  }

  function pastItem(h) {
    var b = h.bundle || {}, rc = h.receipt || {};
    var it = el('div', 'rec-item');
    var t = el('div', 'rec-title');
    t.appendChild(el('span', 'mono', fmtDT(b.created_at)));
    var to = el('span'); to.appendChild(bdi(rc.port_name || '')); t.appendChild(to);
    if (rc.status === 'unconfirmed') { t.appendChild(tag(L.diff, 'unconfirmed')); }
    if (rc.status === 'unsent') { t.appendChild(tag(L.giveFail, 'unconfirmed')); }
    it.appendChild(t);
    var m = el('div', 'rec-meta');
    m.appendChild(el('span', null, L.pastItems + ' ' + (b.item_count !== undefined ? b.item_count : '')));
    var no = el('span'); no.appendChild(document.createTextNode(L.receiptNo + ' ')); no.appendChild(bdi(rc.receipt_id || '')); m.appendChild(no);
    it.appendChild(m);
    return it;
  }

  /* ================================================================
     器の約束（6.6）
     ================================================================ */
  async function openPromise() {
    var wrap = el('div');
    wrap.appendChild(el('p', null, W['W-161']));
    function list(title, items) {
      wrap.appendChild(el('h3', null, title));
      var ul = el('ul'); items.forEach(function (s) { ul.appendChild(el('li', null, s)); }); wrap.appendChild(ul);
    }
    list(L.promiseDoesTitle, L.promiseDoes);
    list(L.promiseDoesntTitle, L.promiseDoesnt);
    wrap.appendChild(el('h3', null, L.promiseSendTitle));
    wrap.appendChild(el('p', null, L.promiseSend));
    wrap.appendChild(el('h3', null, L.promiseFullTitle));
    var full = el('div'); wrap.appendChild(full);
    openModal(W['W-160'], wrap);
    var items = [];
    try { items = listOf(await api('GET', '/api/prompts')); } catch (e) { items = []; }
    if (!items.length) { full.appendChild(el('div', 'err', W['W-163'])); return; }
    items.forEach(function (p) {
      full.appendChild(el('div', 'rec-meta', (L.readerLabels[p.name] || p.name) + '　' + W['W-162a'] + p.version + W['W-162b'] + p.decided_on));
      full.appendChild(el('div', 'longbox', p.text));
    });
  }

  /* ================================================================
     右の帯（6）
     ================================================================ */
  function refreshCondBar() {
    var bar = $('condbar');
    if (!bar) { return; }
    clear(bar);
    L.condGroups.forEach(function (g) {
      var b = el('button', 'chip-btn', S.cond[g.key]); b.type = 'button';
      b.title = g.label; b.setAttribute('aria-label', g.label + ' ' + S.cond[g.key]);
      b.addEventListener('click', function () { goView('renshu'); });
      bar.appendChild(b);
    });
  }

  function buildTier(name) {
    var body = $('rail-body');
    clear(body);
    var t = el('div', 'tier');
    t.appendChild(el('div', 'tier-head', W['W-125'][name]));
    var vis = el('div', 'visline');
    vis.appendChild(el('span', null, W['W-126']));
    vis.appendChild(linkbtn(W['W-151'], openVisible));
    vis.appendChild(linkbtn(W['PROMISE-LINK'], openPromise));
    t.appendChild(vis);
    if (name === 'kako') { t.appendChild(el('div', 'note calm tier-note', noteKako)); }
    if (name === 'renshu') { var bar = el('div', 'condbar'); bar.id = 'condbar'; t.appendChild(bar); }
    var log = el('div', 'tier-log'); log.id = 'tier-log'; log.setAttribute('role', 'log');
    t.appendChild(log);
    var foot = el('div', 'tier-foot');
    var state = el('div', 'tier-state'); state.id = 'tier-state'; state.setAttribute('role', 'status');
    var ta = el('textarea', 'tier-in'); ta.id = 'tier-in'; ta.placeholder = W['W-130']; ta.setAttribute('aria-label', W['W-130']);
    ta.value = S.drafts[name] || '';
    var row = el('div', 'tier-btns');
    foot.appendChild(state); foot.appendChild(ta);
    if (name === 'seiri') {
      state.textContent = L.seiriState;
      row.appendChild(linkbtn(L.seiriGo, function () { goView('seiri'); }, 'body-size'));
      row.appendChild(btn(L.arrangeBtn, 'btn-second sendbtn', function () { goView('seiri'); }));
    }
    if (name === 'kako') {
      row.appendChild(btn(L.kakoEnd, 'btn-second sendbtn', openKakoEnd));
    }
    if (name === 'renshu') { state.textContent = W['W-136']; }
    var send = btn(W['W-134'], 'btn-main btn-send sendbtn', function () { sendTier(name); });
    send.id = 'tier-send';
    row.appendChild(send);
    foot.appendChild(row);
    if (name === 'renshu' || name === 'seiri') { foot.appendChild(el('p', 'tier-note-s', W['W-138'])); }
    t.appendChild(foot);
    body.appendChild(t);
    ta.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' && ev.altKey) { ev.preventDefault(); sendTier(name); } });
    ta.addEventListener('input', function () { S.drafts[name] = ta.value; });
    paintLog(name);
    if (name === 'renshu') { refreshCondBar(); }
  }

  function paintLog(name) {
    var log = $('tier-log');
    if (!log) { return; }
    clear(log);
    var msgs = S.chat[name];
    if (!msgs.length) {
      var ef = figure('koto', 'fig-64');
      var es = el('div', 'empty-s', W['W-139']);
      if (ef) { var ew = el('div', 'empty-wrap'); add(ew, ef, es); log.appendChild(ew); }
      else { log.appendChild(es); }
      return;
    }
    msgs.forEach(function (m) { log.appendChild(msgNode(m)); });
    scrollLogBottom();
  }

  function msgNode(m) {
    var n = el('div', 'msg ' + m.who);
    if (m.who === 'me') {
      n.appendChild(el('div', 'msg-head', fmtTime(m.at)));
      n.appendChild(document.createTextNode(m.text));
      return n;
    }
    if (m.who === 'sys') {
      n.appendChild(document.createTextNode(m.text));
      if (m.keep) { n.appendChild(keepRow(m)); }
      return n;
    }
    var head = el('div', 'msg-head');
    head.appendChild(bdi(W['W-141'])); head.appendChild(document.createTextNode('　' + fmtTime(m.at)));
    n.appendChild(head);
    if (m.readback !== undefined && m.readback !== null) {
      var rb = el('div', 'readback');
      rb.appendChild(el('span', 'tag tag-person readback-tag', L.yourText));
      var rt = el('div', 'rb-text'); rt.textContent = m.readback; rb.appendChild(rt);
      n.appendChild(rb);
    }
    if (m.question) { n.appendChild(el('div', 'q-text', m.question)); }
    if (m.turnId && m.ask === 'open') {
      var ask = el('div', 'markrow');
      ask.appendChild(el('span', null, L.contOrStop));
      var cont = btn(L.keepGoing, 'btn-second sendbtn', function () { m.ask = 'continued'; paintLog('renshu'); var t = $('tier-in'); if (t) { t.focus(); } });
      var stop = btn(L.doRead, 'btn-second sendbtn', function () { m.ask = 'stopped'; paintLog('renshu'); });
      add(ask, cont, stop);
      n.appendChild(ask);
    } else if (m.turnId && m.ask === 'stopped') {
      n.appendChild(marksRow(m));
    }
    var foot = el('div', 'msg-foot');
    foot.textContent = 'モデル: ' + (m.model || '—') + ' ・ 指示の版: ' + (m.ver || '—') + ' ・ のこしていません';
    n.appendChild(foot);
    return n;
  }
  function disableRow(row) { Array.prototype.forEach.call(row.querySelectorAll('button'), function (b) { b.disabled = true; }); }

  function pushMsg(tier, m) {
    S.chat[tier].push(m);
    if (S.rail === tier) { paintLog(tier); }
  }

  function marksRow(m) {
    var row = el('div', 'markrow');
    L.marks.forEach(function (p) {
      var b = btn(p[1], 'btn-second sendbtn', async function () {
        disableRow(row);
        try {
          await api('POST', '/api/practice/marks', { turn_id: m.turnId, mark: p[0] });
          m.ask = 'done';
          S.chat.renshu.push({ who: 'sys', text: L.markDone(p[0], m.condText || condText(S.cond)) });
          S.chat.renshu.push({ who: 'sys', text: L.keepAsk, keep: true });
          /* 本文の「条件ごとの 回数」を読み直す（印を押したら回数が 1 増えるのが見える） */
          var sb = document.getElementById('summary-box');
          if (sb && S.view === 'renshu') { loadSummary(sb); }
        } catch (e) {
          if (S.loggedIn) { S.chat.renshu.push({ who: 'sys', text: L.markFail }); }
        }
        if (S.loggedIn && S.rail === 'renshu') { paintLog('renshu'); }
      });
      row.appendChild(b);
    });
    return row;
  }

  function keepRow(m) {
    var row = el('div', 'markrow');
    var no = btn(L.keepNo, 'btn-second sendbtn', function () { m.keep = false; paintLog('renshu'); });
    var yes = btn(L.keepYes, 'btn-second sendbtn'); yes.disabled = true; yes.title = L.keepYesSoon;
    add(row, no, yes, el('span', 'tiny', L.keepYesSoon));
    return row;
  }

  function openKakoEnd() {
    var wrap = el('div');
    wrap.appendChild(el('p', null, L.kakoAsk));
    var row = el('div', 'btnrow');
    var no = btn(L.keepNo, 'btn-main', function () { S.chat.kako = []; S.drafts.kako = ''; var ta = $('tier-in'); if (ta && S.rail === 'kako') { ta.value = ''; } paintLog('kako'); h.close(); });
    var yes = btn(L.keepYes, 'btn-second'); yes.disabled = true;
    add(row, no, yes); wrap.appendChild(row);
    wrap.appendChild(line(L.keepYesSoon, 'tiny'));
    var h = openModal(L.kakoEnd, wrap, { cls: 'narrow', focus: no });
  }

  function openVisible() {
    var wrap = el('div');
    add(wrap, el('p', null, W['W-152']), el('p', null, S.rail === 'kako' ? L.kakoLocal : W['W-153']));
    openModal(W['W-126'].replace(/[:：].*$/, ''), wrap, { cls: 'narrow' });
  }

  async function sendTier(name) {
    var ta = $('tier-in');
    if (!ta || S.sending) { return; }
    var text = ta.value;
    if (!text.trim()) { return; }
    if (name === 'kako') {
      ta.value = ''; S.drafts.kako = '';
      if (!S.chat.kako.length) { S.chat.kako.push({ who: 'sys', text: L.kakoLocal }); }
      pushMsg('kako', { who: 'me', text: text, at: new Date().toISOString() });
      return;
    }
    if (name === 'seiri') {
      ta.value = ''; S.drafts.seiri = '';
      var cur = S.stmt.sections.trouble;
      S.stmt.sections.trouble = cur ? cur + '\n' + text : text;
      pushMsg('seiri', { who: 'me', text: text, at: new Date().toISOString() });
      pushMsg('seiri', { who: 'sys', text: L.seiriAdded });
      if (S.view === 'seiri') { showView('seiri', true); }
      return;
    }
    // renshu: Claude に送る
    if (S.status && S.status.claude === 'no_key') { pushMsg('renshu', { who: 'sys', text: L.noKey }); return; }
    S.sending = true;
    var send = $('tier-send'); if (send) { send.disabled = true; }
    var state = $('tier-state'); if (state) { state.textContent = W['W-133']; }
    ta.value = ''; S.drafts.renshu = '';
    var cond = copy(S.cond);
    pushMsg('renshu', { who: 'me', text: text, at: new Date().toISOString() });
    try {
      var r = await api('POST', '/api/practice/turns', { conditions: cond, text: text });
      pushMsg('renshu', {
        who: 'them', at: new Date().toISOString(), readback: r.readback, question: r.question || null,
        turnId: r.turn_id, ask: 'open', model: r.demo ? ((r.model || '') + '（記録）') : r.model, ver: r.prompt_version || r.instruction_version, condText: condText(cond)
      });
    } catch (e) {
      if (S.loggedIn) { pushMsg('renshu', { who: 'sys', text: W['W-142'] }); }
    }
    S.sending = false;
    send = $('tier-send'); if (send) { send.disabled = false; }
    state = $('tier-state'); if (state) { state.textContent = W['W-136']; }
  }

  /* ================================================================
     つなぎ込み
     ================================================================ */
  function wire() {
    $('gate-form').addEventListener('submit', onGateSubmit);
    $('btn-logout').addEventListener('click', function () { doLogout(false); });
    $('btn-logout-left').addEventListener('click', function () { doLogout(false); });
    $('btn-promise-left').addEventListener('click', openPromise);
    var nav = document.querySelectorAll('#nav .nav-btn');
    Array.prototype.forEach.call(nav, function (b) { b.addEventListener('click', function () { goView(b.getAttribute('data-view')); }); });

    $('btn-leftmin').addEventListener('click', function () { ui.leftMin = !ui.leftMin; saveUi(); applyLayout(); });
    $('btn-railmin').addEventListener('click', function () { ui.railMin = !ui.railMin; saveUi(); applyLayout(); if (!ui.railMin) { scrollLogBottom(); } });
    $('btn-chatback').addEventListener('click', function () { ui.leftMin = true; ui.railMin = false; saveUi(); applyLayout(); scrollLogBottom(); });
    $('btn-showmain').addEventListener('click', function () {
      ui.railMin = true; saveUi(); applyLayout(); window.scrollTo(0, 0); $('main').scrollTop = 0;
      try { $('btn-chatback').focus(); } catch (e) { /* 何もしない */ }
    });
    $('rail-sel').addEventListener('change', function () {
      if (S.rail === 'kako') { S.chat.kako = []; S.drafts.kako = ''; }   // 過去の話は、段を替えるとのこらない
      var next = $('rail-sel').value;
      var prev = $('tier-in'); if (prev) { S.drafts[S.rail] = prev.value; }
      S.rail = next; ui.sel = next; saveUi();
      buildTier(next);
    });
    $('btn-reload').addEventListener('click', async function () {
      var b = $('btn-reload'); b.disabled = true;
      var work = Promise.all([refreshStatus()]);
      await Promise.race([work, new Promise(function (r) { setTimeout(r, 4000); })]);
      if (S.loggedIn) { showView(S.view, true); buildTier(S.rail); }
      b.disabled = false;
    });

    // 幅をかえる取っ手
    var grip = $('rail-grip'), rail = $('rail'), drag = null;
    grip.addEventListener('pointerdown', function (ev) {
      drag = { x: ev.clientX, w: rail.getBoundingClientRect().width };
      rail.classList.add('dragging');
      try { grip.setPointerCapture(ev.pointerId); } catch (e) { /* 何もしない */ }
      ev.preventDefault();
    });
    grip.addEventListener('pointermove', function (ev) {
      if (!drag) { return; }
      var cap = Math.floor(window.innerWidth * 0.6);
      var w = Math.max(300, Math.min(cap, drag.w + (drag.x - ev.clientX)));
      rail.style.setProperty('--railw', w + 'px'); drag.now = w;
    });
    function endDrag() {
      if (!drag) { return; }
      rail.classList.remove('dragging');
      if (drag.now) { ui.railW = Math.round(drag.now); saveUi(); }
      drag = null;
    }
    grip.addEventListener('pointerup', endDrag);
    grip.addEventListener('pointercancel', endDrag);

    window.addEventListener('resize', function () { if (S && S.loggedIn) { applyLayout(); } });
    document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') { closeAllModals(); } });
    ['click', 'keydown', 'scroll', 'touchstart', 'pointerdown'].forEach(function (name) {
      document.addEventListener(name, onActivity, true);
    });
  }

  function start() {
    if (!BRAND_FIGURES) { document.body.setAttribute('data-figures', '0'); }
    paintNavIcons();
    wire(); boot();
  }
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', start); } else { start(); }
})();
