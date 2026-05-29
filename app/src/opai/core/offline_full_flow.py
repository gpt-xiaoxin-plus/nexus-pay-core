"""Offline full-flow runner backed by the protocol capture dataset.

The runner is deliberately network-free: it validates that a bundled capture
dataset contains the protocol shapes needed for each phase, then simulates a
complete registration -> OTP -> balance -> payment workflow. This gives a
repeatable end-to-end test harness without touching real accounts, SMS, PINs,
or payment rails.
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any


FLOW_STEPS = [
    {
        "id": "login_probe",
        "label": "Login/registration probe",
        "required_paths": ["/goto-auth/login/methods"],
    },
    {
        "id": "signup_otp_methods",
        "label": "Signup OTP methods",
        "required_paths": ["/cvs/v1/methods"],
    },
    {
        "id": "signup_otp_initiate",
        "label": "Signup OTP initiate",
        "required_paths": ["/cvs/v1/initiate"],
    },
    {
        "id": "signup_otp_verify",
        "label": "Signup OTP verify",
        "required_paths": ["/cvs/v1/verify"],
    },
    {
        "id": "account_create",
        "label": "Account create",
        "required_paths": ["/v7/customers/signup"],
    },
    {
        "id": "token_exchange",
        "label": "Token exchange",
        "required_paths": ["/goto-auth/token"],
    },
    {
        "id": "pin_setup",
        "label": "PIN setup",
        "required_paths": ["/api/v2/users/pins/setup/tokens"],
    },
    {
        "id": "profile_check",
        "label": "Profile check",
        "required_paths": ["/v1/users/profile"],
    },
    {
        "id": "balance_poll",
        "label": "Balance poll",
        "required_paths": [
            "/v1/payment-options/balances",
            "/v1/user/wallet-card/balance",
        ],
        "match_any": True,
    },
]


def load_dataset(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


def capture_paths(dataset: dict[str, Any]) -> set[str]:
    return {
        endpoint.get("path", "")
        for endpoint in dataset.get("capture_summary", {}).get("endpoints", [])
        if endpoint.get("path")
    }


def validate_flow_dataset(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate whether required offline protocol shapes are present."""
    paths = capture_paths(dataset)
    validations = []
    for step in FLOW_STEPS:
        required = step["required_paths"]
        if step.get("match_any"):
            present = [p for p in required if p in paths]
            ok = bool(present)
            missing = [] if ok else required
        else:
            present = [p for p in required if p in paths]
            missing = [p for p in required if p not in paths]
            ok = not missing
        validations.append({
            "id": step["id"],
            "label": step["label"],
            "ok": ok,
            "present_paths": present,
            "missing_paths": missing,
        })
    return validations


def run_offline_full_flow(dataset_path: str | Path) -> dict[str, Any]:
    """Run a deterministic offline simulation of the full GoPay workflow."""
    dataset = load_dataset(dataset_path)
    validations = validate_flow_dataset(dataset)
    missing = [v for v in validations if not v["ok"]]
    run_id = uuid.uuid4().hex[:12]
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    result: dict[str, Any] = {
        "run_id": run_id,
        "mode": "offline_mock",
        "dataset": str(Path(dataset_path).expanduser()),
        "started_at": now,
        "validations": validations,
        "success": not missing,
        "phases": [],
    }

    if missing:
        result["error"] = "dataset_missing_required_protocol_shapes"
        result["missing_steps"] = missing
        return result

    account_id = f"offline-account-{run_id}"
    phone = "+620000000000"
    job_id = f"offline-job-{run_id}"
    snap_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"offline-midtrans-{run_id}"))

    result["phases"] = [
        {
            "phase": "register",
            "status": "ok",
            "account_id": account_id,
            "phone": phone,
            "otp": "<mocked>",
            "pin": "<mocked>",
        },
        {
            "phase": "balance_poll",
            "status": "ok",
            "balance_rp": 10000,
            "source": "offline_capture_shape",
        },
        {
            "phase": "job_claim",
            "status": "ok",
            "job_id": job_id,
            "provider": "gopay",
            "midtrans_url": f"https://app.midtrans.com/snap/v4/redirection/{snap_id}",
        },
        {
            "phase": "payment",
            "status": "ok",
            "transaction_status": "settlement",
            "detail": "offline simulated payment completed",
        },
    ]
    result["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return result


def write_offline_flow_result(result: dict[str, Any], out_path: str | Path | None = None) -> str:
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if out_path:
        Path(out_path).expanduser().write_text(text + "\n", encoding="utf-8")
    return text
