"""Versioned offline GoPay protocol profile builder.

The profile is a stable, project-owned layer on top of the raw capture bundle:
it keeps the real-device capture as the source of truth, folds in code evidence
from reference repositories, and describes which parts are capture-backed,
code-backed, or still missing.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


PROFILE_VERSION = "gopay-protocol-vnext-2026-05-29"


REGISTRATION_FLOW = [
    ("login_probe", "POST", "/goto-auth/login/methods"),
    ("signup_otp_methods", "POST", "/cvs/v1/methods"),
    ("signup_otp_initiate", "POST", "/cvs/v1/initiate"),
    ("signup_otp_verify", "POST", "/cvs/v1/verify"),
    ("account_create", "POST", "/v7/customers/signup"),
    ("token_exchange", "POST", "/goto-auth/token"),
    ("pin_setup", "POST", "/api/v2/users/pins/setup/tokens"),
    ("profile_check", "GET", "/v1/users/profile"),
    ("balance_poll", "GET", "/v1/payment-options/balances"),
]


PAYMENT_FLOW = [
    ("midtrans_linking", "POST", "/snap/v3/accounts/{snap_token}/linking"),
    ("gopay_validate_reference", "POST", "/v1/linking/validate-reference"),
    ("gopay_user_consent", "POST", "/v1/linking/user-consent"),
    ("gopay_validate_otp", "POST", "/v1/linking/validate-otp"),
    ("gopay_validate_pin", "POST", "/v1/linking/validate-pin"),
    ("midtrans_charge", "POST", "/snap/v2/transactions/{snap_token}/charge"),
    ("gopay_payment_validate", "GET", "/v1/payment/validate"),
    ("gopay_payment_confirm", "POST", "/v1/payment/confirm"),
    ("gopay_payment_process", "POST", "/v1/payment/process"),
    ("midtrans_status", "GET", "/snap/v1/transactions/{snap_token}/status"),
]


def load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def _capture_by_path(dataset: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_path: dict[str, list[dict[str, Any]]] = {}
    for endpoint in dataset.get("capture_summary", {}).get("endpoints", []):
        by_path.setdefault(endpoint.get("path", ""), []).append(endpoint)
    return by_path


def _code_by_path(dataset: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    by_path: dict[str, list[dict[str, Any]]] = {}
    for item in dataset.get("gopay_inventory", {}).get("code_endpoint_inventory", []):
        by_path.setdefault(item.get("path", ""), []).append(item)
    return by_path


def _template_matches(path_template: str, candidate_path: str) -> bool:
    if "{" not in path_template:
        return path_template == candidate_path
    template_parts = path_template.strip("/").split("/")
    candidate_parts = candidate_path.strip("/").split("/")
    if len(template_parts) != len(candidate_parts):
        return False
    for expected, actual in zip(template_parts, candidate_parts):
        if expected.startswith("{") and expected.endswith("}"):
            continue
        if expected != actual:
            return False
    return True


def _code_matches_for_path(code_by_path: dict[str, list[dict[str, Any]]], path_template: str) -> list[dict[str, Any]]:
    matches = []
    for path, items in code_by_path.items():
        if _template_matches(path_template, path):
            matches.extend(items)
    return matches


def _flow_evidence(
    dataset: dict[str, Any],
    flow: list[tuple[str, str, str]],
) -> list[dict[str, Any]]:
    capture_by_path = _capture_by_path(dataset)
    code_by_path = _code_by_path(dataset)
    evidence = []
    for step_id, method, path in flow:
        capture_matches = [
            item for item in capture_by_path.get(path, [])
            if not method or item.get("method") == method
        ]
        code_matches = _code_matches_for_path(code_by_path, path)
        evidence.append({
            "id": step_id,
            "method": method,
            "path": path,
            "capture_backed": bool(capture_matches),
            "code_backed": bool(code_matches),
            "capture": capture_matches,
            "code": code_matches,
        })
    return evidence


def _reference_summary(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    refs = []
    for ref in dataset.get("comparison", {}).get("references", []):
        refs.append({
            "root": ref.get("root", ""),
            "files_scanned": ref.get("files_scanned", 0),
            "endpoint_keys": ref.get("endpoint_keys", 0),
            "paths": ref.get("paths", 0),
            "capture_full_matches": len(ref.get("capture_matched", [])),
            "capture_path_matches": len(ref.get("capture_paths_matched", [])),
            "matched_paths": ref.get("capture_paths_matched", []),
        })
    return refs


def build_protocol_profile(dataset: dict[str, Any]) -> dict[str, Any]:
    registration = _flow_evidence(dataset, REGISTRATION_FLOW)
    payment = _flow_evidence(dataset, PAYMENT_FLOW)
    capture_summary = dataset.get("capture_summary", {})
    inventory = dataset.get("gopay_inventory", {})
    missing = {
        "registration": [s for s in registration if not s["capture_backed"] and not s["code_backed"]],
        "payment": [s for s in payment if not s["capture_backed"] and not s["code_backed"]],
    }
    return {
        "version": PROFILE_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "offline_complete_protocol_profile",
        "sources": dataset.get("sources", {}),
        "summary": {
            "capture_total_items": capture_summary.get("total_items", 0),
            "capture_total_endpoints": capture_summary.get("total_endpoints", 0),
            "code_endpoint_inventory": len(inventory.get("code_endpoint_inventory", [])),
            "capture_categories": inventory.get("capture_category_counts", {}),
        },
        "references": _reference_summary(dataset),
        "flows": {
            "registration": registration,
            "payment": payment,
        },
        "missing": missing,
    }


def write_protocol_profile(
    profile: dict[str, Any],
    json_path: str | Path,
    markdown_path: str | Path | None = None,
) -> None:
    Path(json_path).expanduser().write_text(
        json.dumps(profile, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if markdown_path:
        Path(markdown_path).expanduser().write_text(profile_markdown(profile), encoding="utf-8")


def profile_markdown(profile: dict[str, Any]) -> str:
    lines = [
        "# GoPay Protocol vNext",
        "",
        f"- Version: `{profile.get('version', '')}`",
        f"- Generated at: `{profile.get('generated_at', '')}`",
        f"- Mode: `{profile.get('mode', '')}`",
        "",
        "## Sources",
        "",
        f"- Capture: `{profile.get('sources', {}).get('capture_xml', '')}`",
        f"- Current: `{profile.get('sources', {}).get('current_root', '')}`",
    ]
    for root in profile.get("sources", {}).get("reference_roots", []):
        lines.append(f"- Reference: `{root}`")

    summary = profile.get("summary", {})
    lines.extend([
        "",
        "## Summary",
        "",
        f"- Capture items: {summary.get('capture_total_items', 0)}",
        f"- Capture endpoints: {summary.get('capture_total_endpoints', 0)}",
        f"- Code endpoint inventory: {summary.get('code_endpoint_inventory', 0)}",
        "",
        "## References",
        "",
    ])
    for ref in profile.get("references", []):
        lines.append(
            f"- `{ref['root']}`: files={ref['files_scanned']}, "
            f"endpoints={ref['endpoint_keys']}, paths={ref['paths']}, "
            f"capture_path_matches={ref['capture_path_matches']}"
        )

    for flow_name in ("registration", "payment"):
        lines.extend(["", f"## {flow_name.title()} Flow", ""])
        for step in profile.get("flows", {}).get(flow_name, []):
            capture = "capture" if step["capture_backed"] else "no-capture"
            code = "code" if step["code_backed"] else "no-code"
            lines.append(f"- `{step['id']}` `{step['method']} {step['path']}` [{capture}, {code}]")

    lines.extend(["", "## Missing", ""])
    for flow_name, steps in profile.get("missing", {}).items():
        if not steps:
            lines.append(f"- `{flow_name}`: none")
        else:
            for step in steps:
                lines.append(f"- `{flow_name}` missing `{step['method']} {step['path']}`")

    return "\n".join(lines) + "\n"
