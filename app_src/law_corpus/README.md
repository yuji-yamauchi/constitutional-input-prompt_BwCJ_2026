# 法令集（law_corpus）

1 条 = 1 つの JSON ファイル。器は、ここにある JSON のうち `verified_by_person` が true の物だけを読みます。

## 形

| 欄 | 意味 |
|---|---|
| `id` | 条の id（英数字と `-` `_` だけ） |
| `law_name` | 法令名 |
| `article` | 条番号 |
| `text_verbatim` | 原文の写し（1 字も変えない） |
| `source_name` | 取得元の名（例: e-Gov 法令検索） |
| `retrieved_on` | 取得した日（YYYY-MM-DD） |
| `retrieved_by` | 取得した人の役（人の名は書かない） |
| `set_version` | 法令集の版 |
| `verified_by_person` | 人が原文と読み合わせた印（true / false） |
| `note` | 覚え書き（画面には出ない） |

上の 7 欄（`law_name` から `set_version` まで）が、束に添える条文の欄です。

## 決まり

- 原文は e-Gov 法令検索から人が写し、人が読み合わせて `verified_by_person` を true にします。
- true にする人 = 作成者（山内雄司）。
- Claude は条の id を返すだけです。画面に出る本文は、いつもこの JSON から出ます。
- `verified_by_person` が false の物、欄が欠けた物、読めない物は、画面に出ません。
- 名が `_` で始まる物は読みません（形の見本用）。
- 同じ id が 2 つ在るときは、どちらも読みません。
