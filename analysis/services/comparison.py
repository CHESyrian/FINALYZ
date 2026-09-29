"""
Multi-period comparison: compare ratio sets across two periods.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from .models import FinancialStatement, RatioResult
from .analyzer import analyze
from .benchmarks import enrich_ratios_with_benchmarks


def _ratio_map(ratios: list[RatioResult] | list[dict]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for r in ratios or []:
        if isinstance(r, dict):
            abbr = r.get("abbreviation") or ""
            out[abbr] = r
        else:
            out[r.abbreviation] = {
                "name": r.name,
                "abbreviation": r.abbreviation,
                "value": str(r.value) if r.value is not None else None,
                "formatted": r.formatted,
                "status": r.status,
                "category": r.category,
                "unit": r.unit,
            }
    return out


def _pct_change(old: Decimal | None, new: Decimal | None) -> str | None:
    if old is None or new is None:
        return None
    if old == 0:
        return None
    change = ((new - old) / abs(old)) * Decimal("100")
    return f"{change.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):+f}%"


def _direction(old: Decimal | None, new: Decimal | None) -> str:
    if old is None or new is None:
        return "n/a"
    if new > old:
        return "up"
    if new < old:
        return "down"
    return "flat"


def _derive_period_averages(
    period_a: FinancialStatement,
    period_b: FinancialStatement,
) -> tuple[FinancialStatement, bool]:
    """
    When both periods have ending total assets / equity and the current period
    has no explicit average, set average = (A + B) / 2 on period B.

    This matches the textbook definition of average assets/equity for the span
    from baseline (A) to current (B). Does not overwrite averages the user
    already supplied.

    Returns (period_b, derived) where derived is True if any average was set.
    """
    derived = False

    # Average Total Assets
    if (
        period_b.average_total_assets is None
        and period_a.total_assets is not None
        and period_b.total_assets is not None
    ):
        avg_assets = (period_a.total_assets + period_b.total_assets) / Decimal("2")
        object.__setattr__(period_b, "average_total_assets", avg_assets)
        derived = True

    # Average Equity
    if (
        period_b.average_equity is None
        and period_a.equity is not None
        and period_b.equity is not None
    ):
        avg_equity = (period_a.equity + period_b.equity) / Decimal("2")
        object.__setattr__(period_b, "average_equity", avg_equity)
        derived = True

    # Optional WC averages when both sides have the line items
    if (
        period_b.average_inventory is None
        and period_a.inventory is not None
        and period_b.inventory is not None
    ):
        object.__setattr__(
            period_b,
            "average_inventory",
            (period_a.inventory + period_b.inventory) / Decimal("2"),
        )
        derived = True

    if (
        period_b.average_receivables is None
        and period_a.receivables is not None
        and period_b.receivables is not None
    ):
        object.__setattr__(
            period_b,
            "average_receivables",
            (period_a.receivables + period_b.receivables) / Decimal("2"),
        )
        derived = True

    if (
        period_b.average_accounts_payable is None
        and period_a.accounts_payable is not None
        and period_b.accounts_payable is not None
    ):
        object.__setattr__(
            period_b,
            "average_accounts_payable",
            (period_a.accounts_payable + period_b.accounts_payable) / Decimal("2"),
        )
        derived = True

    return period_b, derived


def compare_periods(
    period_a: FinancialStatement,
    period_b: FinancialStatement,
    *,
    industry: str = "general",
    label_a: str | None = None,
    label_b: str | None = None,
) -> dict[str, Any]:
    """
    Analyze two statements and return a side-by-side ratio comparison.

    period_a is treated as the baseline (earlier); period_b as the current period.
    When both periods supply ending Total Assets / Equity (and related WC lines)
    and period_b has no explicit averages, averages are derived as (A + B) / 2
    so ATO, EM, ROA, ROE, and turnover ratios use the textbook denominator.
    """
    period_b, averages_derived = _derive_period_averages(period_a, period_b)

    result_a = analyze(period_a, industry=industry)
    result_b = analyze(period_b, industry=industry)

    enriched_a = enrich_ratios_with_benchmarks(result_a.ratios, industry)
    enriched_b = enrich_ratios_with_benchmarks(result_b.ratios, industry)

    map_a = _ratio_map(enriched_a)
    map_b = _ratio_map(enriched_b)
    all_abbrs = list(dict.fromkeys([*map_a.keys(), *map_b.keys()]))

    rows: list[dict[str, Any]] = []
    improved = 0
    worsened = 0

    for abbr in all_abbrs:
        a = map_a.get(abbr) or {}
        b = map_b.get(abbr) or {}
        try:
            va = Decimal(str(a["value"])) if a.get("value") not in (None, "", "None") else None
        except Exception:
            va = None
        try:
            vb = Decimal(str(b["value"])) if b.get("value") not in (None, "", "None") else None
        except Exception:
            vb = None

        direction = _direction(va, vb)
        # For lower-is-better solvency ratios, invert "improved" intuition lightly
        lower_better = abbr in ("DR", "D/E")
        if direction == "up":
            if lower_better:
                worsened += 1
                trend = "worse"
            else:
                improved += 1
                trend = "better"
        elif direction == "down":
            if lower_better:
                improved += 1
                trend = "better"
            else:
                worsened += 1
                trend = "worse"
        else:
            trend = "flat" if direction == "flat" else "n/a"

        rows.append(
            {
                "abbreviation": abbr,
                "name": b.get("name") or a.get("name") or abbr,
                "category": b.get("category") or a.get("category") or "",
                "period_a": a.get("formatted") or "N/A",
                "period_b": b.get("formatted") or "N/A",
                "status_a": a.get("status") or "n/a",
                "status_b": b.get("status") or "n/a",
                "change": _pct_change(va, vb),
                "direction": direction,
                "trend": trend,
            }
        )

    label_a = label_a or period_a.period or "Period A"
    label_b = label_b or period_b.period or "Period B"

    return {
        "label_a": label_a,
        "label_b": label_b,
        "company_name": period_b.company_name or period_a.company_name,
        "industry": industry,
        "summary_a": result_a.summary,
        "summary_b": result_b.summary,
        "rows": rows,
        "improved": improved,
        "worsened": worsened,
        "available": sum(1 for r in rows if r["period_a"] != "N/A" or r["period_b"] != "N/A"),
        "averages_derived": averages_derived,
    }
