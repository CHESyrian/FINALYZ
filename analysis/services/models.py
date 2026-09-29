"""
Domain models for financial analysis.

Pure Python – no Django dependency.
All monetary values use Decimal for precision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class FinancialStatement:
    """
    Normalized financial snapshot from income statement, balance sheet,
    and (optionally) cash flow statement.

    Required: revenue
    Everything else is optional (manual input or partial Excel).
    Ratios and report sections activate based on which fields are present.
    For "Average" fields: if not provided, the single-period value is used.
    """

    # --- Income Statement ---
    revenue: Decimal                                      # Net Sales / Revenue
    cogs: Decimal | None = None                           # Cost of Goods Sold
    gross_profit: Decimal | None = None                   # Revenue - COGS (auto-computed if missing)
    operating_income: Decimal | None = None               # EBIT in many cases
    ebit: Decimal | None = None                           # Explicit EBIT (falls back to operating_income)
    interest_expense: Decimal | None = None
    net_income: Decimal | None = None
    net_credit_sales: Decimal | None = None               # For Receivables Turnover (falls back to revenue)

    # --- Balance Sheet (point-in-time) ---
    current_assets: Decimal | None = None
    cash: Decimal | None = None
    cash_equivalents: Decimal | None = None
    inventory: Decimal | None = None
    prepaid_expenses: Decimal | None = None
    receivables: Decimal | None = None                    # Accounts Receivable
    total_assets: Decimal | None = None
    current_liabilities: Decimal | None = None
    accounts_payable: Decimal | None = None               # Trade / accounts payable (for DPO / CCC)
    total_liabilities: Decimal | None = None
    total_debt: Decimal | None = None                     # Interest-bearing debt (falls back to total_liabilities)
    equity: Decimal | None = None                         # Shareholders' Equity

    # --- Cash Flow Statement (optional – enables cash-flow ratios) ---
    operating_cash_flow: Decimal | None = None            # Cash from operating activities (OCF)
    capital_expenditures: Decimal | None = None           # CapEx as positive outflow amount
    free_cash_flow: Decimal | None = None                 # OCF − CapEx (auto if both present)
    investing_cash_flow: Decimal | None = None            # Optional; often negative
    financing_cash_flow: Decimal | None = None            # Optional

    # --- Averages (optional – preferred for ROA, ROE, Turnover ratios) ---
    average_total_assets: Decimal | None = None
    average_equity: Decimal | None = None
    average_inventory: Decimal | None = None
    average_receivables: Decimal | None = None
    average_accounts_payable: Decimal | None = None

    # --- Meta ---
    period: str | None = None
    company_name: str | None = None

    def __post_init__(self) -> None:
        """Coerce numeric fields to Decimal and derive convenient values."""
        for name in self.__slots__:
            value = getattr(self, name)
            if value is not None and name not in ("period", "company_name"):
                if not isinstance(value, Decimal):
                    object.__setattr__(self, name, Decimal(str(value)))

        # Auto-compute gross_profit if possible
        if self.gross_profit is None and self.revenue is not None and self.cogs is not None:
            object.__setattr__(self, "gross_profit", self.revenue - self.cogs)

        # Auto-compute free cash flow if OCF and CapEx are present
        if (
            self.free_cash_flow is None
            and self.operating_cash_flow is not None
            and self.capital_expenditures is not None
        ):
            object.__setattr__(
                self,
                "free_cash_flow",
                self.operating_cash_flow - self.capital_expenditures,
            )

    # ----- Convenience resolvers used by ratio functions -----

    def get_ebit(self) -> Decimal | None:
        return self.ebit if self.ebit is not None else self.operating_income

    def get_total_debt(self) -> Decimal | None:
        return self.total_debt if self.total_debt is not None else self.total_liabilities

    def get_average_assets(self) -> Decimal | None:
        return self.average_total_assets if self.average_total_assets is not None else self.total_assets

    def get_average_equity(self) -> Decimal | None:
        return self.average_equity if self.average_equity is not None else self.equity

    def get_average_inventory(self) -> Decimal | None:
        return self.average_inventory if self.average_inventory is not None else self.inventory

    def get_average_receivables(self) -> Decimal | None:
        return self.average_receivables if self.average_receivables is not None else self.receivables

    def get_average_payables(self) -> Decimal | None:
        return (
            self.average_accounts_payable
            if self.average_accounts_payable is not None
            else self.accounts_payable
        )

    def get_net_credit_sales(self) -> Decimal | None:
        return self.net_credit_sales if self.net_credit_sales is not None else self.revenue

    def get_cash_and_equivalents(self) -> Decimal | None:
        if self.cash is None and self.cash_equivalents is None:
            return None
        return (self.cash or Decimal("0")) + (self.cash_equivalents or Decimal("0"))

    def get_invested_capital(self) -> Decimal | None:
        """
        Approximate invested capital for ROIC:
        Total Debt + Equity − Cash & Equivalents (cash subtracted when known).
        Falls back to Total Debt + Equity when cash is unavailable.
        """
        debt = self.get_total_debt()
        equity = self.equity
        if debt is None or equity is None:
            return None
        cash = self.get_cash_and_equivalents()
        if cash is not None:
            return debt + equity - cash
        return debt + equity

    def get_free_cash_flow(self) -> Decimal | None:
        if self.free_cash_flow is not None:
            return self.free_cash_flow
        if self.operating_cash_flow is not None and self.capital_expenditures is not None:
            return self.operating_cash_flow - self.capital_expenditures
        return None

    def has_income_statement_depth(self) -> bool:
        return any(
            v is not None
            for v in (self.cogs, self.gross_profit, self.operating_income, self.net_income)
        )

    def has_balance_sheet_depth(self) -> bool:
        return any(
            v is not None
            for v in (
                self.current_assets,
                self.total_assets,
                self.current_liabilities,
                self.equity,
            )
        )

    def has_cash_flow_depth(self) -> bool:
        return self.operating_cash_flow is not None


@dataclass(slots=True)
class RatioResult:
    """Single ratio with value, status and explanation."""

    name: str
    abbreviation: str
    value: Decimal | None
    formatted: str
    unit: str                 # "x" | "%"
    status: str               # "good" | "warning" | "bad" | "n/a"
    interpretation: str
    category: str             # "liquidity" | "profitability" | "solvency" | "efficiency" | "cash_flow"
    formula: str
    source_statement: str = ""  # "income_statement" | "balance_sheet" | "cash_flow" | "mixed"


@dataclass(slots=True)
class AnalysisResult:
    """Complete analysis output."""

    statement: FinancialStatement
    ratios: list[RatioResult] = field(default_factory=list)
    summary: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    # Optional DuPont breakdown (dict form for session/JSON friendliness)
    dupont: dict[str, Any] | None = None

    def ratios_by_category(self) -> dict[str, list[RatioResult]]:
        result: dict[str, list[RatioResult]] = {}
        for r in self.ratios:
            result.setdefault(r.category, []).append(r)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
            "dupont": self.dupont,
            "ratios": [
                {
                    "name": r.name,
                    "abbreviation": r.abbreviation,
                    "value": str(r.value) if r.value is not None else None,
                    "formatted": r.formatted,
                    "unit": r.unit,
                    "status": r.status,
                    "interpretation": r.interpretation,
                    "category": r.category,
                    "formula": r.formula,
                }
                for r in self.ratios
            ],
        }
