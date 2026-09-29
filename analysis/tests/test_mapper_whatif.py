"""Tests for Excel mapper and what-if simulation."""

from decimal import Decimal
from django.test import SimpleTestCase

from analysis.services.mapper import auto_map_headers, apply_mapping, COLUMN_ALIASES
from analysis.services.sample_data import get_sample_statement
from analysis.services.whatif import (
    statement_to_dict,
    statement_from_dict,
    apply_percent_changes,
    run_whatif,
)


class MapperTests(SimpleTestCase):
    def test_auto_map_common_headers(self):
        headers = ["Net Sales", "Cost of Goods Sold", "Total Assets", "Total Equity"]
        mapping = auto_map_headers(headers)
        self.assertEqual(mapping.get("revenue"), "Net Sales")
        self.assertEqual(mapping.get("cogs"), "Cost of Goods Sold")
        self.assertEqual(mapping.get("total_assets"), "Total Assets")
        self.assertEqual(mapping.get("equity"), "Total Equity")

    def test_apply_mapping_builds_statement(self):
        headers = ["Revenue", "COGS", "Net Income"]
        rows = [["1000", "400", "150"]]
        mapping = {"revenue": "Revenue", "cogs": "COGS", "net_income": "Net Income"}
        stmt = apply_mapping(headers, rows, mapping, company_name="T", period="FY1")
        self.assertEqual(stmt.revenue, Decimal("1000"))
        self.assertEqual(stmt.cogs, Decimal("400"))
        self.assertEqual(stmt.gross_profit, Decimal("600"))
        self.assertEqual(stmt.company_name, "T")

    def test_apply_mapping_requires_revenue(self):
        with self.assertRaises(ValueError):
            apply_mapping(["COGS"], [["100"]], {"cogs": "COGS"})

    def test_aliases_cover_key_fields(self):
        for field in ("revenue", "operating_cash_flow", "equity"):
            self.assertIn(field, COLUMN_ALIASES)
            self.assertTrue(COLUMN_ALIASES[field])


class WhatIfTests(SimpleTestCase):
    def test_roundtrip_statement_dict(self):
        s = get_sample_statement()
        d = statement_to_dict(s)
        s2 = statement_from_dict(d)
        self.assertEqual(s2.revenue, s.revenue)
        self.assertEqual(s2.operating_cash_flow, s.operating_cash_flow)

    def test_percent_change_revenue(self):
        s = get_sample_statement()
        new_s, log = apply_percent_changes(s, {"revenue": Decimal("10")})
        self.assertIn("revenue", log)
        expected = s.revenue * Decimal("1.10")
        self.assertEqual(new_s.revenue, expected)

    def test_run_whatif_comparison(self):
        s = get_sample_statement()
        result = run_whatif(s, {"revenue": Decimal("-10")}, industry="manufacturing")
        self.assertIn("comparison", result)
        self.assertIn("change_log", result)
        self.assertTrue(result["comparison"])
