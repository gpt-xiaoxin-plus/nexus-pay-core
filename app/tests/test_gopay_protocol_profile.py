from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from opai.core.gopay_protocol_profile import build_protocol_profile, write_protocol_profile


class GoPayProtocolProfileTests(unittest.TestCase):
    def test_build_profile_marks_capture_and_code_evidence(self):
        dataset = {
            "sources": {"capture_xml": "capture.xml", "current_root": "repo", "reference_roots": []},
            "capture_summary": {
                "total_items": 1,
                "total_endpoints": 1,
                "endpoints": [
                    {
                        "method": "POST",
                        "host": "accounts.goto-products.com",
                        "path": "/cvs/v1/methods",
                        "endpoint": "POST accounts.goto-products.com/cvs/v1/methods",
                        "count": 1,
                        "statuses": {"200": 1},
                    }
                ],
            },
            "gopay_inventory": {
                "capture_category_counts": {"gojek_signup_otp": 1},
                "code_endpoint_inventory": [
                    {
                        "root": "repo",
                        "category": "midtrans",
                        "endpoint_key": "app.midtrans.com/snap/v3/accounts/{snap_token}/linking",
                        "host": "app.midtrans.com",
                        "path": "/snap/v3/accounts/{snap_token}/linking",
                    }
                ],
            },
            "comparison": {"references": []},
        }

        profile = build_protocol_profile(dataset)

        signup_methods = profile["flows"]["registration"][1]
        self.assertTrue(signup_methods["capture_backed"])

        linking = profile["flows"]["payment"][0]
        self.assertTrue(linking["code_backed"])

        with tempfile.TemporaryDirectory() as tmp:
            out_json = Path(tmp) / "profile.json"
            out_md = Path(tmp) / "profile.md"
            write_protocol_profile(profile, out_json, out_md)
            self.assertIn("gopay-protocol-vnext", out_json.read_text(encoding="utf-8"))
            self.assertIn("GoPay Protocol vNext", out_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
