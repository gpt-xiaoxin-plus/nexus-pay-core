"""Offline Burp XML importer for captured GoPay/Gojek protocol traffic.

This module intentionally keeps captured traffic offline and redacted. It
decodes Burp items, extracts request/response shapes, and summarizes endpoint
usage without preserving bearer tokens, cookies, OTPs, PINs, phone numbers, or
other raw credentials.
"""
from __future__ import annotations

import base64
import json
import re
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit


SENSITIVE_HEADER_RE = re.compile(
    r"(^authorization$|cookie|token|secret|signature|x-e[123]$|verification)",
    re.IGNORECASE,
)
SENSITIVE_KEY_RE = re.compile(
    r"(token|secret|authorization|password|passwd|pin|otp|code|phone|mobile|email|"
    r"name|uuid|user[_-]?id|customer[_-]?id|account[_-]?id|session|device|unique)",
    re.IGNORECASE,
)
SAFE_METADATA_KEYS = {
    "code_length",
    "otp_length",
    "pin_length",
    "length",
}
FULL_URL_RE = re.compile(r"""https?://[^\s"'<>`\)\]]+""")
PATH_LITERAL_RE = re.compile(
    r"(?<![A-Za-z0-9_])/(?:api/|v\d+/|goto-auth/|cvs/|snap/|gojek/|courier/|"
    r"litmus/|bff/|paylater/)[A-Za-z0-9._~:/?&={}\-,]*"
)
TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".txt",
    ".bat",
    ".ps1",
}
SKIP_FILENAMES = {
    "gopay_protocol_inventory.json",
    "gopay_protocol_inventory.md",
    "package-lock.json",
    "protocol_offline_dataset.json",
    "protocol_offline_report.md",
    "protocol_vnext.json",
    "protocol_vnext.md",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Pipfile.lock",
}
PROTOCOL_HOST_RE = re.compile(
    r"(^|\.)(gojekapi\.com|gopayapi\.com|goto-products\.com|midtrans\.com|"
    r"stripe\.com|chatgpt\.com|openai\.com|paypal\.com|paypalobjects\.com|"
    r"herosms\.com|sms-activate\.org|5sim\.net)$",
    re.IGNORECASE,
)


def safe_urlsplit(url: str) -> SplitResult | None:
    try:
        return urlsplit(url)
    except ValueError:
        return None


def decode_burp_blob(text: str | None, is_base64: bool) -> bytes:
    """Decode a Burp request/response blob."""
    raw = (text or "").strip()
    if not raw:
        return b""
    if not is_base64:
        return raw.encode("utf-8", errors="replace")
    return base64.b64decode(raw)


def bytes_to_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def split_http_message(data: bytes) -> tuple[str, dict[str, str], bytes]:
    """Split a raw HTTP message into first line, headers, and body bytes."""
    if not data:
        return "", {}, b""

    marker = b"\r\n\r\n"
    if marker in data:
        head, body = data.split(marker, 1)
        lines = head.split(b"\r\n")
    elif b"\n\n" in data:
        head, body = data.split(b"\n\n", 1)
        lines = head.split(b"\n")
    else:
        lines = data.splitlines()
        body = b""

    first_line = bytes_to_text(lines[0]).strip() if lines else ""
    headers: dict[str, str] = {}
    for line in lines[1:]:
        s = bytes_to_text(line)
        if ":" not in s:
            continue
        key, value = s.split(":", 1)
        headers[key.strip()] = value.strip()
    return first_line, headers, body


def redact_header_value(name: str, value: str) -> str:
    if SENSITIVE_HEADER_RE.search(name):
        return "<redacted>"
    return value


def redact_json_value(key: str, value: Any) -> Any:
    if key.lower() in SAFE_METADATA_KEYS:
        return value
    if SENSITIVE_KEY_RE.search(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {k: redact_json_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_json_value(key, v) for v in value[:3]]
    return value


def json_shape(value: Any) -> Any:
    """Return a compact structural description for a JSON value."""
    if isinstance(value, dict):
        return {k: json_shape(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        if not value:
            return []
        return [json_shape(value[0])]
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


def parse_body_shape(body: bytes, headers: dict[str, str]) -> dict[str, Any]:
    content_type = ""
    for k, v in headers.items():
        if k.lower() == "content-type":
            content_type = v.lower()
            break

    stripped = body.strip()
    if not stripped:
        return {"kind": "empty"}

    if "json" in content_type or stripped[:1] in (b"{", b"["):
        try:
            parsed = json.loads(bytes_to_text(stripped))
        except Exception:
            return {"kind": "text", "bytes": len(body)}
        return {
            "kind": "json",
            "shape": json_shape(parsed),
            "redacted_sample": redact_json_value("", parsed),
        }

    if "application/x-www-form-urlencoded" in content_type:
        return {"kind": "form", "bytes": len(body)}

    if content_type:
        return {"kind": content_type.split(";")[0], "bytes": len(body)}
    return {"kind": "binary_or_text", "bytes": len(body)}


def body_summary(body_info: dict[str, Any]) -> dict[str, Any]:
    """Compact body info for endpoint summaries without retaining sample values."""
    kind = body_info.get("kind", "unknown")
    if kind == "json":
        return {"kind": "json", "shape": body_info.get("shape")}
    result = {"kind": kind}
    if "bytes" in body_info:
        result["bytes"] = body_info["bytes"]
    return result


def normalize_endpoint(method: str, url: str, path: str) -> dict[str, str]:
    parsed = safe_urlsplit(url)
    host = parsed.netloc if parsed else ""
    clean_path = (parsed.path if parsed else "") or path or "/"
    return {
        "method": method.upper(),
        "host": host,
        "path": clean_path,
        "endpoint": f"{method.upper()} {host}{clean_path}",
    }


def parse_burp_xml(path: str | Path) -> list[dict[str, Any]]:
    """Parse Burp XML export into redacted per-item protocol records."""
    xml_path = Path(path)
    root = ET.parse(xml_path).getroot()
    records: list[dict[str, Any]] = []

    for idx, item in enumerate(root.findall("item"), start=1):
        url = (item.findtext("url") or "").strip()
        method = (item.findtext("method") or "").strip()
        path_text = (item.findtext("path") or "").strip()
        status_text = (item.findtext("status") or "").strip()
        host_text = (item.findtext("host") or "").strip()

        request_el = item.find("request")
        response_el = item.find("response")
        request_bytes = decode_burp_blob(
            request_el.text if request_el is not None else "",
            (request_el is not None and request_el.get("base64") == "true"),
        )
        response_bytes = decode_burp_blob(
            response_el.text if response_el is not None else "",
            (response_el is not None and response_el.get("base64") == "true"),
        )

        req_line, req_headers, req_body = split_http_message(request_bytes)
        resp_line, resp_headers, resp_body = split_http_message(response_bytes)
        endpoint = normalize_endpoint(method, url, path_text)
        if not endpoint["host"]:
            endpoint["host"] = host_text
            endpoint["endpoint"] = f"{endpoint['method']} {host_text}{endpoint['path']}"

        records.append({
            "index": idx,
            "time": item.findtext("time") or "",
            "url": url,
            "method": endpoint["method"],
            "host": endpoint["host"],
            "path": endpoint["path"],
            "endpoint": endpoint["endpoint"],
            "status": int(status_text) if status_text.isdigit() else None,
            "request": {
                "line": req_line,
                "headers": {k: redact_header_value(k, v) for k, v in sorted(req_headers.items())},
                "header_names": sorted(req_headers),
                "body": parse_body_shape(req_body, req_headers),
            },
            "response": {
                "line": resp_line,
                "headers": {k: redact_header_value(k, v) for k, v in sorted(resp_headers.items())},
                "header_names": sorted(resp_headers),
                "body": parse_body_shape(resp_body, resp_headers),
            },
        })

    return records


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    for rec in records:
        key = rec["endpoint"]
        if key not in grouped:
            grouped[key] = {
                "endpoint": key,
                "method": rec["method"],
                "host": rec["host"],
                "path": rec["path"],
                "count": 0,
                "statuses": {},
                "request_header_names": set(),
                "response_header_names": set(),
                "request_body_shapes": [],
                "response_body_shapes": [],
            }
        entry = grouped[key]
        entry["count"] += 1
        status = rec.get("status")
        if status is not None:
            entry["statuses"][str(status)] = entry["statuses"].get(str(status), 0) + 1
        entry["request_header_names"].update(rec["request"]["header_names"])
        entry["response_header_names"].update(rec["response"]["header_names"])

        req_shape = body_summary(rec["request"]["body"])
        if req_shape not in entry["request_body_shapes"]:
            entry["request_body_shapes"].append(req_shape)
        resp_shape = body_summary(rec["response"]["body"])
        if resp_shape not in entry["response_body_shapes"]:
            entry["response_body_shapes"].append(resp_shape)

    endpoints = []
    host_counts: dict[str, int] = defaultdict(int)
    for entry in grouped.values():
        host_counts[entry["host"]] += entry["count"]
        entry["request_header_names"] = sorted(entry["request_header_names"])
        entry["response_header_names"] = sorted(entry["response_header_names"])
        endpoints.append(entry)

    endpoints.sort(key=lambda e: (-e["count"], e["host"], e["path"], e["method"]))
    return {
        "total_items": len(records),
        "total_endpoints": len(endpoints),
        "hosts": dict(sorted(host_counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        "endpoints": endpoints,
    }


def import_capture(path: str | Path) -> dict[str, Any]:
    records = parse_burp_xml(path)
    return {
        "source": str(Path(path).expanduser()),
        "summary": summarize_records(records),
        "records": records,
    }


def write_report(report: dict[str, Any], out_path: str | Path | None = None) -> str:
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if out_path:
        Path(out_path).expanduser().write_text(text + "\n", encoding="utf-8")
    return text


def endpoint_key(host: str, path: str) -> str:
    return f"{normalize_host(host)}{path}"


def endpoint_key_from_url(url: str) -> str:
    parsed = safe_urlsplit(url)
    if parsed is None:
        return ""
    if not parsed.netloc:
        return ""
    if not is_protocol_host(parsed.netloc):
        return ""
    return endpoint_key(parsed.netloc, parsed.path or "/")


def normalize_host(host: str) -> str:
    return host.split("@")[-1].split(":")[0].strip().lower().rstrip(".")


def normalize_url_literal(url: str) -> str:
    parsed = safe_urlsplit(url)
    if parsed is None:
        return ""
    if not parsed.netloc:
        return ""
    host = normalize_host(parsed.netloc)
    path = parsed.path or "/"
    return f"{parsed.scheme or 'https'}://{host}{path}"


def is_protocol_host(host: str) -> bool:
    normalized = normalize_host(host)
    return bool(PROTOCOL_HOST_RE.search(normalized))


def _iter_text_files(root: Path):
    skip_dirs = {
        ".git",
        ".venv",
        "__pycache__",
        "node_modules",
        "venv",
    }
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.name in SKIP_FILENAMES:
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS:
            yield path


def extract_protocol_literals(root: str | Path) -> dict[str, Any]:
    """Extract URL/path literals from a code tree for offline comparison."""
    base = Path(root).expanduser().resolve()
    files = []
    urls: dict[str, set[str]] = defaultdict(set)
    paths: dict[str, set[str]] = defaultdict(set)
    endpoint_keys: set[str] = set()
    invalid_urls: dict[str, set[str]] = defaultdict(set)

    if not base.exists():
        return {
            "root": str(base),
            "files_scanned": 0,
            "urls": [],
            "paths": [],
            "endpoint_keys": [],
            "invalid_urls": [],
        }

    for path in _iter_text_files(base):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        rel = str(path.relative_to(base))
        files.append(rel)

        for raw in FULL_URL_RE.findall(text):
            url = raw.rstrip(".,;")
            parsed = safe_urlsplit(url)
            if parsed is None:
                invalid_urls[url].add(rel)
                continue
            if not is_protocol_host(parsed.netloc):
                continue
            normalized_url = normalize_url_literal(url)
            if not normalized_url:
                continue
            urls[normalized_url].add(rel)
            key = endpoint_key_from_url(url)
            if key:
                endpoint_keys.add(key)
            if parsed.path and parsed.path != "/":
                paths[parsed.path].add(rel)

        for raw in PATH_LITERAL_RE.findall(text):
            clean = raw.rstrip(".,;")
            paths[clean].add(rel)

    return {
        "root": str(base),
        "files_scanned": len(files),
        "urls": [
            {"value": value, "files": sorted(files_for_value)}
            for value, files_for_value in sorted(urls.items())
        ],
        "paths": [
            {"value": value, "files": sorted(files_for_value)}
            for value, files_for_value in sorted(paths.items())
        ],
        "endpoint_keys": sorted(endpoint_keys),
        "invalid_urls": [
            {"value": value, "files": sorted(files_for_value)}
            for value, files_for_value in sorted(invalid_urls.items())
        ],
    }


def _normalize_reference_roots(reference_root: str | Path | list[str | Path] | tuple[str | Path, ...] | None) -> list[str | Path]:
    if reference_root is None:
        return []
    if isinstance(reference_root, (list, tuple)):
        return [root for root in reference_root if str(root).strip()]
    if str(reference_root).strip():
        return [reference_root]
    return []


def _combine_code_sources(sources: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not sources:
        return None
    urls: dict[str, set[str]] = defaultdict(set)
    paths: dict[str, set[str]] = defaultdict(set)
    endpoint_keys: set[str] = set()
    files_scanned = 0
    roots = []

    for source in sources:
        root = source.get("root", "")
        roots.append(root)
        files_scanned += int(source.get("files_scanned", 0) or 0)
        endpoint_keys.update(source.get("endpoint_keys", []))
        for item in source.get("urls", []):
            value = item.get("value", "")
            for file_name in item.get("files", []):
                urls[value].add(f"{root}:{file_name}")
        for item in source.get("paths", []):
            value = item.get("value", "")
            for file_name in item.get("files", []):
                paths[value].add(f"{root}:{file_name}")

    return {
        "root": ";".join(roots),
        "roots": roots,
        "files_scanned": files_scanned,
        "urls": [
            {"value": value, "files": sorted(files_for_value)}
            for value, files_for_value in sorted(urls.items())
        ],
        "paths": [
            {"value": value, "files": sorted(files_for_value)}
            for value, files_for_value in sorted(paths.items())
        ],
        "endpoint_keys": sorted(endpoint_keys),
    }


def _compare_capture_to_source(
    capture_keys: set[str],
    capture_paths: set[str],
    source: dict[str, Any],
) -> dict[str, Any]:
    source_keys = set(source.get("endpoint_keys", []))
    source_paths = {p["value"] for p in source.get("paths", [])}
    return {
        "root": source.get("root", ""),
        "files_scanned": source.get("files_scanned", 0),
        "endpoint_keys": len(source_keys),
        "paths": len(source_paths),
        "capture_matched": sorted(capture_keys & source_keys),
        "capture_paths_matched": sorted(capture_paths & source_paths),
        "source_only": sorted(source_keys - capture_keys),
    }


def build_combined_dataset(
    capture_xml: str | Path,
    current_root: str | Path,
    reference_root: str | Path | list[str | Path] | tuple[str | Path, ...] | None = None,
) -> dict[str, Any]:
    """Bundle capture summary and code literal comparisons into one dataset."""
    capture = import_capture(capture_xml)
    capture_summary = capture["summary"]
    capture_keys = {
        endpoint_key(e["host"], e["path"])
        for e in capture_summary.get("endpoints", [])
    }
    capture_paths = {e["path"] for e in capture_summary.get("endpoints", [])}

    current = extract_protocol_literals(current_root)
    reference_roots = _normalize_reference_roots(reference_root)
    references = [extract_protocol_literals(root) for root in reference_roots]
    reference = _combine_code_sources(references)
    current_keys = set(current.get("endpoint_keys", []))
    reference_keys = set(reference.get("endpoint_keys", [])) if reference else set()
    current_paths = {p["value"] for p in current.get("paths", [])}
    reference_paths = {p["value"] for p in reference.get("paths", [])} if reference else set()

    comparison = {
        "capture_endpoint_keys": len(capture_keys),
        "current_endpoint_keys": len(current_keys),
        "reference_endpoint_keys": len(reference_keys),
        "capture_paths": len(capture_paths),
        "current_paths": len(current_paths),
        "reference_paths": len(reference_paths),
        "capture_matched_current": sorted(capture_keys & current_keys),
        "capture_matched_reference": sorted(capture_keys & reference_keys),
        "capture_matched_both": sorted(capture_keys & current_keys & reference_keys),
        "capture_paths_matched_current": sorted(capture_paths & current_paths),
        "capture_paths_matched_reference": sorted(capture_paths & reference_paths),
        "capture_paths_matched_both": sorted(capture_paths & current_paths & reference_paths),
        "capture_only": sorted(capture_keys - current_keys - reference_keys),
        "capture_paths_only": sorted(capture_paths - current_paths - reference_paths),
        "current_only": sorted(current_keys - capture_keys),
        "reference_only": sorted(reference_keys - capture_keys),
        "references": [
            _compare_capture_to_source(capture_keys, capture_paths, source)
            for source in references
        ],
    }

    return {
        "sources": {
            "capture_xml": str(Path(capture_xml).expanduser()),
            "current_root": str(Path(current_root).expanduser()),
            "reference_root": str(Path(reference_roots[0]).expanduser()) if reference_roots else "",
            "reference_roots": [
                str(Path(root).expanduser())
                for root in reference_roots
            ],
        },
        "capture_summary": capture_summary,
        "code_sources": {
            "current": current,
            "reference": reference,
            "references": references,
        },
        "comparison": comparison,
        "gopay_inventory": build_gopay_inventory(capture_summary, current, references),
    }


def classify_endpoint(host: str, path: str) -> str:
    host = normalize_host(host)
    if "goto-products.com" in host:
        if path.startswith("/cvs/"):
            return "gojek_signup_otp"
        if path.startswith("/goto-auth/"):
            return "gojek_auth"
        return "gojek_accounts"
    if "gojekapi.com" in host:
        if path.startswith("/v7/customers") or path.startswith("/gojek/"):
            return "gojek_customer"
        if path.startswith("/courier/") or path.startswith("/litmus/") or path.startswith("/v1/devices"):
            return "gojek_supporting"
        return "gojek_api"
    if "gopayapi.com" in host:
        if "/pins/" in path:
            return "gopay_pin"
        if "payment-options" in path or "wallet-card" in path:
            return "gopay_balance"
        if "linking" in path or "payment" in path:
            return "gopay_payment"
        return "gopay_app"
    if "midtrans.com" in host:
        return "midtrans"
    if "stripe.com" in host:
        return "stripe"
    if "chatgpt.com" in host or "openai.com" in host:
        return "openai_checkout"
    if "paypal.com" in host:
        return "paypal"
    if "herosms.com" in host or "sms-activate.org" in host or "5sim.net" in host:
        return "sms_provider"
    return "supporting"


def build_gopay_inventory(
    capture_summary: dict[str, Any],
    current: dict[str, Any],
    references: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a compact, redacted protocol inventory from capture + repos."""
    capture_items = []
    category_counts: dict[str, int] = defaultdict(int)
    for endpoint in capture_summary.get("endpoints", []):
        category = classify_endpoint(endpoint.get("host", ""), endpoint.get("path", ""))
        category_counts[category] += endpoint.get("count", 0)
        capture_items.append({
            "category": category,
            "endpoint": endpoint.get("endpoint", ""),
            "method": endpoint.get("method", ""),
            "host": endpoint.get("host", ""),
            "path": endpoint.get("path", ""),
            "count": endpoint.get("count", 0),
            "statuses": endpoint.get("statuses", {}),
            "request_body_shapes": endpoint.get("request_body_shapes", []),
            "response_body_shapes": endpoint.get("response_body_shapes", []),
        })

    code_sources = [current, *references]
    code_inventory = []
    for source in code_sources:
        for key in source.get("endpoint_keys", []):
            parsed = key.split("/", 1)
            host = parsed[0]
            path = "/" + parsed[1] if len(parsed) == 2 else "/"
            code_inventory.append({
                "root": source.get("root", ""),
                "category": classify_endpoint(host, path),
                "endpoint_key": key,
                "host": host,
                "path": path,
            })

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "boundary": "complete_protocol_inventory_with_sensitive_values_redacted",
        "capture_category_counts": dict(sorted(category_counts.items())),
        "capture_endpoints": capture_items,
        "code_endpoint_inventory": sorted(
            code_inventory,
            key=lambda item: (item["category"], item["host"], item["path"], item["root"]),
        ),
    }


def markdown_digest(dataset: dict[str, Any]) -> str:
    summary = dataset["capture_summary"]
    comp = dataset["comparison"]
    hosts = summary.get("hosts", {})
    top_endpoints = summary.get("endpoints", [])[:25]
    reference_roots = dataset["sources"].get("reference_roots") or []

    lines = [
        "# Offline Protocol Dataset",
        "",
        "## Sources",
        "",
        f"- Capture XML: `{dataset['sources']['capture_xml']}`",
        f"- Current repo: `{dataset['sources']['current_root']}`",
    ]
    if reference_roots:
        for root in reference_roots:
            lines.append(f"- Reference repo: `{root}`")
    else:
        lines.append(f"- Reference repo: `{dataset['sources']['reference_root']}`")

    lines.extend([
        "",
        "## Capture Summary",
        "",
        f"- Total items: {summary.get('total_items', 0)}",
        f"- Unique endpoints: {summary.get('total_endpoints', 0)}",
        "",
        "## Hosts",
        "",
    ])
    for host, count in hosts.items():
        lines.append(f"- `{host}`: {count}")

    lines.extend([
        "",
        "## Comparison",
        "",
        f"- Capture endpoint keys: {comp['capture_endpoint_keys']}",
        f"- Current code endpoint keys: {comp['current_endpoint_keys']}",
        f"- Reference code endpoint keys: {comp['reference_endpoint_keys']}",
        f"- Capture matched current: {len(comp['capture_matched_current'])}",
        f"- Capture matched reference: {len(comp['capture_matched_reference'])}",
        f"- Capture matched both: {len(comp['capture_matched_both'])}",
        f"- Capture paths matched current: {len(comp['capture_paths_matched_current'])}",
        f"- Capture paths matched reference: {len(comp['capture_paths_matched_reference'])}",
        f"- Capture paths matched both: {len(comp['capture_paths_matched_both'])}",
        "",
        "## Top Capture Endpoints",
        "",
    ])
    for endpoint in top_endpoints:
        lines.append(
            f"- {endpoint['count']}x `{endpoint['method']} {endpoint['host']}{endpoint['path']}` "
            f"statuses={endpoint['statuses']}"
        )

    lines.extend([
        "",
        "## Capture Endpoints Not Present As Full URL Literals",
        "",
    ])
    for key in comp["capture_only"][:50]:
        lines.append(f"- `{key}`")
    if len(comp["capture_only"]) > 50:
        lines.append(f"- ... {len(comp['capture_only']) - 50} more")

    ref_comparisons = comp.get("references") or []
    if ref_comparisons:
        lines.extend([
            "",
            "## Reference Repos",
            "",
        ])
        for ref in ref_comparisons:
            lines.append(
                f"- `{ref.get('root', '')}`: "
                f"endpoint_keys={ref.get('endpoint_keys', 0)}, "
                f"paths={ref.get('paths', 0)}, "
                f"capture_full_matches={len(ref.get('capture_matched', []))}, "
                f"capture_path_matches={len(ref.get('capture_paths_matched', []))}"
            )

    return "\n".join(lines) + "\n"


def inventory_markdown(dataset: dict[str, Any]) -> str:
    inventory = dataset.get("gopay_inventory", {})
    lines = [
        "# GoPay Protocol Inventory",
        "",
        f"- Generated at: `{inventory.get('generated_at', '')}`",
        f"- Boundary: `{inventory.get('boundary', '')}`",
        f"- Capture source: `{dataset.get('sources', {}).get('capture_xml', '')}`",
        "",
        "## Capture Categories",
        "",
    ]
    for category, count in inventory.get("capture_category_counts", {}).items():
        lines.append(f"- `{category}`: {count}")

    lines.extend([
        "",
        "## Capture Endpoints",
        "",
    ])
    for endpoint in inventory.get("capture_endpoints", []):
        lines.append(
            f"- `{endpoint['category']}` {endpoint['count']}x "
            f"`{endpoint['method']} {endpoint['host']}{endpoint['path']}` "
            f"statuses={endpoint['statuses']}"
        )

    lines.extend([
        "",
        "## Code Endpoint Inventory",
        "",
    ])
    for item in inventory.get("code_endpoint_inventory", [])[:250]:
        lines.append(
            f"- `{item['category']}` `{item['endpoint_key']}` "
            f"source=`{item['root']}`"
        )
    remaining = len(inventory.get("code_endpoint_inventory", [])) - 250
    if remaining > 0:
        lines.append(f"- ... {remaining} more")

    return "\n".join(lines) + "\n"


def write_combined_dataset(
    dataset: dict[str, Any],
    json_path: str | Path,
    markdown_path: str | Path | None = None,
    inventory_json_path: str | Path | None = None,
    inventory_markdown_path: str | Path | None = None,
) -> None:
    Path(json_path).expanduser().write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if markdown_path:
        Path(markdown_path).expanduser().write_text(markdown_digest(dataset), encoding="utf-8")
    if inventory_json_path:
        Path(inventory_json_path).expanduser().write_text(
            json.dumps(dataset.get("gopay_inventory", {}), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if inventory_markdown_path:
        Path(inventory_markdown_path).expanduser().write_text(
            inventory_markdown(dataset),
            encoding="utf-8",
        )
