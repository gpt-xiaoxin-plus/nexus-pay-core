"""OpenAI Plus checkout → Midtrans URL generator.

This module stops at the Midtrans Snap redirection URL. It does not submit the
GoPay payment; the existing GoPay payment worker consumes the returned URL.
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import uuid
from typing import Any

import tls_client


DEFAULT_STRIPE_PK = (
    "pk_live_51HOrSwC6h1nxGoI3lTAgRjYVrz4dU3fVOabyCcKR3pbEJguCVAlqCxdxCUvoRh1XWwRac"
    "ViovU3kLKvpkjh7IqkW00iXQsjo3n"
)

DEFAULT_TIMEOUT = 30


class OpenAICheckoutError(RuntimeError):
    pass


def _looks_like_html(value: str) -> bool:
    sample = value.lstrip()[:80].lower()
    return sample.startswith("<html") or sample.startswith("<!doctype html")


class OpenAICheckout:
    def __init__(
        self,
        *,
        access_token: str,
        cookie_header: str = "",
        session_token: str = "",
        device_id: str = "",
        user_agent: str = "",
        proxy: str = "",
    ) -> None:
        token = (access_token or "").strip()
        if token.startswith("Bearer "):
            token = token[7:].strip()
        if not token:
            raise OpenAICheckoutError("AT/access token 不能为空")

        self.access_token = token
        self.device_id = (device_id or "").strip() or str(uuid.uuid4())
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
        )
        # Match the local checkout-link-extractor TLS path that has been working
        # on this machine: chrome130 + cookie jar + a chatgpt.com warmup request.
        self.cs = tls_client.Session(client_identifier="chrome130", random_tls_extension_order=True)
        self.ext = tls_client.Session(client_identifier="chrome130", random_tls_extension_order=True)
        self.cs.cookies_enabled = True
        self.ext.cookies_enabled = True
        if proxy:
            self.cs.proxies = {"http": proxy, "https": proxy}
            self.ext.proxies = {"http": proxy, "https": proxy}

        cookie_parts: list[str] = []
        seen: set[str] = set()
        for raw in (cookie_header or "").split(";"):
            part = raw.strip()
            if part and "=" in part:
                name = part.split("=", 1)[0].strip()
                if name and name not in seen:
                    seen.add(name)
                    cookie_parts.append(part)
        if session_token and "__Secure-next-auth.session-token" not in seen:
            cookie_parts.append(f"__Secure-next-auth.session-token={session_token.strip()}")
        if self.device_id and "oai-did" not in seen:
            cookie_parts.append(f"oai-did={self.device_id}")
        self.cookie_header = "; ".join(cookie_parts)

    def _chatgpt_headers(self, target_path: str = "") -> dict[str, str]:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Origin": "https://chatgpt.com",
            "Referer": "https://chatgpt.com/",
            "oai-device-id": self.device_id,
            "oai-language": "en-US",
            "sec-ch-ua": '"Google Chrome";v="147", "Not.A/Brand";v="8", "Chromium";v="147"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }
        if self.cookie_header:
            headers["Cookie"] = self.cookie_header
        if target_path:
            headers["x-openai-target-path"] = target_path
            headers["x-openai-target-route"] = target_path
        return headers

    def _json_body(self, resp) -> dict[str, Any]:
        try:
            return resp.json()
        except Exception:
            return {"raw": getattr(resp, "text", "")}

    def _chatgpt_error(self, resp, data: dict[str, Any], label: str = "OpenAI checkout") -> OpenAICheckoutError:
        raw = str(data.get("raw") or "")
        if resp.status_code == 403 and _looks_like_html(raw):
            return OpenAICheckoutError(
                f"{label} 失败: 403。chatgpt.com 返回了浏览器校验页面，不是 JSON API；"
                "AT 单独没有通过当前会话校验。请在本机网页补填同一浏览器的完整 chatgpt.com Cookie，"
                "必要时再填 oai-device-id，然后重试。"
            )
        return OpenAICheckoutError(f"{label} 失败: {resp.status_code} {str(data)[:500]}")

    def create_checkout(
        self,
        *,
        country: str = "ID",
        currency: str = "IDR",
        plan_name: str = "chatgptplusplan",
        promo_campaign_id: str = "plus-1-month-free",
        checkout_ui_mode: str = "hosted",
    ) -> dict[str, str]:
        body = {
            "entry_point": "all_plans_pricing_modal",
            "plan_name": plan_name,
            "billing_details": {"country": country.upper(), "currency": currency.upper()},
            "promo_campaign": {
                "promo_campaign_id": promo_campaign_id,
                "is_coupon_from_query_param": False,
            },
            "checkout_ui_mode": checkout_ui_mode,
            "cancel_url": "https://chatgpt.com/#pricing",
        }
        try:
            self.cs.get(
                "https://chatgpt.com",
                headers={"User-Agent": self.user_agent, "Accept": "*/*"},
                allow_redirects=True,
                timeout_seconds=DEFAULT_TIMEOUT,
            )
        except Exception:
            pass
        resp = self.cs.post(
            "https://chatgpt.com/backend-api/payments/checkout",
            headers={
                "authorization": f"Bearer {self.access_token}",
                "content-type": "application/json",
                "accept": "application/json",
            },
            json=body,
            allow_redirects=True,
            timeout_seconds=DEFAULT_TIMEOUT,
        )
        data = self._json_body(resp)
        if resp.status_code not in (200, 201):
            raise self._chatgpt_error(resp, data)
        cs_id = str(data.get("checkout_session_id") or data.get("session_id") or data.get("id") or "")
        checkout_url = str(data.get("url") or data.get("stripe_hosted_url") or data.get("checkout_url") or "")
        processor_entity = str(data.get("processor_entity") or "openai_llc")
        if not cs_id:
            m = re.search(r"(cs_(?:live|test)_[A-Za-z0-9_]+)", checkout_url)
            cs_id = m.group(1) if m else ""
        if not cs_id:
            raise OpenAICheckoutError(f"OpenAI checkout 响应没有 session id: {str(data)[:500]}")
        return {"checkout_session_id": cs_id, "checkout_url": checkout_url, "processor_entity": processor_entity}

    def _stripe_form_post(self, url: str, body: dict[str, str]) -> dict[str, Any]:
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://checkout.stripe.com",
            "Referer": "https://checkout.stripe.com/",
        }
        resp = self.ext.post(
            url,
            headers=headers,
            data=urllib.parse.urlencode(body),
            timeout_seconds=DEFAULT_TIMEOUT,
        )
        data = self._json_body(resp)
        if resp.status_code != 200:
            raise OpenAICheckoutError(f"Stripe 请求失败: {resp.status_code} {str(data)[:500]}")
        return data

    def _stripe_get(self, url: str, params: dict[str, str]) -> dict[str, Any]:
        qs = urllib.parse.urlencode(params)
        sep = "&" if "?" in url else "?"
        resp = self.ext.get(
            f"{url}{sep}{qs}",
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Referer": "https://checkout.stripe.com/",
            },
            timeout_seconds=DEFAULT_TIMEOUT,
        )
        data = self._json_body(resp)
        if resp.status_code != 200:
            raise OpenAICheckoutError(f"Stripe 查询失败: {resp.status_code} {str(data)[:500]}")
        return data

    def _stripe_create_pm(self, cs_id: str, stripe_pk: str, billing: dict[str, str]) -> str:
        data = self._stripe_form_post(
            "https://api.stripe.com/v1/payment_methods",
            {
                "billing_details[name]": billing.get("name") or "John Doe",
                "billing_details[email]": billing.get("email") or "buyer@example.com",
                "billing_details[address][country]": billing.get("country") or "US",
                "billing_details[address][line1]": billing.get("line1") or "3110 Sunset Boulevard",
                "billing_details[address][city]": billing.get("city") or "Los Angeles",
                "billing_details[address][postal_code]": billing.get("postal_code") or "90026",
                "billing_details[address][state]": billing.get("state") or "CA",
                "type": "gopay",
                "client_attribution_metadata[checkout_session_id]": cs_id,
                "key": stripe_pk,
            },
        )
        pm_id = str(data.get("id") or "")
        if not pm_id.startswith("pm_"):
            raise OpenAICheckoutError(f"Stripe 未返回 GoPay payment_method: {str(data)[:500]}")
        return pm_id

    def _stripe_init(self, cs_id: str, stripe_pk: str) -> dict[str, Any]:
        data = self._stripe_form_post(
            f"https://api.stripe.com/v1/payment_pages/{cs_id}/init",
            {
                "browser_locale": "en-US",
                "browser_timezone": "Asia/Shanghai",
                "elements_session_client[client_betas][0]": "custom_checkout_server_updates_1",
                "elements_session_client[client_betas][1]": "custom_checkout_manual_approval_1",
                "elements_session_client[elements_init_source]": "custom_checkout",
                "elements_session_client[referrer_host]": "chatgpt.com",
                "elements_session_client[stripe_js_id]": str(uuid.uuid4()),
                "elements_session_client[locale]": "en",
                "elements_session_client[is_aggregation_expected]": "false",
                "key": stripe_pk,
            },
        )
        pm_types = [x for x in data.get("payment_method_types", []) if isinstance(x, str)]
        if "gopay" not in pm_types:
            raise OpenAICheckoutError(f"这个 checkout 不支持 GoPay: payment_method_types={pm_types}")
        if not data.get("init_checksum"):
            raise OpenAICheckoutError("Stripe init 没有返回 init_checksum")
        return data

    @staticmethod
    def _extract_redirect_to_url(payload: dict[str, Any]) -> str:
        for key in ("next_action", "payment_intent", "setup_intent"):
            obj = payload.get(key)
            if not isinstance(obj, dict):
                continue
            action = obj if key == "next_action" else obj.get("next_action")
            if isinstance(action, dict) and action.get("type") == "redirect_to_url":
                return str(((action.get("redirect_to_url") or {}).get("url") or "")).strip()
        return ""

    @staticmethod
    def _amount_value(value: Any) -> str:
        if isinstance(value, bool):
            return ""
        if isinstance(value, int) and value >= 0:
            return str(value)
        if isinstance(value, float) and value >= 0 and value.is_integer():
            return str(int(value))
        if isinstance(value, str) and value.strip().isdigit():
            return value.strip()
        if isinstance(value, dict):
            for key in ("amount_due", "amount_total", "total", "amount", "value"):
                out = OpenAICheckout._amount_value(value.get(key))
                if out:
                    return out
        return ""

    @staticmethod
    def _stripe_expected_amount_candidates(init_data: dict[str, Any]) -> list[str]:
        candidates: list[str] = []

        def add(value: Any) -> None:
            amount = OpenAICheckout._amount_value(value)
            if amount and amount not in candidates:
                candidates.append(amount)

        direct_paths = (
            ("amount_due",),
            ("amount_total",),
            ("total",),
            ("invoice", "amount_due"),
            ("invoice", "amount_total"),
            ("invoice", "total"),
            ("latest_invoice", "amount_due"),
            ("latest_invoice", "amount_total"),
            ("latest_invoice", "total"),
            ("subscription", "latest_invoice", "amount_due"),
            ("subscription", "latest_invoice", "amount_total"),
            ("subscription", "latest_invoice", "total"),
            ("payment_intent", "amount"),
            ("payment_intent", "amount_received"),
            ("order", "amount_total"),
            ("order", "total"),
            ("line_items", "total"),
            ("line_item_group", "total"),
        )
        for path in direct_paths:
            cur: Any = init_data
            for key in path:
                if not isinstance(cur, dict):
                    cur = None
                    break
                cur = cur.get(key)
            add(cur)

        preferred_names = {"amount_due", "amount_total", "total", "total_amount"}

        def walk(obj: Any, key_name: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    key_l = str(key).lower()
                    if key_l in preferred_names:
                        add(value)
                    walk(value, key_l)
            elif isinstance(obj, list):
                for value in obj:
                    walk(value, key_name)

        walk(init_data)
        # Keep zero as last fallback for free trial sessions only.
        if "0" in candidates:
            candidates = [x for x in candidates if x != "0"] + ["0"]
        return candidates or ["0"]

    def _stripe_confirm(self, cs_id: str, pm_id: str, stripe_pk: str) -> dict[str, Any]:
        init_data = self._stripe_init(cs_id, stripe_pk)
        chatgpt_return = (
            f"https://chatgpt.com/checkout/verify?stripe_session_id={cs_id}"
            "&processor_entity=openai_llc&plan_type=plus"
        )
        return_url = (
            f"https://checkout.stripe.com/c/pay/{cs_id}"
            f"?returned_from_redirect=true&ui_mode=custom&return_url={urllib.parse.quote(chatgpt_return, safe='')}"
        )
        body = {
            "guid": uuid.uuid4().hex,
            "muid": uuid.uuid4().hex,
            "sid": uuid.uuid4().hex,
            "payment_method": pm_id,
            "init_checksum": str(init_data.get("init_checksum") or ""),
            "version": "fed52f3bc6",
            "expected_payment_method_type": "gopay",
            "return_url": return_url,
            "elements_session_client[session_id]": f"elements_session_{uuid.uuid4().hex[:11]}",
            "elements_session_client[locale]": "en",
            "elements_session_client[referrer_host]": "chatgpt.com",
            "elements_session_client[is_aggregation_expected]": "false",
            "client_attribution_metadata[client_session_id]": str(uuid.uuid4()),
            "client_attribution_metadata[merchant_integration_source]": "elements",
            "client_attribution_metadata[merchant_integration_subtype]": "payment-element",
            "client_attribution_metadata[payment_intent_creation_flow]": "deferred",
            "key": stripe_pk,
        }
        url = f"https://api.stripe.com/v1/payment_pages/{cs_id}/confirm"
        amounts = self._stripe_expected_amount_candidates(init_data)
        last_error: OpenAICheckoutError | None = None
        for amount in amounts:
            attempt = dict(body)
            attempt["expected_amount"] = amount
            try:
                return self._stripe_form_post(url, attempt)
            except OpenAICheckoutError as exc:
                msg = str(exc).lower()
                if "terms of service" in msg:
                    attempt["consent[terms_of_service]"] = "accepted"
                    try:
                        return self._stripe_form_post(url, attempt)
                    except OpenAICheckoutError as exc2:
                        msg = str(exc2).lower()
                        last_error = exc2
                else:
                    last_error = exc
                if "checkout_amount_mismatch" in msg or "expected_amount" in msg:
                    continue
                raise last_error
        if last_error:
            raise last_error
        raise OpenAICheckoutError("Stripe confirm failed before request")

    def _chatgpt_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        resp = self.cs.post(
            f"https://chatgpt.com{path}",
            headers=self._chatgpt_headers(path),
            data=json.dumps(body),
            timeout_seconds=DEFAULT_TIMEOUT,
        )
        data = self._json_body(resp)
        if resp.status_code not in (200, 201):
            raise OpenAICheckoutError(f"ChatGPT 请求失败: {resp.status_code} {str(data)[:500]}")
        return data

    def _chatgpt_approve(self, cs_id: str, processor_entity: str) -> None:
        try:
            self._chatgpt_post("/backend-api/sentinel/ping", {})
        except Exception:
            pass
        data = self._chatgpt_post(
            "/backend-api/payments/checkout/approve",
            {"checkout_session_id": cs_id, "processor_entity": processor_entity or "openai_llc"},
        )
        if data.get("result") != "approved":
            raise OpenAICheckoutError(f"ChatGPT approve 未通过: {str(data)[:500]}")

    def _fetch_pm_redirect_snap_token(self, pm_url: str) -> str:
        direct = re.search(r"app\.midtrans\.com/snap/v[14]/redirection/([a-f0-9-]{36})", pm_url)
        if direct:
            return direct.group(1)
        resp = self.ext.get(
            pm_url,
            headers={"User-Agent": self.user_agent, "Accept": "*/*"},
            allow_redirects=False,
            timeout_seconds=DEFAULT_TIMEOUT,
        )
        if resp.status_code not in (301, 302, 303, 307, 308):
            raise OpenAICheckoutError(f"pm-redirects 未返回跳转: {resp.status_code}")
        loc = resp.headers.get("Location", "")
        match = re.search(r"app\.midtrans\.com/snap/v[14]/redirection/([a-f0-9-]{36})", loc)
        if not match:
            raise OpenAICheckoutError(f"pm-redirects Location 没有 Midtrans token: {loc[:200]}")
        return match.group(1)

    def _follow_redirect_to_midtrans(self, cs_id: str, stripe_pk: str) -> str:
        params = {
            "elements_session_client[client_betas][0]": "custom_checkout_server_updates_1",
            "elements_session_client[client_betas][1]": "custom_checkout_manual_approval_1",
            "elements_session_client[elements_init_source]": "custom_checkout",
            "elements_session_client[referrer_host]": "chatgpt.com",
            "elements_session_client[session_id]": f"elements_session_{uuid.uuid4().hex[:11]}",
            "elements_session_client[stripe_js_id]": str(uuid.uuid4()),
            "elements_session_client[locale]": "en",
            "elements_session_client[is_aggregation_expected]": "false",
            "elements_options_client[saved_payment_method][enable_save]": "never",
            "elements_options_client[saved_payment_method][enable_redisplay]": "never",
            "key": stripe_pk,
            "_stripe_version": (
                "2025-03-31.basil; checkout_server_update_beta=v1; "
                "checkout_manual_approval_preview=v1"
            ),
        }
        deadline = time.time() + 60
        last = ""
        while time.time() < deadline:
            data = self._stripe_get(f"https://api.stripe.com/v1/payment_pages/{cs_id}", params)
            si = data.get("setup_intent") or {}
            if isinstance(si, dict) and si.get("status") == "requires_action":
                url = (((si.get("next_action") or {}).get("redirect_to_url") or {}).get("url") or "")
                if url:
                    return self._fetch_pm_redirect_snap_token(url)
            last = f"setup_intent={si.get('status')!r} payment_status={data.get('payment_status')!r}"
            time.sleep(1)
        raise OpenAICheckoutError(f"Midtrans snap 生成超时: {last}")

    def generate_midtrans_url_from_checkout(
        self,
        checkout: dict[str, str],
        *,
        billing: dict[str, str] | None = None,
    ) -> dict[str, str]:
        billing = billing or {}
        cs_id = checkout["checkout_session_id"]
        processor = checkout.get("processor_entity") or "openai_llc"
        stripe_pk = checkout.get("publishable_key") or DEFAULT_STRIPE_PK
        pm_id = self._stripe_create_pm(cs_id, stripe_pk, billing)
        confirm_data = self._stripe_confirm(cs_id, pm_id, stripe_pk)
        redirect = self._extract_redirect_to_url(confirm_data)
        if redirect:
            snap = self._fetch_pm_redirect_snap_token(redirect)
        else:
            self._chatgpt_approve(cs_id, processor)
            snap = self._follow_redirect_to_midtrans(cs_id, stripe_pk)
        return {
            **checkout,
            "snap_token": snap,
            "midtrans_url": f"https://app.midtrans.com/snap/v4/redirection/{snap}",
        }

    def generate_midtrans_url(self, *, billing: dict[str, str] | None = None) -> dict[str, str]:
        return self.generate_midtrans_url_from_checkout(self.create_checkout(), billing=billing)
