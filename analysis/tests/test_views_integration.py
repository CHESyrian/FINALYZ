"""Integration-style tests for manual input and compare flows."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from analysis.services.comparison import compare_periods
from analysis.services.models import FinancialStatement


User = get_user_model()


class ManualAndCompareIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester",
            password="test-pass-12345",
        )
        self.client = Client()
        self.client.login(username="tester", password="test-pass-12345")

    def test_manual_input_posts_to_report(self):
        url = reverse("analysis:manual_input")
        data = {
            "company_name": "Integration Co",
            "period": "FY 2025",
            "industry": "manufacturing",
            "revenue": "1000000",
            "net_income": "120000",
            "total_assets": "800000",
            "equity": "400000",
            "operating_income": "180000",
            "interest_expense": "20000",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analysis Report")
        self.assertContains(response, "Integration Co")
        # DuPont should be present for full inputs
        self.assertContains(response, "DuPont")
        # Session should hold last report for export
        session = self.client.session
        self.assertIn("last_report", session)
        self.assertEqual(session["last_report"].get("industry"), "manufacturing")
        self.assertTrue(session["last_report"].get("dupont", {}).get("available"))

    def test_compare_derives_averages_and_returns_result(self):
        url = reverse("analysis:compare")
        data = {
            "company_name": "Compare Co",
            "industry": "general",
            "period_a": "FY 2024",
            "period_b": "FY 2025",
            "revenue_a": "1000",
            "revenue_b": "1200",
            "net_income_a": "100",
            "net_income_b": "150",
            "total_assets_a": "800",
            "total_assets_b": "1000",
            "equity_a": "400",
            "equity_b": "500",
            "inventory_a": "100",
            "inventory_b": "120",
            "operating_cash_flow_a": "80",
            "operating_cash_flow_b": "110",
            "capital_expenditures_a": "30",
            "capital_expenditures_b": "40",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Period Comparison")
        # Auto-average note when averages were derived
        self.assertContains(response, "derived")
        session = self.client.session
        self.assertIn("last_comparison", session)
        cmp = session["last_comparison"]
        self.assertTrue(cmp.get("averages_derived"))
        # Domain-level check: ATO for B uses average assets
        a = FinancialStatement(
            revenue=Decimal("1000"),
            total_assets=Decimal("800"),
            equity=Decimal("400"),
            net_income=Decimal("100"),
        )
        b = FinancialStatement(
            revenue=Decimal("1200"),
            total_assets=Decimal("1000"),
            equity=Decimal("500"),
            net_income=Decimal("150"),
        )
        result = compare_periods(a, b)
        self.assertEqual(b.average_total_assets, Decimal("900"))
        self.assertEqual(b.average_equity, Decimal("450"))
        self.assertTrue(result["averages_derived"])
