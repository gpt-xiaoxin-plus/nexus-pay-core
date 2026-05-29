from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opai", description="GoPay protocol automation (no browser)")
    parser.add_argument("--debug", action="store_true", help="enable debug logging")
    sub = parser.add_subparsers(dest="command")

    # === worker (protocol-based, no browser) ===
    p_worker = sub.add_parser("worker", help="GoPay protocol worker (register + pay)")
    worker_sub = p_worker.add_subparsers(dest="worker_command")

    p_w_run = worker_sub.add_parser("run", help="Start parallel register+pay worker threads")
    p_w_run.add_argument("--workers", type=int, default=3, help="Number of parallel workers")
    p_w_run.add_argument("--pin", default="147258", help="GoPay PIN to set")
    p_w_run.add_argument("--poll", type=float, default=10, help="Inbox poll interval (seconds)")
    p_w_run.add_argument("--api-key", default="", help="Hero-SMS API key")
    p_w_run.add_argument("--resume", nargs="+", metavar="PHONE", help="Resume from existing accounts")

    p_w_dry = worker_sub.add_parser("dry-run", help="Register one account only (no payment)")
    p_w_dry.add_argument("--pin", default="147258", help="GoPay PIN to set")
    p_w_dry.add_argument("--api-key", default="", help="Hero-SMS API key")

    p_w_register = worker_sub.add_parser("register", help="Register a single GoPay account")
    p_w_register.add_argument("--pin", default="147258", help="GoPay PIN to set")
    p_w_register.add_argument("--api-key", default="", help="Hero-SMS API key")
    p_w_register.add_argument("--proxy", default="", help="Proxy URL")

    p_w_manual = worker_sub.add_parser("manual-register", help="Register a single GoPay account with manual phone/OTP input")
    p_w_manual.add_argument("--phone", default="", help="Phone number, e.g. 0851..., 851..., +62851...")
    p_w_manual.add_argument("--pin", default="147258", help="GoPay PIN to set")
    p_w_manual.add_argument("--proxy", default="", help="Proxy URL")
    p_w_manual.add_argument("--mock", action="store_true", help="Local test mode: accept any phone and do not call live GoPay APIs")
    p_w_manual.add_argument("--country-code", default="62", help="Country code for live manual mode, default 62")
    p_w_manual.add_argument("--signed-up-country", default="ID", help="signed_up_country value for account create, default ID")
    p_w_manual.add_argument("--force-live", action="store_true", help="Really call live GoPay APIs even when country-code is not 62")
    p_w_manual.add_argument("--relogin-after-register", action="store_true", help="Logout after registration, then login again to save fresh tokens")

    p_w_balance = worker_sub.add_parser("balance", help="Check balance of a saved account")
    p_w_balance.add_argument("phone", help="Phone number")
    p_w_balance.add_argument("--proxy", default="", help="Proxy URL")

    worker_sub.add_parser("fingerprints", help="Ensure saved accounts have stable payment fingerprints")

    # === pay (protocol-based single payment test) ===
    p_pay = sub.add_parser("pay", help="Run a single protocol payment against Midtrans URL")
    p_pay.add_argument("midtrans_url", help="Midtrans snap redirect URL")
    p_pay.add_argument("--phone", required=True, help="GoPay local phone (no +62)")
    p_pay.add_argument("--pin", required=True, help="6-digit PIN")
    p_pay.add_argument("--proxy", default="", help="Proxy URL")
    p_pay.add_argument("--otp", default="", help="Optional one-time GoPay linking OTP; otherwise prompt in terminal")

    # === capture (offline Burp XML protocol import) ===
    p_capture = sub.add_parser("capture", help="Offline Burp XML protocol capture tools")
    capture_sub = p_capture.add_subparsers(dest="capture_command")

    p_c_import = capture_sub.add_parser("import", help="Decode, redact, and summarize a Burp XML export")
    p_c_import.add_argument("xml_path", help="Path to Burp XML export")
    p_c_import.add_argument("--out", default="", help="Optional JSON report output path")
    p_c_import.add_argument(
        "--summary-only",
        action="store_true",
        help="Print/write only endpoint summary, not per-request records",
    )

    p_c_bundle = capture_sub.add_parser("bundle", help="Build one offline dataset from capture + code repos")
    p_c_bundle.add_argument("xml_path", help="Path to Burp XML export")
    p_c_bundle.add_argument(
        "--current-root",
        default=".",
        help="Current project root to scan for protocol literals",
    )
    p_c_bundle.add_argument(
        "--reference-root",
        action="append",
        default=[],
        help="Optional reference repo root to scan for protocol literals; repeat for multiple repos",
    )
    p_c_bundle.add_argument(
        "--out-json",
        default="config/protocol_offline_dataset.json",
        help="Combined JSON dataset output path",
    )
    p_c_bundle.add_argument(
        "--out-md",
        default="config/protocol_offline_report.md",
        help="Markdown digest output path",
    )
    p_c_bundle.add_argument(
        "--out-inventory-json",
        default="config/gopay_protocol_inventory.json",
        help="Redacted GoPay protocol inventory JSON output path",
    )
    p_c_bundle.add_argument(
        "--out-inventory-md",
        default="config/gopay_protocol_inventory.md",
        help="Redacted GoPay protocol inventory Markdown output path",
    )

    # === flow (offline full-flow test harness) ===
    p_flow = sub.add_parser("flow", help="Offline full-flow protocol runner")
    flow_sub = p_flow.add_subparsers(dest="flow_command")

    p_f_offline = flow_sub.add_parser("offline", help="Run register->OTP->balance->payment offline")
    p_f_offline.add_argument(
        "--dataset",
        default="config/protocol_offline_dataset.json",
        help="Combined protocol dataset JSON from `opai capture bundle`",
    )
    p_f_offline.add_argument(
        "--out",
        default="config/offline_full_flow_result.json",
        help="Offline flow result JSON output path",
    )

    # === protocol (versioned offline profile) ===
    p_protocol = sub.add_parser("protocol", help="Build and inspect versioned protocol profiles")
    protocol_sub = p_protocol.add_subparsers(dest="protocol_command")

    p_p_build = protocol_sub.add_parser("build", help="Build protocol vNext profile from dataset")
    p_p_build.add_argument(
        "--dataset",
        default="config/protocol_offline_dataset.json",
        help="Combined protocol dataset JSON",
    )
    p_p_build.add_argument(
        "--out-json",
        default="config/protocol_vnext.json",
        help="Protocol vNext JSON output path",
    )
    p_p_build.add_argument(
        "--out-md",
        default="config/protocol_vnext.md",
        help="Protocol vNext Markdown output path",
    )

    p_p_status = protocol_sub.add_parser("status", help="Print protocol vNext status")
    p_p_status.add_argument(
        "--profile",
        default="config/protocol_vnext.json",
        help="Protocol vNext JSON profile path",
    )

    return parser


def cmd_worker_run(args: argparse.Namespace) -> None:
    from opai.core.gopay_protocol_worker import run_worker
    run_worker(
        max_workers=args.workers,
        pin=args.pin,
        poll_interval=args.poll,
        resume_phones=args.resume,
        api_key=args.api_key,
    )


def cmd_worker_dry_run(args: argparse.Namespace) -> None:
    from opai.core.gopay_protocol_worker import _register_one, _make_proxy, _get_envelope_did
    from opai.core.sms_helpers import sms_done

    api_key = args.api_key or os.environ.get("OPAI_HEROSMS_API_KEY", "")
    if not api_key:
        raise SystemExit("No API key. Set --api-key or OPAI_HEROSMS_API_KEY")
    proxy = _make_proxy()
    envelope_did = _get_envelope_did()
    result = _register_one(api_key, args.pin, proxy, envelope_did)
    if result:
        print(f"SUCCESS: {result['phone']} pin={args.pin}")
        sms_done(api_key, result["aid"])
    else:
        raise SystemExit("FAILED")


def cmd_worker_register(args: argparse.Namespace) -> None:
    from opai.core.gopay_protocol_worker import _register_one, _make_proxy, _get_envelope_did
    from opai.core.sms_helpers import sms_done

    api_key = args.api_key or os.environ.get("OPAI_HEROSMS_API_KEY", "")
    if not api_key:
        raise SystemExit("No API key. Set --api-key or OPAI_HEROSMS_API_KEY")
    proxy = args.proxy or _make_proxy()
    envelope_did = _get_envelope_did()
    result = _register_one(api_key, args.pin, proxy, envelope_did)
    if result:
        print(json.dumps({
            "phone": result["phone"],
            "pin": args.pin,
            "local": result["local"],
        }, indent=2))
        sms_done(api_key, result["aid"])
    else:
        raise SystemExit("FAILED")


def cmd_worker_manual_register(args: argparse.Namespace) -> None:
    from opai.core.gopay_protocol_worker import (
        _normalize_phone,
        _normalize_phone_for_country,
        _register_one_manual,
        _register_one_manual_live_country,
        _make_proxy,
        _get_envelope_did,
    )

    phone = args.phone.strip()
    if not phone:
        phone = input("请输入接收 GoPay OTP 的手机号（例如 0851... / 851... / +62851...）: ").strip()

    if args.mock:
        signup_otp = input(f"[mock] 注册 OTP 已发送到 {phone}，请输入任意验证码: ").strip()
        pin_otp = input(f"[mock] PIN OTP 已发送到 {phone}，请输入任意验证码: ").strip()
        result = {
            "mode": "manual-mock",
            "phone": phone,
            "pin": args.pin,
            "signup_otp_entered": bool(signup_otp),
            "pin_otp_entered": bool(pin_otp),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        out = Path("config/manual_register_mock_result.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({**result, "out": str(out)}, ensure_ascii=False, indent=2))
        return

    country_code = args.country_code.strip().lstrip("+") or "62"
    if country_code != "62":
        if not args.force_live:
            raise SystemExit("非 +62 号码要真实请求 GoPay，请加 --force-live，例如 --country-code 86 --force-live。")
        normalized = _normalize_phone_for_country(phone, country_code)
        if not normalized:
            raise SystemExit("手机号格式不对，无法按指定 country-code 规范化。")
        proxy = args.proxy or _make_proxy()
        envelope_did = _get_envelope_did()
        print(f"[live] 将真实请求 GoPay 接口: phone={normalized}, country_code=+{country_code}")
        result = _register_one_manual_live_country(
            normalized,
            args.pin,
            proxy,
            envelope_did,
            country_code=f"+{country_code}",
            signed_up_country=args.signed_up_country,
            relogin_after_register=args.relogin_after_register,
        )
        if result:
            print(json.dumps({
                "phone": result["phone"],
                "pin": args.pin,
                "local": result["local"],
                "mode": "manual-live-country",
                "country_code": f"+{country_code}",
            }, ensure_ascii=False, indent=2))
        else:
            raise SystemExit("FAILED")
        return

    normalized = _normalize_phone(phone)
    if not normalized:
        raise SystemExit("手机号格式不对：GoPay 印尼号码请填 08...、8...、62... 或 +62...，不要填 86 开头的中国号码。")
    proxy = args.proxy or _make_proxy()
    envelope_did = _get_envelope_did()
    result = _register_one_manual(
        normalized,
        args.pin,
        proxy,
        envelope_did,
        relogin_after_register=args.relogin_after_register,
    )
    if result:
        print(json.dumps({
            "phone": result["phone"],
            "pin": args.pin,
            "local": result["local"],
            "mode": "manual",
        }, ensure_ascii=False, indent=2))
    else:
        raise SystemExit("FAILED")


def cmd_worker_balance(args: argparse.Namespace) -> None:
    from opai.core.gopay_protocol_worker import _resume_account, _check_balance

    account = _resume_account(args.phone, proxy=args.proxy)
    if not account:
        raise SystemExit(f"Account {args.phone} not found")
    bal = _check_balance(account["client"])
    print(json.dumps({"phone": account["phone"], "balance_rp": bal}, indent=2))


def cmd_worker_fingerprints(args: argparse.Namespace) -> None:
    from opai.core.gopay_protocol_worker import migrate_account_payment_fingerprints

    print(json.dumps(migrate_account_payment_fingerprints(), ensure_ascii=False, indent=2))


def cmd_pay(args: argparse.Namespace) -> None:
    from opai.core.gopay_payment_protocol import GoPayPayment
    from opai.core.gopay_protocol_worker import _load_account_payment_fingerprint
    from opai.core.payment_fingerprint import build_payment_fingerprint

    otp_once = {"value": args.otp.strip()}

    def wait_otp(phone: str, timeout: int):
        if otp_once["value"]:
            code = otp_once["value"]
            otp_once["value"] = ""
            return code
        try:
            return input(f"[manual] GoPay linking OTP 已发送到 {phone}，请输入验证码（建议 {timeout}s 内输入）: ").strip() or None
        except EOFError:
            return None

    payment_profile = _load_account_payment_fingerprint(args.phone) or build_payment_fingerprint(
        phone=args.phone,
        local=args.phone,
    )
    payment = GoPayPayment(proxy=args.proxy, payment_fingerprint=payment_profile)
    result = payment.pay(
        midtrans_url=args.midtrans_url,
        phone=args.phone,
        country_code="62",
        pin=args.pin,
        wait_otp=wait_otp,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_capture_import(args: argparse.Namespace) -> None:
    from opai.core.burp_capture import import_capture, write_report

    report = import_capture(args.xml_path)
    output = report["summary"] if args.summary_only else report
    if args.out:
        write_report(output, args.out)
        summary = report["summary"]
        print(json.dumps({
            "ok": True,
            "out": args.out,
            "total_items": summary["total_items"],
            "total_endpoints": summary["total_endpoints"],
            "hosts": summary["hosts"],
        }, ensure_ascii=False, indent=2))
    else:
        print(write_report(output))


def cmd_capture_bundle(args: argparse.Namespace) -> None:
    from opai.core.burp_capture import build_combined_dataset, write_combined_dataset

    dataset = build_combined_dataset(
        capture_xml=args.xml_path,
        current_root=args.current_root,
        reference_root=args.reference_root or None,
    )
    write_combined_dataset(
        dataset,
        args.out_json,
        args.out_md or None,
        args.out_inventory_json or None,
        args.out_inventory_md or None,
    )
    comparison = dataset["comparison"]
    print(json.dumps({
        "ok": True,
        "out_json": args.out_json,
        "out_md": args.out_md,
        "out_inventory_json": args.out_inventory_json,
        "out_inventory_md": args.out_inventory_md,
        "capture_total_items": dataset["capture_summary"]["total_items"],
        "capture_total_endpoints": dataset["capture_summary"]["total_endpoints"],
        "capture_matched_current": len(comparison["capture_matched_current"]),
        "capture_matched_reference": len(comparison["capture_matched_reference"]),
        "capture_paths_matched_current": len(comparison["capture_paths_matched_current"]),
        "capture_paths_matched_reference": len(comparison["capture_paths_matched_reference"]),
        "capture_only": len(comparison["capture_only"]),
        "capture_paths_only": len(comparison["capture_paths_only"]),
    }, ensure_ascii=False, indent=2))


def cmd_flow_offline(args: argparse.Namespace) -> None:
    from opai.core.offline_full_flow import run_offline_full_flow, write_offline_flow_result

    result = run_offline_full_flow(args.dataset)
    write_offline_flow_result(result, args.out)
    print(json.dumps({
        "ok": result["success"],
        "mode": result["mode"],
        "out": args.out,
        "run_id": result["run_id"],
        "phases": [p["phase"] for p in result.get("phases", [])],
        "error": result.get("error", ""),
    }, ensure_ascii=False, indent=2))


def cmd_protocol_build(args: argparse.Namespace) -> None:
    from opai.core.gopay_protocol_profile import (
        build_protocol_profile,
        load_json,
        write_protocol_profile,
    )

    dataset = load_json(args.dataset)
    profile = build_protocol_profile(dataset)
    write_protocol_profile(profile, args.out_json, args.out_md or None)
    missing = profile.get("missing", {})
    print(json.dumps({
        "ok": True,
        "version": profile["version"],
        "out_json": args.out_json,
        "out_md": args.out_md,
        "capture_total_items": profile["summary"]["capture_total_items"],
        "capture_total_endpoints": profile["summary"]["capture_total_endpoints"],
        "code_endpoint_inventory": profile["summary"]["code_endpoint_inventory"],
        "registration_missing": len(missing.get("registration", [])),
        "payment_missing": len(missing.get("payment", [])),
    }, ensure_ascii=False, indent=2))


def cmd_protocol_status(args: argparse.Namespace) -> None:
    from opai.core.gopay_protocol_profile import load_json

    profile = load_json(args.profile)
    missing = profile.get("missing", {})
    print(json.dumps({
        "version": profile.get("version", ""),
        "generated_at": profile.get("generated_at", ""),
        "sources": profile.get("sources", {}),
        "summary": profile.get("summary", {}),
        "registration_missing": [
            f"{s['method']} {s['path']}" for s in missing.get("registration", [])
        ],
        "payment_missing": [
            f"{s['method']} {s['path']}" for s in missing.get("payment", [])
        ],
    }, ensure_ascii=False, indent=2))


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    if args.command == "worker":
        if args.worker_command == "run":
            cmd_worker_run(args)
        elif args.worker_command == "dry-run":
            cmd_worker_dry_run(args)
        elif args.worker_command == "register":
            cmd_worker_register(args)
        elif args.worker_command == "manual-register":
            cmd_worker_manual_register(args)
        elif args.worker_command == "balance":
            cmd_worker_balance(args)
        elif args.worker_command == "fingerprints":
            cmd_worker_fingerprints(args)
        else:
            parser.parse_args(["worker", "--help"])
    elif args.command == "pay":
        cmd_pay(args)
    elif args.command == "capture":
        if args.capture_command == "import":
            cmd_capture_import(args)
        elif args.capture_command == "bundle":
            cmd_capture_bundle(args)
        else:
            parser.parse_args(["capture", "--help"])
    elif args.command == "flow":
        if args.flow_command == "offline":
            cmd_flow_offline(args)
        else:
            parser.parse_args(["flow", "--help"])
    elif args.command == "protocol":
        if args.protocol_command == "build":
            cmd_protocol_build(args)
        elif args.protocol_command == "status":
            cmd_protocol_status(args)
        else:
            parser.parse_args(["protocol", "--help"])
    else:
        parser.print_help()
