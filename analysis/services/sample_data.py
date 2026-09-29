"""
Sample company data for demo mode.
"""

from decimal import Decimal

from .models import FinancialStatement


def get_sample_statement() -> FinancialStatement:
    """Return a realistic sample financial statement (Demo Manufacturing Co.)."""
    return FinancialStatement(
        company_name="Demo Manufacturing Co.",
        period="FY 2025",
        # Income Statement
        revenue=Decimal("2500000"),
        cogs=Decimal("1450000"),
        gross_profit=Decimal("1050000"),
        operating_income=Decimal("380000"),
        interest_expense=Decimal("45000"),
        net_income=Decimal("265000"),
        # Assets
        current_assets=Decimal("920000"),
        cash=Decimal("210000"),
        cash_equivalents=Decimal("40000"),
        inventory=Decimal("310000"),
        prepaid_expenses=Decimal("25000"),
        receivables=Decimal("280000"),
        total_assets=Decimal("3200000"),
        # Liabilities & Equity
        current_liabilities=Decimal("480000"),
        accounts_payable=Decimal("185000"),
        total_liabilities=Decimal("1400000"),
        total_debt=Decimal("950000"),
        equity=Decimal("1800000"),
        # Cash Flow
        operating_cash_flow=Decimal("310000"),
        capital_expenditures=Decimal("120000"),
        free_cash_flow=Decimal("190000"),
        investing_cash_flow=Decimal("-135000"),
        financing_cash_flow=Decimal("-80000"),
    )


def get_sample_form_initial() -> dict:
    """Initial data dict for ManualInputForm (demo pre-fill)."""
    s = get_sample_statement()
    return {
        "company_name": s.company_name,
        "period": s.period,
        "revenue": s.revenue,
        "cogs": s.cogs,
        "gross_profit": s.gross_profit,
        "operating_income": s.operating_income,
        "interest_expense": s.interest_expense,
        "net_income": s.net_income,
        "current_assets": s.current_assets,
        "cash": s.cash,
        "cash_equivalents": s.cash_equivalents,
        "inventory": s.inventory,
        "prepaid_expenses": s.prepaid_expenses,
        "receivables": s.receivables,
        "total_assets": s.total_assets,
        "current_liabilities": s.current_liabilities,
        "accounts_payable": s.accounts_payable,
        "total_liabilities": s.total_liabilities,
        "total_debt": s.total_debt,
        "equity": s.equity,
        "operating_cash_flow": s.operating_cash_flow,
        "capital_expenditures": s.capital_expenditures,
        "free_cash_flow": s.free_cash_flow,
        "investing_cash_flow": s.investing_cash_flow,
        "financing_cash_flow": s.financing_cash_flow,
        "industry": "manufacturing",
    }
