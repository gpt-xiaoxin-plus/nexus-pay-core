from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone

TARGET_HOSTS = (
    "gopayapi.com",
    "gojekapi.com",
    "goto-products.com",
    "midtrans.com",
    "app.gopay.co.id",
)

TARGET_PATH_KEYWORDS = (
    "pin",
    "challenge",
    "otp",
    "token",
    "payment-options",
    "balances",
    "profiles",
    "security",
    "meter",
    "wallet",
    "festival",
    "envelope",
)


def _body_preview(content: bytes, limit: int = 20000) -> dict:
    if not content:
        return {"text": "", "base64": ""}
    data = content[:limit]
    try:
        text = data.decode("utf-8")
        return {"text": text, "base64": ""}
    except UnicodeDecodeError:
        return {"text": "", "base64": base64.b64encode(data).decode("ascii")}


def _headers(headers) -> dict:
    return {str(k): str(v) for k, v in headers.items()}


def response(flow):
    host = flow.request.pretty_host or ""
    path = flow.request.path or ""
    host_hit = any(x in host for x in TARGET_HOSTS)
    path_hit = any(x in path.lower() for x in TARGET_PATH_KEYWORDS)
    if not host_hit and not path_hit:
        return

    out = os.environ.get("GOPAY_CAPTURE_JSONL") or "captures/gopay_flows.jsonl"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    record = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "request": {
            "method": flow.request.method,
            "scheme": flow.request.scheme,
            "host": host,
            "port": flow.request.port,
            "path": path,
            "url": flow.request.pretty_url,
            "headers": _headers(flow.request.headers),
            "body": _body_preview(flow.request.raw_content or b""),
        },
        "response": {
            "status_code": flow.response.status_code if flow.response else None,
            "headers": _headers(flow.response.headers) if flow.response else {},
            "body": _body_preview(flow.response.raw_content or b"") if flow.response else {"text": "", "base64": ""},
        },
    }

    with open(out, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

