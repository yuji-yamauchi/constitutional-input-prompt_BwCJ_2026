# デモ素材（demo/）

## docs/
自作のダミー書類の SVG（通知表・診断書・個別支援計画・母子手帳の 1 ページ）。
果物の名と、ダミーの番号の型だけで作った物で、実在の様式・人・施設を写していません。右下に「自作のダミー（デモ用）」と入っています。
SVG は Claude に送れません（画像は jpeg / png / webp だけ）。デモで読み取りを見せるときは、画面に出して撮った png に直して使います。

## recorded/
鍵なしのデモ（`CIP_DEMO_MODE`）が返す、Claude の応答の記録。`<役>/default.json` が、記録の無い入力に返る応答です。
入力の sha256 の先頭 16 字の名の JSON が在れば、そちらが先に返ります。

いまの `default.json` は仮の物（手書き・`recorded_from_live: false`）です。作成者の鍵で `python3 -B -m app_src.tools.record_demo` を 1 回回すと、`demo/record_inputs.json` の入力で本物の Claude を呼び、応答を `recorded_from_live: true` で書き直します（`default.json` も置き換わります）。全部が本物の記録になると、画面の上の帯の字が「用意した 物です」から「録画用に記録した物です」に変わります。
