from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from opai.core.gopay_payment_protocol import GoPayPayment
from opai.core.payment_fingerprint import (
    build_payment_fingerprint,
    ensure_account_payment_fingerprint,
    payment_fingerprint_headers,
)


class PaymentFingerprintTests(unittest.TestCase):
    def test_build_payment_fingerprint_is_stable_per_account(self):
        first = build_payment_fingerprint(phone="+620000000002", local="81234567890", account_id="acct-1")
        second = build_payment_fingerprint(phone="+620000000002", local="81234567890", account_id="acct-1")
        other = build_payment_fingerprint(phone="+620000000003", local="81234567891", account_id="acct-2")

        self.assertEqual(first, second)
        self.assertNotEqual(first["profile_id"], other["profile_id"])
        self.assertIn("Chrome/", first["user_agent"])

    def test_ensure_account_payment_fingerprint_preserves_saved_profile(self):
        account = {
            "phone": "+620000000002",
            "local": "81234567890",
            "account_id": "acct-1",
        }
        saved = ensure_account_payment_fingerprint(account)
        account["phone"] = "+6280000000000"
        self.assertEqual(ensure_account_payment_fingerprint(account), saved)

    def test_headers_include_browser_fingerprint_fields(self):
        profile = build_payment_fingerprint(phone="+620000000002")
        headers = payment_fingerprint_headers(profile)

        self.assertEqual(headers["User-Agent"], profile["user_agent"])
        self.assertEqual(headers["Sec-CH-UA"], profile["sec_ch_ua"])
        self.assertEqual(headers["X-Timezone"], profile["timezone"])
        self.assertEqual(headers["X-User-Locale"], "id_ID")
        self.assertEqual(headers["Viewport-Width"], str(profile["viewport"]["width"]))

    def test_gopay_payment_uses_supplied_fingerprint(self):
        profile = build_payment_fingerprint(phone="+620000000002")
        payment = GoPayPayment(payment_fingerprint=profile)

        self.assertEqual(payment._headers["User-Agent"], profile["user_agent"])
        self.assertEqual(payment._headers["Accept-Language"], "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7")
        self.assertEqual(payment._headers["Sec-CH-UA"], profile["sec_ch_ua"])
        self.assertEqual(payment._headers["X-Timezone"], "Asia/Jakarta")
        self.assertEqual(payment._headers["Viewport-Width"], str(profile["viewport"]["width"]))

    def test_gopay_payment_rejects_fingerprint_drift(self):
        profile = build_payment_fingerprint(phone="+620000000002")
        payment = GoPayPayment(payment_fingerprint=profile)
        payment._headers["User-Agent"] = "drifted"

        with self.assertRaisesRegex(Exception, "payment fingerprint drift"):
            payment._request_headers()

    def test_migrate_account_payment_fingerprints(self):
        from opai.core import gopay_protocol_worker as worker

        old_path = worker.ACCOUNTS_FILE
        try:
            with tempfile.TemporaryDirectory() as tmp:
                accounts_path = Path(tmp) / "accounts.json"
                accounts_path.write_text(json.dumps([
                    {"phone": "+620000000002", "local": "81234567890", "account_id": "acct-1"},
                ]), encoding="utf-8")
                worker.ACCOUNTS_FILE = str(accounts_path)

                first = worker.migrate_account_payment_fingerprints()
                second = worker.migrate_account_payment_fingerprints()
                stored = json.loads(accounts_path.read_text(encoding="utf-8"))

            self.assertEqual(first["total"], 1)
            self.assertEqual(first["updated"], 1)
            self.assertEqual(second["updated"], 0)
            self.assertEqual(first["accounts"][0]["profile_id"], stored[0]["payment_fingerprint"]["profile_id"])
        finally:
            worker.ACCOUNTS_FILE = old_path


if __name__ == "__main__":
    unittest.main()
