"""
DuPont Analysis Framework.

Decomposes ROE into multiplicative drivers so users can see whether returns
come from margin, asset efficiency, or leverage (and optionally tax/interest).

3-factor (classic):
    ROE = Net Profit Margin × Asset Turnover × Equity Multiplier

5-factor (extended) when EBIT and interest are available:
    ROE = Tax Burden × Interest Burden × EBIT Margin × Asset Turnover × Equity Multiplier

Pure Decimal math; no Django.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from .models import FinancialStatement, RatioResult
from .ratios import (
    _safe_div,
    _num,
    _pct,
    net_margin,
    asset_turnover,
    equity_multiplier,
    return_on_equity,
)
from .benchmarks import get_benchmarks

ZERO = Decimal("0")
HUNDRED = Decimal("100")
# Flag when factor product and direct ROE differ by more than this (absolute ROE decimal)
_ROE_DIVERGENCE_THRESHOLD = Decimal("0.005")  # 0.5 percentage points


@dataclass(slots=True)
class DupontComponent:
    """One factor in the DuPont product."""

    name: str
    abbreviation: str
    value: Decimal | None
    formatted: str
    unit: str
    formula: str
    role: str  # short plain-language role in the chain


@dataclass(slots=True)
class DupontAnalysis:
    """
    Full DuPont breakdown for a statement.

    available is False when required inputs for at least the 3-factor model
    are missing. product_check is the reconstructed ROE from the factors
    (should approximately equal the direct ROE when data is consistent).
    """

    available: bool
    model: str = ""  # "3-factor" | "5-factor" | ""
    components: list[DupontComponent] = field(default_factory=list)
    roe_direct: Decimal | None = None
    roe_direct_formatted: str = "N/A"
    product: Decimal | None = None
    product_formatted: str = "N/A"
    narrative: str = ""
    drivers: list[str] = field(default_factory=list)  # what is helping/hurting ROE

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "model": self.model,
            "roe_direct": str(self.roe_direct) if self.roe_direct is not None else None,
            "roe_direct_formatted": self.roe_direct_formatted,
            "product": str(self.product) if self.product is not None else None,
            "product_formatted": self.product_formatted,
            "narrative": self.narrative,
            "drivers": self.drivers,
            "components": [
                {
                    "name": c.name,
                    "abbreviation": c.abbreviation,
                    "value": str(c.value) if c.value is not None else None,
                    "formatted": c.formatted,
                    "unit": c.unit,
                    "formula": c.formula,
                    "role": c.role,
                }
                for c in self.components
            ],
        }


def _fmt_pct(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    return f"{(value * HUNDRED).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}%"


def _fmt_x(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def compute_dupont(
    stmt: FinancialStatement,
    industry: str | None = None,
) -> DupontAnalysis:
    """
    Build DuPont analysis from a normalized statement.

    Prefers the 5-factor model when EBIT (or operating income) is present;
    otherwise falls back to the classic 3-factor model.

    Driver strength/weak notes use industry benchmark thresholds when
    ``industry`` is provided (same tables as the ratio scorecard).
    """
    npm_r = net_margin(stmt)
    ato_r = asset_turnover(stmt)
    em_r = equity_multiplier(stmt)
    roe_r = return_on_equity(stmt)

    npm = npm_r.value
    ato = ato_r.value
    em = em_r.value
    roe = roe_r.value

    # Minimum for 3-factor: NPM, ATO, EM
    if npm is None or ato is None or em is None:
        return DupontAnalysis(
            available=False,
            narrative=(
                "DuPont analysis needs Net Income, Revenue, Total Assets, and Equity "
                "(averages preferred). Add those fields to unlock the ROE breakdown."
            ),
        )

    ebit = stmt.get_ebit()
    interest = stmt.interest_expense
    use_five = ebit is not None and stmt.revenue is not None and stmt.net_income is not None

    components: list[DupontComponent] = []
    product: Decimal | None = None
    model = "3-factor"

    if use_five:
        # Pretax income approximation: EBIT − Interest (ignores other non-operating items)
        ebt = ebit - (interest or ZERO)
        # Guard: negative/zero EBT still allowed for ratios but division by zero blocked
        tax_burden = _safe_div(stmt.net_income, ebt)  # NI / EBT
        interest_burden = _safe_div(ebt, ebit)  # EBT / EBIT
        ebit_margin = _safe_div(ebit, stmt.revenue)  # EBIT / Revenue

        if (
            tax_burden is not None
            and interest_burden is not None
            and ebit_margin is not None
        ):
            model = "5-factor"
            product = tax_burden * interest_burden * ebit_margin * ato * em
            components = [
                DupontComponent(
                    name="Tax Burden",
                    abbreviation="TB",
                    value=tax_burden,
                    formatted=_fmt_x(tax_burden),
                    unit="x",
                    formula="Net Income / EBT (EBIT − Interest)",
                    role="Share of pretax profit kept after tax",
                ),
                DupontComponent(
                    name="Interest Burden",
                    abbreviation="IB",
                    value=interest_burden,
                    formatted=_fmt_x(interest_burden),
                    unit="x",
                    formula="EBT / EBIT",
                    role="Share of operating profit left after interest",
                ),
                DupontComponent(
                    name="EBIT Margin",
                    abbreviation="EBITM",
                    value=ebit_margin,
                    formatted=_fmt_pct(ebit_margin),
                    unit="%",
                    formula="EBIT / Revenue",
                    role="Operating profitability before financing and tax",
                ),
                DupontComponent(
                    name="Asset Turnover",
                    abbreviation="ATO",
                    value=ato,
                    formatted=_fmt_x(ato),
                    unit="x",
                    formula="Revenue / Average Total Assets",
                    role="How efficiently assets generate sales",
                ),
                DupontComponent(
                    name="Equity Multiplier",
                    abbreviation="EM",
                    value=em,
                    formatted=_fmt_x(em),
                    unit="x",
                    formula="Average Total Assets / Average Equity",
                    role="Financial leverage amplifying ROE",
                ),
            ]

    if model == "3-factor":
        product = npm * ato * em
        components = [
            DupontComponent(
                name="Net Profit Margin",
                abbreviation="NPM",
                value=npm,
                formatted=_fmt_pct(npm),
                unit="%",
                formula="Net Income / Revenue",
                role="Bottom-line profitability per sales dollar",
            ),
            DupontComponent(
                name="Asset Turnover",
                abbreviation="ATO",
                value=ato,
                formatted=_fmt_x(ato),
                unit="x",
                formula="Revenue / Average Total Assets",
                role="How efficiently assets generate sales",
            ),
            DupontComponent(
                name="Equity Multiplier",
                abbreviation="EM",
                value=em,
                formatted=_fmt_x(em),
                unit="x",
                formula="Average Total Assets / Average Equity",
                role="Financial leverage amplifying ROE",
            ),
        ]

    drivers = _identify_drivers(components, model, industry=industry)
    # Divergence note: 5-factor EBT≈EBIT−Interest ignores other non-operating items
    if (
        roe is not None
        and product is not None
        and abs(roe - product) > _ROE_DIVERGENCE_THRESHOLD
    ):
        drivers.append(
            "Factor product differs from direct ROE — other non-operating items "
            "may sit between EBIT and net income, or averages vs ending balances differ."
        )
    narrative = _build_narrative(model, roe, product, components, drivers)

    return DupontAnalysis(
        available=True,
        model=model,
        components=components,
        roe_direct=roe,
        roe_direct_formatted=_fmt_pct(roe),
        product=product,
        product_formatted=_fmt_pct(product),
        narrative=narrative,
        drivers=drivers,
    )


def _identify_drivers(
    components: list[DupontComponent],
    model: str,
    industry: str | None = None,
) -> list[str]:
    """
    Heuristic notes on which factors help or hurt ROE.

    Thresholds for NPM, EBIT margin (via OPM), ATO, and EM come from the
    industry benchmark tables when available; TB/IB keep stable universal bands.
    """
    notes: list[str] = []
    by_abbr = {c.abbreviation: c for c in components}
    benches = get_benchmarks(industry)

    def _higher_bands(abbr: str, fallback_good: str, fallback_weak: str) -> tuple[Decimal, Decimal]:
        b = benches.get(abbr)
        if b is not None and b.direction == "higher":
            return b.good_threshold, b.warning_threshold
        return Decimal(fallback_good), Decimal(fallback_weak)

    # Margin-like (higher better). EBITM uses OPM industry bands.
    margin_specs = (
        ("NPM", "NPM", "0.08", "0.03", "Net margin"),
        ("EBITM", "OPM", "0.12", "0.05", "EBIT margin"),
        ("TB", None, "0.75", "0.60", "Tax burden (after-tax retention)"),
        ("IB", None, "0.85", "0.70", "Interest burden (post-interest retention)"),
    )
    for abbr, bench_key, fb_good, fb_weak, label in margin_specs:
        c = by_abbr.get(abbr)
        if c is None or c.value is None:
            continue
        if bench_key:
            good, weak = _higher_bands(bench_key, fb_good, fb_weak)
        else:
            good, weak = Decimal(fb_good), Decimal(fb_weak)
        if c.value >= good:
            notes.append(f"{label} is a strength ({c.formatted}).")
        elif c.value < weak:
            notes.append(f"{label} is dragging ROE ({c.formatted}).")

    # Asset turnover (higher better)
    ato = by_abbr.get("ATO")
    if ato and ato.value is not None:
        ato_good, ato_weak = _higher_bands("ATO", "1.0", "0.5")
        if ato.value >= ato_good:
            notes.append(f"Asset turnover is efficient ({ato.formatted}x).")
        elif ato.value < ato_weak:
            notes.append(f"Low asset turnover ({ato.formatted}x) limits ROE.")

    # Leverage — EM is lower-is-better in benchmarks (high EM = more risk)
    em = by_abbr.get("EM")
    if em and em.value is not None:
        em_b = benches.get("EM")
        if em_b is not None and em_b.direction == "lower":
            high_lev = em_b.warning_threshold  # at/above → elevated leverage
            conservative = em_b.good_threshold  # at/below → conservative
        else:
            high_lev = Decimal("3.0")
            conservative = Decimal("1.5")
        if em.value >= high_lev:
            notes.append(
                f"High equity multiplier ({em.formatted}x) boosts ROE but increases financial risk."
            )
        elif em.value <= conservative:
            notes.append(
                f"Conservative leverage ({em.formatted}x) — ROE relies more on operations than debt."
            )

    if not notes:
        notes.append("Drivers are balanced; no single factor stands out as dominant.")
    return notes


def _build_narrative(
    model: str,
    roe: Decimal | None,
    product: Decimal | None,
    components: list[DupontComponent],
    drivers: list[str],
) -> str:
    roe_s = _fmt_pct(roe)
    prod_s = _fmt_pct(product)
    chain = " × ".join(f"{c.abbreviation} ({c.formatted})" for c in components)
    parts = [
        f"DuPont {model} decomposition: ROE ≈ {chain}.",
        f"Direct ROE is {roe_s}; product of factors is {prod_s}.",
    ]
    if drivers:
        parts.append(drivers[0])
    return " ".join(parts)
