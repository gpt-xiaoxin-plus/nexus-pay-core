from __future__ import annotations

import base64
import tempfile
import unittest
from pathlib import Path

from opai.core.burp_capture import build_combined_dataset, extract_protocol_literals, import_capture


def b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


class BurpCaptureTests(unittest.TestCase):
    def test_import_capture_decodes_redacts_and_summarizes(self):
        request = (
            "POST /cvs/v1/verify HTTP/1.1\r\n"
            "Host: accounts.goto-products.com\r\n"
            "Authorization: Bearer live-token\r\n"
            "Content-Type: application/json\r\n"
            "\r\n"
            '{"phone_number":"8123456789","otp":"1234","pin":"147258","flow":"signup_na"}'
        )
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            "Set-Cookie: sid=secret\r\n"
            "\r\n"
            '{"data":{"verification_token":"secret-token","otp_length":4}}'
        )
        xml = f"""<?xml version="1.0"?>
<items>
  <item>
    <time>Tue May 26 10:45:14 CST 2026</time>
    <url><![CDATA[https://accounts.goto-products.com/cvs/v1/verify]]></url>
    <host>accounts.goto-products.com</host>
    <port>443</port>
    <protocol>https</protocol>
    <method><![CDATA[POST]]></method>
    <path><![CDATA[/cvs/v1/verify]]></path>
    <extension>null</extension>
    <request base64="true"><![CDATA[{b64(request)}]]></request>
    <status>200</status>
    <responselength>64</responselength>
    <mimetype>JSON</mimetype>
    <response base64="true"><![CDATA[{b64(response)}]]></response>
    <comment></comment>
  </item>
</items>
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "capture.xml"
            path.write_text(xml, encoding="utf-8")
            report = import_capture(path)

        self.assertEqual(report["summary"]["total_items"], 1)
        self.assertEqual(report["summary"]["total_endpoints"], 1)
        endpoint = report["summary"]["endpoints"][0]
        self.assertEqual(endpoint["endpoint"], "POST accounts.goto-products.com/cvs/v1/verify")
        self.assertEqual(endpoint["statuses"], {"200": 1})
        self.assertEqual(endpoint["request_body_shapes"], [{
            "kind": "json",
            "shape": {
                "flow": "str",
                "otp": "str",
                "phone_number": "str",
                "pin": "str",
            },
        }])
        self.assertNotIn("redacted_sample", endpoint["request_body_shapes"][0])

        rec = report["records"][0]
        self.assertEqual(rec["request"]["headers"]["Authorization"], "<redacted>")
        self.assertEqual(rec["response"]["headers"]["Set-Cookie"], "<redacted>")

        sample = rec["request"]["body"]["redacted_sample"]
        self.assertEqual(sample["phone_number"], "<redacted>")
        self.assertEqual(sample["otp"], "<redacted>")
        self.assertEqual(sample["pin"], "<redacted>")
        self.assertEqual(sample["flow"], "signup_na")

        resp_sample = rec["response"]["body"]["redacted_sample"]
        self.assertEqual(resp_sample["data"]["verification_token"], "<redacted>")
        self.assertEqual(resp_sample["data"]["otp_length"], 4)

    def test_extract_protocol_literals_and_bundle(self):
        request = (
            "GET /v1/users/profile HTTP/1.1\r\n"
            "Host: customer.gopayapi.com\r\n"
            "\r\n"
        )
        xml = f"""<?xml version="1.0"?>
<items>
  <item>
    <time>Tue May 26 10:45:14 CST 2026</time>
    <url><![CDATA[https://customer.gopayapi.com/v1/users/profile]]></url>
    <host>customer.gopayapi.com</host>
    <port>443</port>
    <protocol>https</protocol>
    <method><![CDATA[GET]]></method>
    <path><![CDATA[/v1/users/profile]]></path>
    <extension>null</extension>
    <request base64="true"><![CDATA[{b64(request)}]]></request>
    <status>200</status>
    <responselength>0</responselength>
    <mimetype></mimetype>
    <response base64="false"></response>
    <comment></comment>
  </item>
</items>
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capture_path = root / "capture.xml"
            capture_path.write_text(xml, encoding="utf-8")
            code_root = root / "repo"
            code_root.mkdir()
            (code_root / "client.py").write_text(
                'BASE = "https://customer.gopayapi.com"\n'
                'PROFILE = "https://customer.gopayapi.com/v1/users/profile"\n',
                encoding="utf-8",
            )

            literals = extract_protocol_literals(code_root)
            self.assertIn(
                "customer.gopayapi.com/v1/users/profile",
                literals["endpoint_keys"],
            )

            dataset = build_combined_dataset(capture_path, code_root)
            self.assertEqual(
                dataset["comparison"]["capture_matched_current"],
                ["customer.gopayapi.com/v1/users/profile"],
            )
            self.assertEqual(
                dataset["comparison"]["capture_paths_matched_current"],
                ["/v1/users/profile"],
            )

    def test_bundle_supports_multiple_reference_roots(self):
        request = (
            "POST /snap/v3/accounts/tok/linking HTTP/1.1\r\n"
            "Host: app.midtrans.com\r\n"
            "\r\n"
        )
        xml = f"""<?xml version="1.0"?>
<items>
  <item>
    <url><![CDATA[https://app.midtrans.com/snap/v3/accounts/tok/linking?secret=live]]></url>
    <host>app.midtrans.com</host>
    <method><![CDATA[POST]]></method>
    <path><![CDATA[/snap/v3/accounts/tok/linking]]></path>
    <request base64="true"><![CDATA[{b64(request)}]]></request>
    <status>200</status>
    <response base64="false"></response>
  </item>
</items>
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            capture_path = root / "capture.xml"
            capture_path.write_text(xml, encoding="utf-8")
            current_root = root / "current"
            ref_a = root / "ref_a"
            ref_b = root / "ref_b"
            current_root.mkdir()
            ref_a.mkdir()
            ref_b.mkdir()
            (current_root / "client.py").write_text('BASE = "https://app.midtrans.com"\n')
            (ref_a / "pay.py").write_text(
                'LINK = "https://app.midtrans.com/snap/v3/accounts/tok/linking?token=secret"\n',
                encoding="utf-8",
            )
            (ref_b / "chat.py").write_text(
                'CHECKOUT = "https://chatgpt.com/backend-api/payments/checkout"\n',
                encoding="utf-8",
            )

            dataset = build_combined_dataset(capture_path, current_root, [ref_a, ref_b])

        self.assertEqual(len(dataset["code_sources"]["references"]), 2)
        self.assertEqual(
            dataset["comparison"]["capture_matched_reference"],
            ["app.midtrans.com/snap/v3/accounts/tok/linking"],
        )
        self.assertEqual(len(dataset["comparison"]["references"]), 2)
        self.assertIn("gopay_inventory", dataset)


if __name__ == "__main__":
    unittest.main()
