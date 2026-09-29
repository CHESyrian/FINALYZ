"""
High-level financial analysis engine.

Takes a FinancialStatement → returns AnalysisResult
with core + cash-flow ratios, summary, strengths, weaknesses and recommendations.
"""

from __future__ import annotations

from .models import AnalysisResult, FinancialStatement, RatioResult
from .ratios import calculate_all_ratios
from .dupont import compute_dupont


def analyze(
    statement: FinancialStatement,
    industry: str | None = None,
) -> AnalysisResult:
    """
    Run full analysis on a normalized financial statement.

    Main entry point of the domain layer.
    ``industry`` is passed through to DuPont driver notes so thresholds match
    the same benchmark tables used by the ratio scorecard.
    """
    ratios = calculate_all_ratios(statement)
    dupont = compute_dupont(statement, industry=industry)

    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[str] = []

    for ratio in ratios:
        if ratio.status == "good":
            strengths.append(f"{ratio.name} ({ratio.abbreviation}): {ratio.interpretation}")
        elif ratio.status == "bad":
            weaknesses.append(f"{ratio.name} ({ratio.abbreviation}): {ratio.interpretation}")
            recommendations.append(_recommendation_for(ratio))
        elif ratio.status == "warning":
            recommendations.append(_recommendation_for(ratio))

    recommendations = [r for r in recommendations if r]
    summary = _build_summary(statement, ratios, strengths, weaknesses)

    return AnalysisResult(
        statement=statement,
        ratios=ratios,
        summary=summary,
        strengths=strengths,
        weaknesses=weaknesses,
        recommendations=recommendations,
        dupont=dupont.to_dict(),
    )


def _recommendation_for(ratio: RatioResult) -> str:
    mapping = {
        "CR": "Improve working capital: accelerate receivables collection or increase cash buffer.",
        "QR": "Reduce reliance on inventory and prepaid items for liquidity.",
        "CaR": "Build a stronger cash reserve to cover short-term obligations.",
        "GPM": "Review pricing and cost of goods sold. Negotiate better supplier terms.",
        "OPM": "Control operating expenses and improve operational efficiency.",
        "NPM": "Examine full cost structure. Aim for higher conversion of revenue to profit.",
        "ROA": "Improve asset utilization and overall profitability.",
        "ROE": "Focus on profitability and efficient use of shareholders' equity.",
        "DR": "Reduce the proportion of assets financed by debt.",
        "D/E": "Consider reducing debt or increasing equity to lower financial risk.",
        "ER": "Strengthen the equity base relative to total assets.",
        "EM": "Review leverage: a high equity multiplier boosts ROE but increases financial risk.",
        "ICR": "Improve EBIT or reduce interest-bearing debt to strengthen coverage.",
        "ATO": "Increase sales relative to the asset base or optimize underused assets.",
        "RT": "Tighten credit policy and improve collection processes.",
        "ITR": "Optimize inventory levels; reduce slow-moving stock.",
        "DSO": "Accelerate collections: tighten credit terms and follow up overdue invoices.",
        "DIO": "Reduce inventory days by improving demand planning and clearing slow movers.",
        "DPO": "Negotiate longer supplier payment terms where sustainable.",
        "CCC": "Shorten the cash conversion cycle via faster collections, leaner inventory, and supplier terms.",
        "ROIC": "Improve operating returns on capital employed; review underperforming assets or projects.",
        "OCFR": "Strengthen operating cash generation or reduce short-term liabilities.",
        "CFM": "Improve conversion of sales into operating cash (collections, working capital).",
        "FCFM": "Review CapEx and operating cash so more free cash remains after reinvestment.",
        "CCR": "Investigate timing differences between profit and cash (receivables, inventory, accruals).",
    }
    return mapping.get(ratio.abbreviation, f"Review and improve {ratio.name}.")


def _build_summary(
    statement: FinancialStatement,
    ratios: list[RatioResult],
    strengths: list[str],
    weaknesses: list[str],
) -> str:
    company = statement.company_name or "The company"
    period = f" for {statement.period}" if statement.period else ""

    bad_count = sum(1 for r in ratios if r.status == "bad")
    warning_count = sum(1 for r in ratios if r.status == "warning")
    available = sum(1 for r in ratios if r.status != "n/a")
    total = len(ratios)

    sources: list[str] = []
    if statement.has_income_statement_depth() or statement.revenue is not None:
        sources.append("income statement")
    if statement.has_balance_sheet_depth():
        sources.append("balance sheet")
    if statement.has_cash_flow_depth():
        sources.append("cash flow")
    source_note = ", ".join(sources) if sources else "limited data"

    if available == 0:
        return (
            f"{company}{period}: Not enough data to perform a meaningful analysis. "
            "Please supply at least revenue and key balance-sheet, profitability, or cash-flow figures."
        )

    parts = [
        f"{company}{period} – analysis based on {available}/{total} ratios "
        f"(from {source_note})."
    ]

    if bad_count == 0 and warning_count == 0:
        parts.append("Overall financial health appears solid with no major red flags.")
    elif bad_count == 0:
        parts.append(
            f"Financial health is acceptable; {warning_count} indicator(s) warrant monitoring."
        )
    else:
        parts.append(
            f"There are {bad_count} area(s) of concern and {warning_count} item(s) needing attention."
        )

    if strengths:
        parts.append(f"Strengths: {len(strengths)}.")
    if weaknesses:
        parts.append(f"Weaknesses: {len(weaknesses)}.")

    if not statement.has_cash_flow_depth():
        parts.append(
            "Add operating cash flow (and CapEx) to unlock cash-flow ratios and quality-of-earnings checks."
        )

    return " ".join(parts)
