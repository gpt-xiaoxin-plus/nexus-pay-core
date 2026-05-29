from __future__ import annotations

import re
import unittest

from opai.core.gojek_client import GojekClient, generate_device_identity


class DeviceIdentityTests(unittest.TestCase):
    def test_device_identity_is_stable_for_same_seed(self):
        first = generate_device_identity("+620000000004")
        second = generate_device_identity("+620000000004")

        self.assertEqual(first, second)
        self.assertEqual(first["uniqueid"], "83f1b98676e702ee")
        self.assertRegex(first["session_id"], r"^[0-9a-f-]{36}$")

    def test_device_identity_varies_between_accounts(self):
        first = generate_device_identity("+620000000004")
        second = generate_device_identity("+620000000005")

        self.assertNotEqual(first["uniqueid"], second["uniqueid"])
        self.assertNotEqual(first["session_id"], second["session_id"])

    def test_device_identity_has_coherent_android_shape(self):
        identity = generate_device_identity("+620000000006")

        self.assertIn(",", identity["model"])
        self.assertRegex(identity["os_info"], r"^Android,(12|13|14)$")
        self.assertRegex(identity["uniqueid"], r"^[0-9a-f]{16}$")
        self.assertIn(f",8:", identity["xm1"])
        self.assertIn(",12:VKEY_DISABLED", identity["xm1"])
        self.assertIn(",13:1003", identity["xm1"])
        self.assertRegex(identity["xm1"], r",3:\d{13}-\d+")
        self.assertRegex(identity["xm1"], r",6:[0-9A-F]{2}(:[0-9A-F]{2}){5}")

    def test_xm1_request_timestamp_can_refresh_without_changing_device_profile(self):
        identity = generate_device_identity("+620000000004")
        client = GojekClient(**identity)
        built = client._build_xm1()

        without_ts_template = re.sub(r",14:\d+", ",14:<ts>", identity["xm1"])
        without_ts_built = re.sub(r",14:\d+", ",14:<ts>", built)
        self.assertEqual(without_ts_template, without_ts_built)


if __name__ == "__main__":
    unittest.main()
