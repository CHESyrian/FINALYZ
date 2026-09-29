"""Tests for AI JSON parse / truncation repair (no network)."""

from django.test import SimpleTestCase

from analysis.services.ai_commentary import _parse_json_response, _repair_truncated_json


class AIParseTests(SimpleTestCase):
    def test_full_json(self):
        raw = (
            '{"executive_summary": "Healthy.", "key_strengths": ["a"], '
            '"key_risks": [], "recommendations": ["r"], "questions_to_ask": [], '
            '"tone_note": "ok", "ratio_notes": {"CR": "fine"}}'
        )
        data = _parse_json_response(raw)
        self.assertEqual(data["executive_summary"], "Healthy.")
        self.assertEqual(data["key_strengths"], ["a"])
        self.assertIn("CR", data["ratio_notes"])

    def test_truncated_json_repaired(self):
        truncated = (
            '{\n "executive_summary": "Demo Manufacturing Co. demonstrated solid '
            "financial health for FY 2025, supported by healthy liquidity"
        )
        repaired = _repair_truncated_json(truncated)
        self.assertTrue(repaired.endswith('"') or repaired.endswith("}"))
        data = _parse_json_response(truncated)
        self.assertIn("Demo Manufacturing", data["executive_summary"])
