"""
Hero-SMS API helpers for GoPay protocol flows.

Extracted from test_full_e2e.py — pure utility functions, no flow logic.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time

import tls_client

log = logging.getLogger(__name__)

HEROSMS_API = "https://hero-sms.com"
SMSBOWER_API = "https://smsbower.page"
HEROSMS_SERVICE = os.environ.get("OPAI_HEROSMS_SERVICE", "ni")
HEROSMS_COUNTRY = os.environ.get("OPAI_HEROSMS_COUNTRY", "6")
SMS_TIMEOUT = 120


def sms_provider_base(provider: str = "") -> str:
    p = (provider or "herosms").strip().lower()
    if p in ("smsbower", "bower", "sms-bower"):
        return SMSBOWER_API
    return HEROSMS_API


def sms_api(
    api_key: str,
    action: str,
    params: dict | None = None,
    retries: int = 3,
    provider: str = "",
) -> str:
    p = {"api_key": api_key, "action": action}
    if params:
        p.update(params)
    for i in range(1, retries + 1):
        try:
            s = tls_client.Session(client_identifier="chrome_120")
            r = s.get(f"{sms_provider_base(provider)}/stubs/handler_api.php", params=p, timeout_seconds=30)
            return r.text.strip()
        except Exception as e:
            log.debug("sms_api attempt %d: %s", i, e)
            if i < retries:
                time.sleep(3)
    raise RuntimeError(f"sms_api {action} failed after {retries} retries")


def sms_get_prices(api_key: str, service: str = "", country: str = "", provider: str = "") -> str:
    action = "getPricesV3" if (provider or "").strip().lower() in ("smsbower", "bower", "sms-bower") else "getPrices"
    return sms_api(api_key, action, {
        "service": service or HEROSMS_SERVICE,
        "country": country or HEROSMS_COUNTRY,
    }, provider=provider)


def sms_get_prices_parsed(api_key: str, service: str = "", country: str = "", provider: str = "") -> list[dict]:
    raw = sms_get_prices(api_key, service, country, provider=provider)
    operators: list[dict] = []
    try:
        data = json.loads(raw) if raw.strip().startswith("{") else {}
    except Exception:
        log.debug("getPrices not JSON: %s", raw[:200])
        data = {}
    svc = service or HEROSMS_SERVICE
    cty = country or HEROSMS_COUNTRY
    country_data = data.get(cty, {})
    service_data = country_data.get(svc, {}) if isinstance(country_data, dict) else {}
    if isinstance(service_data, dict):
        for op_code, op_info in service_data.items():
            try:
                op_code_int = int(op_code)
            except (ValueError, TypeError):
                if op_code in ("cost", "count", "physicalCount"):
                    continue
                op_code_int = -1
            if op_code_int < 0:
                continue
            cost = float(op_info.get("cost") or op_info.get("price") or 999)
            count = int(op_info.get("count") or op_info.get("quantity") or 0)
            operators.append({
                "operator": str(op_info.get("provider_id") or op_code),
                "cost": cost,
                "count": count,
            })
    if not operators:
        aggregated_cost = 0.0
        if isinstance(service_data, dict):
            aggregated_cost = float(service_data.get("cost") or 0)
        raw_total = sms_api(api_key, "getNumbersStatus", {"country": cty}, provider=provider)
        log.info("getNumbersStatus raw: %s", raw_total[:500])
        try:
            status_data = json.loads(raw_total) if raw_total.strip().startswith("{") else {}
        except Exception:
            status_data = {}
        svc_status = status_data.get(svc, {})
        if isinstance(svc_status, dict):
            for op_code, op_count in svc_status.items():
                try:
                    op_count_int = int(op_count)
                except (ValueError, TypeError):
                    continue
                if op_count_int > 0:
                    operators.append({
                        "operator": op_code,
                        "cost": aggregated_cost,
                        "count": op_count_int,
                    })
    operators.sort(key=lambda x: x["cost"])
    log.info("getPrices parsed: %d operators, cheapest=$%.4f", len(operators), operators[0]["cost"] if operators else -1)
    return operators


def sms_get_number_with_operator(
    api_key: str, service: str = "", country: str = "", operator: str = "", provider: str = ""
) -> tuple[str | None, str | None]:
    params: dict[str, str] = {
        "service": service or HEROSMS_SERVICE,
        "country": country or HEROSMS_COUNTRY,
    }
    if operator:
        if (provider or "").strip().lower() in ("smsbower", "bower", "sms-bower"):
            params["providerIds"] = operator
        else:
            params["operator"] = operator
    resp = sms_api(api_key, "getNumber", params, provider=provider)
    log.info("getNumber(operator=%s): %s", operator or "default", resp)
    if resp.startswith("ACCESS_NUMBER:"):
        parts = resp.split(":")
        return f"+{parts[2]}", parts[1]
    if resp.startswith("ACCESS_") or ":" in resp:
        parts = resp.split(":")
        if len(parts) >= 3:
            return f"+{parts[2]}", parts[1]
    log.warning("getNumber failed (operator=%s): %s", operator or "default", resp)
    return None, None


def sms_get_number_tiered(
    api_key: str,
    service: str = "",
    country: str = "",
    provider: str = "",
    max_retries_per_tier: int = 3,
) -> tuple[str | None, str | None, int]:
    operators = sms_get_prices_parsed(api_key, service, country, provider=provider)
    sms_service = service or HEROSMS_SERVICE
    sms_country = country or HEROSMS_COUNTRY
    tried_tiers = 0
    if not operators:
        phone, aid = sms_get_number_with_operator(api_key, sms_service, sms_country, provider=provider)
        return phone, aid, 0
    for idx, op in enumerate(operators):
        if op["count"] <= 0:
            continue
        tried_tiers = idx + 1
        for attempt in range(1, max_retries_per_tier + 1):
            phone, aid = sms_get_number_with_operator(api_key, sms_service, sms_country, op["operator"], provider=provider)
            if phone:
                log.info("tiered rental success: tier=%d operator=%s cost=%.4f phone=%s", idx + 1, op["operator"], op["cost"], phone)
                return phone, aid, idx + 1
            if attempt < max_retries_per_tier:
                time.sleep(2)
    phone, aid = sms_get_number_with_operator(api_key, sms_service, sms_country, provider=provider)
    return phone, aid, tried_tiers


def sms_get_number(api_key: str, service: str = "", country: str = "", provider: str = "") -> tuple[str | None, str | None]:
    resp = sms_api(api_key, "getNumber", {
        "service": service or HEROSMS_SERVICE,
        "country": country or HEROSMS_COUNTRY,
    }, provider=provider)
    log.info("getNumber: %s", resp)
    if resp.startswith("ACCESS_NUMBER:"):
        parts = resp.split(":")
        return f"+{parts[2]}", parts[1]
    log.warning("getNumber failed: %s", resp)
    return None, None


def sms_wait_code(api_key: str, aid: str, timeout: int = SMS_TIMEOUT, provider: str = "") -> str | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = sms_api(api_key, "getStatus", {"id": aid}, provider=provider)
        except Exception:
            time.sleep(5)
            continue
        if resp.startswith("STATUS_OK:"):
            code = resp.split(":", 1)[1]
            m = re.search(r"\b(\d{4,6})\b", code)
            return m.group(1) if m else code
        if resp == "STATUS_CANCEL":
            log.warning("SMS activation cancelled")
            return None
        time.sleep(5)
    return None


def sms_request_another(api_key: str, aid: str, provider: str = "") -> bool:
    try:
        resp = sms_api(api_key, "setStatus", {"id": aid, "status": "3"}, provider=provider)
        log.info("sms_request_another: %s", resp)
        return "ACCESS_RETRY_GET" in resp
    except Exception:
        return False


def sms_cancel(api_key: str, aid: str, provider: str = "") -> None:
    try:
        sms_api(api_key, "setStatus", {"id": aid, "status": "8"}, provider=provider)
    except Exception:
        pass


def sms_done(api_key: str, aid: str, provider: str = "") -> None:
    try:
        sms_api(api_key, "setStatus", {"id": aid, "status": "6"}, provider=provider)
    except Exception:
        pass


# ========== API Error Helpers ==========

def is_waf_block(result: dict) -> bool:
    body = result.get("body", {})
    if isinstance(body, dict) and "raw" in body:
        return "WAF Block Page" in body["raw"]
    return False


def is_rate_limited(result: dict) -> bool:
    errors = result.get("body", {}).get("errors", [])
    if errors:
        code = errors[0].get("code", "")
        return "ratelimit" in code.lower() or "rate_limit" in code.lower()
    return result.get("status") == 429


def get_error_code(result: dict) -> str:
    errors = result.get("body", {}).get("errors", [])
    return errors[0].get("code", "") if errors else ""


def api_call_with_retry(fn, *args, max_retries: int = 2, **kwargs) -> dict:
    """Retry API call on WAF block or transient errors."""
    result = {}
    for attempt in range(max_retries + 1):
        result = fn(*args, **kwargs)
        if result["status"] in (200, 201, 204):
            return result
        if is_waf_block(result):
            if attempt < max_retries:
                wait = 5 * (attempt + 1)
                log.warning("WAF blocked, retrying in %ds... (%d/%d)", wait, attempt + 1, max_retries)
                time.sleep(wait)
                continue
        if is_rate_limited(result):
            if attempt < max_retries:
                wait = 30 * (attempt + 1)
                log.warning("Rate limited, retrying in %ds...", wait)
                time.sleep(wait)
                continue
        return result
    return result
