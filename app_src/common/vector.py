# -*- coding: utf-8 -*-
"""common/vector.py — 検査用の束 V1（ダミーだけ）。指紋の固定値は取り決めの自己検査スクリプトと同じ。"""
import base64
from .contract import fingerprint, sha256_hex

EXPECTED_V1_FINGERPRINT = "bf9b6a54a38041a2bba7dbebeae05c9f3b8a3294d082d89b7f56fb84692acf02"
def vector_v1():
    original_bytes = b"dummy-image-bytes-not-a-real-picture"  # 本物の画像ではない（指紋の照合のためだけ）
    md = "# 通知表（自作のダミー）\n\n- こくご: がんばった\n- たいいく: たのしく とりくんだ\n"
    b = {
        "bundle_version": "cip-bundle-v1",
        "bundle_id": "00000000-0000-4000-8000-000000000011",
        "created_at": "2026-11-07T10:15:00+09:00",
        "sender": {"person_ref": "pr-00000000-0000-4000-8000-000000000021", "display_name": "もも"},
        "recipient": {"port_id": "port-reference-01", "port_name": "受け口（参照用）"},
        "items": [
            {
                "kind": "statement",
                "item_id": "00000000-0000-4000-8000-000000000031",
                "author": "person",
                "finalized_at": "2026-11-07T10:10:00+09:00",
                "sections": {
                    "trouble": "朝の時間に間に合わないことが続いている。",
                    "wish": "始まりの時間を少し遅くできるか相談したい。",
                    "grounds": ["00000000-0000-4000-8000-000000000032"],
                    "statutes": [
                        {
                            "law_name": "（法令名＝取得時に原文で確定）",
                            "article": "（条番号＝取得時に原文で確定）",
                            "text_verbatim": "（原文の写し＝取得時に e-Gov から）",
                            "source_name": "e-Gov 法令検索",
                            "retrieved_on": "2026-11-05",
                            "retrieved_by": "支援者（役）",
                            "set_version": "statutes-v1"
                        }
                    ]
                },
                "text": "朝の時間に間に合わないことが続いています。始まりの時間を少し遅くできるか、相談したいです。"
            },
            {
                "kind": "record",
                "item_id": "00000000-0000-4000-8000-000000000032",
                "record_name": "通知表（自作のダミー）",
                "parts": {
                    "original": {
                        "media_type": "image/jpeg",
                        "sha256": sha256_hex(original_bytes),
                        "bytes_base64": base64.b64encode(original_bytes).decode("ascii"),
                        "taken_at": "2026-11-06T18:00:00+09:00"
                    },
                    "derived": {
                        "label": "派生（Claude が読み取った写し。原本が正）",
                        "markdown": md,
                        "generated_at": "2026-11-06T18:01:00+09:00",
                        "sha256": sha256_hex(md.encode("utf-8"))
                    },
                    "subject_fields": {
                        "author_role": "学校",
                        "written_at": "2026-03-31",
                        "procedure": "学期の記録",
                        "confirmed_by_person": True
                    },
                    "annotations": [
                        {"text": "この学期は休みが多かった。", "written_at": "2026-11-06T18:05:00+09:00", "author": "person"}
                    ]
                }
            }
        ],
        "item_count": 2
    }
    b["fingerprint"] = fingerprint(b)
    return b


def receipt_for(b, port_id="port-reference-01", port_name="受け口（参照用）"):
    return {
        "receipt_version": "cip-receipt-v1",
        "receipt_id": "rc-00000000-0000-4000-8000-000000000041",
        "port_id": port_id,
        "port_name": port_name,
        "bundle_id": b["bundle_id"],
        "bundle_fingerprint": fingerprint(b),   # 受け口が自分で計算した値
        "item_count": b["item_count"],
        "received_at": "2026-11-07T10:15:03+09:00"
    }


def reply_v1(attest=True):
    rp = {
        "reply_version": "cip-reply-v1",
        "reply_id": "rp-00000000-0000-4000-8000-000000000051",
        "port_id": "port-reference-01",
        "port_name": "受け口（参照用）",
        "in_reply_to": "00000000-0000-4000-8000-000000000011",
        "text": "読みました。始まりの時間のことは、次に会うときに一緒に考えましょう。",
        "written_at": "2026-11-07T11:00:00+09:00",
        "author": {"role": "mentor", "attested_at": "2026-11-07T11:00:00+09:00"}
    }
    if attest is not None:
        rp["author"]["human_attestation"] = attest
    return rp
