"""
What-if simulation: change statement values, recalculate ratios, compare to baseline.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from typing import Any

from .models import FinancialStatement, AnalysisResult, RatioResult
from .analyzer import analyze
from .benchmarks import enrich_ratios_with_benchmarks


# Fields users can stress-test (label, form key)
WHATIF_FIELDS: list[tuple[str, str]] = [
    ("revenue", "Revenue"),
    ("cogs", "COGS"),
    ("net_income", "Net Income"),
    ("operating_income", "Operating Income"),
    ("interest_expense", "Interest Expense"),
    ("current_assets", "Current Assets"),
    ("current_liabilities", "Current Liabilities"),
    ("inventory", "Inventory"),
    ("total_assets", "Total Assets"),
    ("total_debt", "Total Debt"),
    ("equity", "Equity"),
    ("operating_cash_flow", "Operating Cash Flow"),
    ("capital_expenditures", "CapEx"),
]


def statement_to_dict(statement: FinancialStatement) -> dict[str, Any]:
    """Serialize statement for session storage."""
    data: dict[str, Any] = {
        "company_name": statement.company_name,
        "period": statement.period,
    }
    for key, _ in WHATIF_FIELDS:
        val = getattr(statement, key, None)
        data[key] = str(val) if val is not None else None
    # Preserve extras used by ratios
    for key in (
        "cash",
        "cash_equivalents",
        "prepaid_expenses",
        "receivables",
        "accounts_payable",
        "total_liabilities",
        "gross_profit",
        "ebit",
        "free_cash_flow",
        "investing_cash_flow",
        "financing_cash_flow",
    ):
        val = getattr(statement, key, None)
        data[key] = str(val) if val is not None else None
    return data


def statement_from_dict(data: dict[str, Any]) -> FinancialStatement:
    """Rebuild FinancialStatement from session dict."""
    def d(key: str) -> Decimal | None:
        v = data.get(key)
        if v is None or v == "":
            return None
        return Decimal(str(v))

    revenue = d("revenue")
    if revenue is None or revenue <= 0:
        raise ValueError("Baseline statement is missing revenue.")

    return FinancialStatement(
        revenue=revenue,
        cogs=d("cogs"),
        gross_profit=d("gross_profit"),
        operating_income=d("operating_income"),
        ebit=d("ebit"),
        interest_expense=d("interest_expense"),
        net_income=d("net_income"),
        current_assets=d("current_assets"),
        cash=d("cash"),
        cash_equivalents=d("cash_equivalents"),
        inventory=d("inventory"),
        prepaid_expenses=d("prepaid_expenses"),
        receivables=d("receivables"),
        total_assets=d("total_assets"),
        current_liabilities=d("current_liabilities"),
        accounts_payable=d("accounts_payable"),
        total_liabilities=d("total_liabilities"),
        total_debt=d("total_debt"),
        equity=d("equity"),
        operating_cash_flow=d("operating_cash_flow"),
        capital_expenditures=d("capital_expenditures"),
        free_cash_flow=d("free_cash_flow"),
        investing_cash_flow=d("investing_cash_flow"),
        financing_cash_flow=d("financing_cash_flow"),
        company_name=data.get("company_name"),
        period=data.get("period"),
    )


def apply_percent_changes(
    base: FinancialStatement,
    changes_pct: dict[str, Decimal],
) -> tuple[FinancialStatement, dict[str, dict[str, str]]]:
    """
    Apply percentage changes to selected fields.

    changes_pct: field -> percent (e.g. -10 means -10%).
    Returns (new_statement, change_log).
    """
    data = statement_to_dict(base)
    change_log: dict[str, dict[str, str]] = {}

    for field, pct in changes_pct.items():
        if pct is None:
            continue
        try:
            pct = Decimal(str(pct))
        except (InvalidOperation, TypeError):
            continue
        if pct == 0:
            continue
        raw = data.get(field)
        if raw is None:
            continue
        old = Decimal(str(raw))
        new = old * (Decimal("1") + pct / Decimal("100"))
        data[field] = str(new)
        change_log[field] = {
            "old": f"{old:.2f}",
            "new": f"{new:.2f}",
            "pct": f"{pct:+.2f}%",
        }

    # If revenue/cogs changed and gross_profit was derived, clear it so __post_init__ recalculates
    if "revenue" in change_log or "cogs" in change_log:
        data["gross_profit"] = None

    # Recalculate FCF from OCF − CapEx when either changes
    if "operating_cash_flow" in change_log or "capital_expenditures" in change_log:
        data["free_cash_flow"] = None

    return statement_from_dict(data), change_log


def compare_ratios(
    baseline: list[dict],
    scenario: list[dict],
) -> list[dict]:
    """Merge baseline vs scenario ratio values for display/AI."""
    by_abbr_b = {r.get("abbreviation"): r for r in baseline}
    by_abbr_s = {r.get("abbreviation"): r for r in scenario}
    out = []
    for abbr, b in by_abbr_b.items():
        s = by_abbr_s.get(abbr) or {}
        out.append({
            "abbreviation": abbr,
            "name": b.get("name"),
            "category": b.get("category"),
            "baseline": b.get("formatted"),
            "scenario": s.get("formatted"),
            "baseline_status": b.get("status"),
            "scenario_status": s.get("status"),
            "baseline_value": b.get("value"),
            "scenario_value": s.get("value"),
        })
    return out


def run_whatif(
    base_statement: FinancialStatement,
    changes_pct: dict[str, Decimal],
    industry: str | None = "general",
) -> dict[str, Any]:
    """
    Full what-if pipeline: apply changes → analyze → compare.
    """
    scenario_stmt, change_log = apply_percent_changes(base_statement, changes_pct)
    if not change_log:
        raise ValueError("No changes applied. Enter at least one non-zero percentage.")

    base_result = analyze(base_statement, industry=industry)
    scen_result = analyze(scenario_stmt, industry=industry)

    base_ratios = enrich_ratios_with_benchmarks(base_result.ratios, industry)
    scen_ratios = enrich_ratios_with_benchmarks(scen_result.ratios, industry)

    return {
        "change_log": change_log,
        "comparison": compare_ratios(base_ratios, scen_ratios),
        "scenario_statement": statement_to_dict(scenario_stmt),
        "scenario_summary_engine": scen_result.summary,
        "baseline_ratios": base_ratios,
        "scenario_ratios": scen_ratios,
    }
