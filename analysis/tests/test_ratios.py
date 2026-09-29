"""Unit tests for ratio calculations (pure domain, no Django DB)."""

from decimal import Decimal
from django.test import SimpleTestCase

from analysis.services.models import FinancialStatement
from analysis.services.ratios import (
    calculate_all_ratios,
    current_ratio,
    gross_margin,
    operating_cash_flow_ratio,
    cash_conversion_ratio,
    days_sales_outstanding,
    days_inventory_outstanding,
    days_payable_outstanding,
    cash_conversion_cycle,
    return_on_invested_capital,
    equity_multiplier,
)
from analysis.services.sample_data import get_sample_statement
from analysis.services.analyzer import analyze
from analysis.services.dupont import compute_dupont


class RatioTests(SimpleTestCase):
    def setUp(self):
        self.stmt = get_sample_statement()

    def test_sample_calculates_all_core_and_cashflow(self):
        ratios = calculate_all_ratios(self.stmt)
        available = [r for r in ratios if r.status != "n/a"]
        self.assertGreaterEqual(len(available), 20)
        abbrs = {r.abbreviation for r in available}
        self.assertIn("CR", abbrs)
        self.assertIn("OCFR", abbrs)
        self.assertIn("CCR", abbrs)
        self.assertIn("DSO", abbrs)
        self.assertIn("DIO", abbrs)
        self.assertIn("DPO", abbrs)
        self.assertIn("CCC", abbrs)
        self.assertIn("ROIC", abbrs)
        self.assertIn("EM", abbrs)

    def test_current_ratio_value(self):
        r = current_ratio(self.stmt)
        # 920000 / 480000 = 1.916...
        self.assertIsNotNone(r.value)
        self.assertAlmostEqual(float(r.value), 920000 / 480000, places=4)
        self.assertEqual(r.status, "good")

    def test_gross_margin_percent(self):
        r = gross_margin(self.stmt)
        self.assertIsNotNone(r.value)
        expected = Decimal("1050000") / Decimal("2500000")
        self.assertEqual(r.value, expected)
        self.assertIn("%", r.formatted)

    def test_missing_fields_yield_na(self):
        thin = FinancialStatement(revenue=Decimal("1000"))
        ratios = calculate_all_ratios(thin)
        na_count = sum(1 for r in ratios if r.status == "n/a")
        self.assertGreater(na_count, 10)
        # Revenue-only can still compute some margin-like n/a without COGS
        gpm = next(r for r in ratios if r.abbreviation == "GPM")
        self.assertEqual(gpm.status, "n/a")

    def test_cash_flow_ratios_require_ocf(self):
        no_cf = FinancialStatement(
            revenue=Decimal("1000"),
            net_income=Decimal("100"),
            current_liabilities=Decimal("200"),
        )
        ocfr = operating_cash_flow_ratio(no_cf)
        self.assertEqual(ocfr.status, "n/a")

        with_cf = FinancialStatement(
            revenue=Decimal("1000"),
            net_income=Decimal("100"),
            current_liabilities=Decimal("200"),
            operating_cash_flow=Decimal("150"),
        )
        ocfr2 = operating_cash_flow_ratio(with_cf)
        self.assertIsNotNone(ocfr2.value)
        ccr = cash_conversion_ratio(with_cf)
        self.assertEqual(ccr.value, Decimal("1.5"))

    def test_dso_dio_dpo_ccc_sample(self):
        dso = days_sales_outstanding(self.stmt)
        # 365 * 280000 / 2500000 ≈ 40.88 days
        self.assertIsNotNone(dso.value)
        self.assertAlmostEqual(float(dso.value), 365 * 280000 / 2500000, places=2)
        self.assertEqual(dso.unit, "days")

        dio = days_inventory_outstanding(self.stmt)
        # 365 * 310000 / 1450000 ≈ 78.07 days
        self.assertIsNotNone(dio.value)
        self.assertAlmostEqual(float(dio.value), 365 * 310000 / 1450000, places=2)

        dpo = days_payable_outstanding(self.stmt)
        # 365 * 185000 / 1450000 ≈ 46.59 days
        self.assertIsNotNone(dpo.value)
        self.assertAlmostEqual(float(dpo.value), 365 * 185000 / 1450000, places=2)

        ccc = cash_conversion_cycle(self.stmt)
        self.assertIsNotNone(ccc.value)
        expected_ccc = dso.value + dio.value - dpo.value
        self.assertEqual(ccc.value, expected_ccc)

    def test_dpo_and_ccc_require_payables(self):
        no_ap = FinancialStatement(
            revenue=Decimal("1000"),
            cogs=Decimal("600"),
            inventory=Decimal("100"),
            receivables=Decimal("80"),
        )
        self.assertEqual(days_payable_outstanding(no_ap).status, "n/a")
        self.assertEqual(cash_conversion_cycle(no_ap).status, "n/a")

    def test_roic_sample(self):
        roic = return_on_invested_capital(self.stmt)
        # EBIT 380000 / (950000 + 1800000 - 250000) = 380000 / 2500000 = 0.152
        self.assertIsNotNone(roic.value)
        invested = Decimal("950000") + Decimal("1800000") - Decimal("250000")
        self.assertEqual(roic.value, Decimal("380000") / invested)
        self.assertIn("%", roic.formatted)

    def test_equity_multiplier_sample(self):
        em = equity_multiplier(self.stmt)
        # 3200000 / 1800000 ≈ 1.777...
        self.assertIsNotNone(em.value)
        self.assertAlmostEqual(float(em.value), 3200000 / 1800000, places=4)
        self.assertEqual(em.unit, "x")

    def test_dupont_five_factor_on_sample(self):
        d = compute_dupont(self.stmt, industry="manufacturing")
        self.assertTrue(d.available)
        self.assertEqual(d.model, "5-factor")
        self.assertEqual(len(d.components), 5)
        abbrs = {c.abbreviation for c in d.components}
        self.assertEqual(abbrs, {"TB", "IB", "EBITM", "ATO", "EM"})
        self.assertIsNotNone(d.product)
        self.assertIsNotNone(d.roe_direct)
        # Product should be close to direct ROE (sample has consistent figures)
        self.assertAlmostEqual(float(d.product), float(d.roe_direct), places=3)
        self.assertTrue(d.drivers)

    def test_dupont_drivers_industry_aware(self):
        """ATO strength threshold is higher for retail than technology."""
        stmt = FinancialStatement(
            revenue=Decimal("1000"),
            net_income=Decimal("40"),
            total_assets=Decimal("1200"),
            equity=Decimal("600"),
            operating_income=Decimal("60"),
            interest_expense=Decimal("10"),
        )
        # ATO = 1000/1200 ≈ 0.83 — above tech good (0.35), below retail good (1.0)
        d_retail = compute_dupont(stmt, industry="retail")
        d_tech = compute_dupont(stmt, industry="technology")
        retail_ato_strength = any("Asset turnover is efficient" in n for n in d_retail.drivers)
        tech_ato_strength = any("Asset turnover is efficient" in n for n in d_tech.drivers)
        self.assertFalse(retail_ato_strength)
        self.assertTrue(tech_ato_strength)

    def test_dupont_three_factor_without_ebit(self):
        thin = FinancialStatement(
            revenue=Decimal("1000"),
            net_income=Decimal("100"),
            total_assets=Decimal("2000"),
            equity=Decimal("1000"),
        )
        d = compute_dupont(thin)
        self.assertTrue(d.available)
        self.assertEqual(d.model, "3-factor")
        self.assertEqual(len(d.components), 3)

    def test_dupont_unavailable_without_equity(self):
        thin = FinancialStatement(revenue=Decimal("1000"), net_income=Decimal("100"))
        d = compute_dupont(thin)
        self.assertFalse(d.available)

    def test_analyze_includes_dupont(self):
        result = analyze(self.stmt, industry="manufacturing")
        self.assertIsNotNone(result.dupont)
        self.assertTrue(result.dupont["available"])
        self.assertEqual(result.dupont["model"], "5-factor")
        self.assertTrue(result.dupont.get("drivers"))

    def test_analyze_summary_mentions_sources(self):
        result = analyze(self.stmt, industry="general")
        self.assertTrue(result.summary)
        self.assertIn("ratio", result.summary.lower())
        self.assertTrue(result.strengths or result.weaknesses or result.recommendations)
