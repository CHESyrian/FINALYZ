"""Tests for multi-period comparison."""

from decimal import Decimal
from django.test import SimpleTestCase

from analysis.services.models import FinancialStatement
from analysis.services.comparison import compare_periods
from analysis.services.sample_data import get_sample_statement


class ComparisonTests(SimpleTestCase):
    def test_compare_detects_improvement(self):
        a = FinancialStatement(
            revenue=Decimal("1000"),
            net_income=Decimal("50"),
            total_assets=Decimal("2000"),
            equity=Decimal("1000"),
            current_assets=Decimal("400"),
            current_liabilities=Decimal("400"),
            period="FY2024",
            company_name="Co",
        )
        b = FinancialStatement(
            revenue=Decimal("1200"),
            net_income=Decimal("120"),
            total_assets=Decimal("2000"),
            equity=Decimal("1100"),
            current_assets=Decimal("600"),
            current_liabilities=Decimal("300"),
            period="FY2025",
            company_name="Co",
        )
        result = compare_periods(a, b, industry="general")
        self.assertEqual(result["label_a"], "FY2024")
        self.assertEqual(result["label_b"], "FY2025")
        self.assertTrue(result["rows"])
        self.assertGreaterEqual(result["improved"], 1)

    def test_sample_vs_weaker(self):
        strong = get_sample_statement()
        weak = get_sample_statement()
        # worsen liquidity
        object.__setattr__(weak, "current_assets", Decimal("200000"))
        object.__setattr__(weak, "period", "FY2024")
        object.__setattr__(strong, "period", "FY2025")
        result = compare_periods(weak, strong, industry="manufacturing")
        self.assertGreaterEqual(result["available"], 5)

    def test_auto_derives_average_assets_and_equity(self):
        """When both periods have ending assets/equity, period B gets (A+B)/2 averages."""
        a = FinancialStatement(
            revenue=Decimal("1000"),
            net_income=Decimal("100"),
            total_assets=Decimal("800"),
            equity=Decimal("400"),
            period="FY2024",
        )
        b = FinancialStatement(
            revenue=Decimal("1200"),
            net_income=Decimal("150"),
            total_assets=Decimal("1000"),
            equity=Decimal("500"),
            period="FY2025",
        )
        # Averages should be unset before compare
        self.assertIsNone(b.average_total_assets)
        self.assertIsNone(b.average_equity)

        result = compare_periods(a, b, industry="general")
        self.assertTrue(result["rows"])

        # After compare_periods, period B was enriched in-place
        self.assertEqual(b.average_total_assets, Decimal("900"))  # (800+1000)/2
        self.assertEqual(b.average_equity, Decimal("450"))  # (400+500)/2

        # ATO for B should use average assets: 1200 / 900 = 1.333...
        ato_row = next(r for r in result["rows"] if r["abbreviation"] == "ATO")
        self.assertNotEqual(ato_row["period_b"], "N/A")

    def test_explicit_average_not_overwritten(self):
        """User-supplied average on period B must not be replaced."""
        a = FinancialStatement(
            revenue=Decimal("1000"),
            total_assets=Decimal("800"),
            equity=Decimal("400"),
            period="A",
        )
        b = FinancialStatement(
            revenue=Decimal("1200"),
            total_assets=Decimal("1000"),
            equity=Decimal("500"),
            average_total_assets=Decimal("950"),  # explicit
            average_equity=Decimal("480"),
            period="B",
        )
        compare_periods(a, b)
        self.assertEqual(b.average_total_assets, Decimal("950"))
        self.assertEqual(b.average_equity, Decimal("480"))
