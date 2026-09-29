"""Unit tests for industry benchmarks and scorecard."""

from decimal import Decimal
from django.test import SimpleTestCase

from analysis.services.models import FinancialStatement
from analysis.services.ratios import calculate_all_ratios
from analysis.services.sample_data import get_sample_statement
from analysis.services.benchmarks import (
    get_benchmarks,
    enrich_ratios_with_benchmarks,
    build_benchmark_scorecard,
    compare_to_benchmark,
)


class BenchmarkTests(SimpleTestCase):
    def setUp(self):
        self.stmt = get_sample_statement()
        self.ratios = calculate_all_ratios(self.stmt)

    def test_industry_overrides_differ_from_general(self):
        general = get_benchmarks("general")
        mfg = get_benchmarks("manufacturing")
        retail = get_benchmarks("retail")
        tech = get_benchmarks("technology")

        # Manufacturing inventory days higher median than general
        self.assertGreater(mfg["DIO"].median, general["DIO"].median)
        # Retail DSO much lower (cash-heavy)
        self.assertLess(retail["DSO"].median, general["DSO"].median)
        # Tech ROIC target higher
        self.assertGreater(tech["ROIC"].median, general["ROIC"].median)
        # Tech EM lower (less leverage)
        self.assertLess(tech["EM"].median, general["EM"].median)

    def test_cash_flow_medians_differ_by_industry(self):
        general = get_benchmarks("general")
        tech = get_benchmarks("technology")
        retail = get_benchmarks("retail")
        self.assertGreater(tech["CFM"].median, general["CFM"].median)
        self.assertLess(retail["CFM"].median, general["CFM"].median)

    def test_enrich_sets_benchmark_fields(self):
        enriched = enrich_ratios_with_benchmarks(self.ratios, "manufacturing")
        with_bench = [r for r in enriched if r.get("benchmark_median")]
        self.assertGreater(len(with_bench), 10)
        dso = next(r for r in enriched if r["abbreviation"] == "DSO")
        self.assertIsNotNone(dso["benchmark_median"])
        self.assertIn(dso["vs_benchmark"], ("above", "near", "below"))

    def test_scorecard_on_sample(self):
        enriched = enrich_ratios_with_benchmarks(self.ratios, "manufacturing")
        card = build_benchmark_scorecard(enriched, "manufacturing")
        self.assertTrue(card["available"])
        self.assertEqual(card["industry"], "manufacturing")
        self.assertGreater(card["total"], 15)
        self.assertEqual(
            card["good"] + card["warning"] + card["bad"],
            card["total"],
        )
        self.assertIn(card["grade"], ("A", "B", "C", "D", "F"))
        self.assertTrue(card["summary"])

    def test_scorecard_empty_when_no_ratios(self):
        card = build_benchmark_scorecard([], "general")
        self.assertFalse(card["available"])
        self.assertEqual(card["grade"], "N/A")

    def test_compare_respects_direction(self):
        # High CCC should be worse (lower-is-better)
        thin = FinancialStatement(
            revenue=Decimal("1000"),
            cogs=Decimal("600"),
            inventory=Decimal("400"),
            receivables=Decimal("300"),
            accounts_payable=Decimal("10"),
            total_assets=Decimal("2000"),
            equity=Decimal("1000"),
            net_income=Decimal("50"),
        )
        ratios = calculate_all_ratios(thin)
        ccc = next(r for r in ratios if r.abbreviation == "CCC")
        cmp_ = compare_to_benchmark(ccc, "retail")
        # Retail wants short CCC; this thin stmt has a long one
        self.assertIn(cmp_["status"], ("warning", "bad"))
