from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from opai.core.offline_full_flow import run_offline_full_flow, validate_flow_dataset


def dataset_with_paths(paths: list[str]) -> dict:
    return {
        "capture_summary": {
            "endpoints": [
                {
                    "method": "POST",
                    "host": "example.test",
                    "path": path,
                    "endpoint": f"POST example.test{path}",
                    "count": 1,
                    "statuses": {"200": 1},
                }
                for path in paths
            ]
        }
    }


class OfflineFullFlowTests(unittest.TestCase):
    def test_validate_flow_dataset_and_run_success(self):
        data = dataset_with_paths([
            "/goto-auth/login/methods",
            "/cvs/v1/methods",
            "/cvs/v1/initiate",
            "/cvs/v1/verify",
            "/v7/customers/signup",
            "/goto-auth/token",
            "/api/v2/users/pins/setup/tokens",
            "/v1/users/profile",
            "/v1/payment-options/balances",
        ])

        validations = validate_flow_dataset(data)
        self.assertTrue(all(v["ok"] for v in validations))

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dataset.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            result = run_offline_full_flow(path)

        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "offline_mock")
        self.assertEqual(result["phases"][-1]["transaction_status"], "settlement")

    def test_run_reports_missing_shapes(self):
        data = dataset_with_paths(["/cvs/v1/methods"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dataset.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            result = run_offline_full_flow(path)

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "dataset_missing_required_protocol_shapes")
        self.assertTrue(result["missing_steps"])


if __name__ == "__main__":
    unittest.main()
