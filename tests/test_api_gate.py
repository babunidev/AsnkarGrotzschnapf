"""Local Instagram API gate (Azeroth-style stop after Meta blocks)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from anskar.instagram.api_gate import InstagramApiGate
from anskar.instagram.errors import InstagramError


class ApiGateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.db = Path(self.temporary.name) / "instagram.sqlite"

    def tearDown(self):
        self.temporary.cleanup()

    def test_access_block_stops_further_calls(self):
        gate = InstagramApiGate(self.db)
        gate.trip_access_blocked(detail="API access blocked")
        with self.assertRaises(InstagramError) as caught:
            gate.assert_clear()
        self.assertEqual(caught.exception.kind, "access_blocked")
        gate.record_access_ok(detail="ok")
        gate.assert_clear()

    def test_rate_limit_cooldown(self):
        gate = InstagramApiGate(self.db)
        remaining = gate.trip_rate_limit(retry_after=120, detail="limit")
        self.assertGreaterEqual(remaining, 120)
        with self.assertRaises(InstagramError) as caught:
            gate.assert_clear()
        self.assertEqual(caught.exception.kind, "rate_limit")


if __name__ == "__main__":
    unittest.main()
