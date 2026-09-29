"""
Financial ratio calculations.

Core ratios (liquidity, profitability, solvency, efficiency) plus working-capital
days (DSO/DIO/DPO), Cash Conversion Cycle, ROIC, and cash-flow ratios when
cash-flow statement fields are present.

Pure functions, Decimal only, no Django.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .models import FinancialStatement, RatioResult

ZERO = Decimal("0")
HUNDRED = Decimal("100")


def _safe_div(num: Decimal | None, den: Decimal | None) -> Decimal | None:
    if num is None or den is None or den == ZERO:
        return None
    return num / den


def _pct(value: Decimal | None) -> str:
    if value is None:
        return "N/A"
    return f"{(value * HUNDRED).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}%"


def _num(value: Decimal | None, places: str = "0.01") -> str:
    if value is None:
        return "N/A"
    return str(value.quantize(Decimal(places), rounding=ROUND_HALF_UP))


def _status_higher_better(value: Decimal | None, good: Decimal, warning: Decimal) -> str:
    if value is None:
        return "n/a"
    if value >= good:
        return "good"
    if value >= warning:
        return "warning"
    return "bad"


def _status_lower_better(value: Decimal | None, good: Decimal, warning: Decimal) -> str:
    if value is None:
        return "n/a"
    if value <= good:
        return "good"
    if value <= warning:
        return "warning"
    return "bad"


# ===========================================================================
# 1. LIQUIDITY
# ===========================================================================

def current_ratio(stmt: FinancialStatement) -> RatioResult:
    """CR = Current Assets / Current Liabilities"""
    value = _safe_div(stmt.current_assets, stmt.current_liabilities)
    status = _status_higher_better(value, Decimal("1.5"), Decimal("1.0"))
    texts = {
        "good": "Strong short-term liquidity.",
        "warning": "Acceptable but tight liquidity.",
        "bad": "Potential liquidity risk.",
        "n/a": "Need Current Assets and Current Liabilities.",
    }
    return RatioResult(
        name="Current Ratio",
        abbreviation="CR",
        value=value,
        formatted=_num(value),
        unit="x",
        status=status,
        interpretation=texts[status],
        category="liquidity",
        formula="Current Assets / Current Liabilities",
    )


def quick_ratio(stmt: FinancialStatement) -> RatioResult:
    """QR = (Current Assets - Inventory - Prepaid Expenses) / Current Liabilities"""
    if stmt.current_assets is None:
        value = None
    else:
        inv = stmt.inventory or ZERO
        prepaid = stmt.prepaid_expenses or ZERO
        value = _safe_div(stmt.current_assets - inv - prepaid, stmt.current_liabilities)
    status = _status_higher_better(value, Decimal("1.0"), Decimal("0.7"))
    texts = {
        "good": "Healthy quick liquidity without relying on inventory.",
        "warning": "Marginal quick ratio.",
        "bad": "Weak acid-test ratio.",
        "n/a": "Need Current Assets and Current Liabilities.",
    }
    return RatioResult(
        name="Quick Ratio",
        abbreviation="QR",
        value=value,
        formatted=_num(value),
        unit="x",
        status=status,
        interpretation=texts[status],
        category="liquidity",
        formula="(Current Assets − Inventory − Prepaid Expenses) / Current Liabilities",
    )


def cash_ratio(stmt: FinancialStatement) -> RatioResult:
    """CaR = (Cash + Cash Equivalents) / Current Liabilities"""
    value = _safe_div(stmt.get_cash_and_equivalents(), stmt.current_liabilities)
    status = _status_higher_better(value, Decimal("0.5"), Decimal("0.2"))
    texts = {
        "good": "Strong cash coverage of short-term liabilities.",
        "warning": "Moderate cash buffer.",
        "bad": "Low cash ratio – limited immediate liquidity.",
        "n/a": "Need Cash/Cash Equivalents and Current Liabilities.",
    }
    return RatioResult(
        name="Cash Ratio",
        abbreviation="CaR",
        value=value,
        formatted=_num(value),
        unit="x",
        status=status,
        interpretation=texts[status],
        category="liquidity",
        formula="(Cash + Cash Equivalents) / Current Liabilities",
    )


# ===========================================================================
# 2. PROFITABILITY
# ===========================================================================

def gross_margin(stmt: FinancialStatement) -> RatioResult:
    """GPM = Gross Profit / Revenue × 100"""
    value = _safe_div(stmt.gross_profit, stmt.revenue)
    status = _status_higher_better(value, Decimal("0.40"), Decimal("0.20"))
    texts = {
        "good": "Strong gross profitability.",
        "warning": "Moderate gross margin.",
        "bad": "Low gross margin.",
        "n/a": "Need Revenue and Gross Profit (or COGS).",
    }
    return RatioResult(
        name="Gross Margin",
        abbreviation="GPM",
        value=value,
        formatted=_pct(value),
        unit="%",
        status=status,
        interpretation=texts[status],
        category="profitability",
        formula="Gross Profit / Revenue × 100",
    )


def operating_margin(stmt: FinancialStatement) -> RatioResult:
    """OPM = Operating Income / Revenue × 100"""
    value = _safe_div(stmt.operating_income, stmt.revenue)
    status = _status_higher_better(value, Decimal("0.15"), Decimal("0.05"))
    texts = {
        "good": "Strong operating efficiency.",
        "warning": "Moderate operating margin.",
        "bad": "Weak operating profitability.",
        "n/a": "Need Operating Income and Revenue.",
    }
    return RatioResult(
        name="Operating Margin",
        abbreviation="OPM",
        value=value,
        formatted=_pct(value),
        unit="%",
        status=status,
        interpretation=texts[status],
        category="profitability",
        formula="Operating Income / Revenue × 100",
    )


def net_margin(stmt: FinancialStatement) -> RatioResult:
    """NPM = Net Income / Revenue × 100"""
    value = _safe_div(stmt.net_income, stmt.revenue)
    status = _status_higher_better(value, Decimal("0.10"), Decimal("0.03"))
    texts = {
        "good": "Healthy bottom-line profitability.",
        "warning": "Thin net margin.",
        "bad": "Very low or negative profitability.",
        "n/a": "Need Net Income and Revenue.",
    }
    return RatioResult(
        name="Net Margin",
        abbreviation="NPM",
        value=value,
        formatted=_pct(value),
        unit="%",
        status=status,
        interpretation=texts[status],
        category="profitability",
        formula="Net Income / Revenue × 100",
    )


def return_on_assets(stmt: FinancialStatement) -> RatioResult:
    """ROA = Net Income / Average Total Assets × 100"""
    value = _safe_div(stmt.net_income, stmt.get_average_assets())
    status = _status_higher_better(value, Decimal("0.08"), Decimal("0.03"))
    texts = {
        "good": "Efficient use of assets.",
        "warning": "Moderate asset efficiency.",
        "bad": "Low return on assets.",
        "n/a": "Need Net Income and (Average) Total Assets.",
    }
    return RatioResult(
        name="Return on Assets",
        abbreviation="ROA",
        value=value,
        formatted=_pct(value),
        unit="%",
        status=status,
        interpretation=texts[status],
        category="profitability",
        formula="Net Income / Average Total Assets × 100",
    )


def return_on_equity(stmt: FinancialStatement) -> RatioResult:
    """ROE = Net Income / Average Shareholders' Equity × 100"""
    value = _safe_div(stmt.net_income, stmt.get_average_equity())
    status = _status_higher_better(value, Decimal("0.15"), Decimal("0.08"))
    texts = {
        "good": "Strong return for shareholders.",
        "warning": "Acceptable but average ROE.",
        "bad": "Low return on equity.",
        "n/a": "Need Net Income and (Average) Equity.",
    }
    return RatioResult(
        name="Return on Equity",
        abbreviation="ROE",
        value=value,
        formatted=_pct(value),
        unit="%",
        status=status,
        interpretation=texts[status],
        category="profitability",
        formula="Net Income / Average Shareholders' Equity × 100",
    )


# ===========================================================================
# 3. SOLVENCY
# ===========================================================================

def debt_ratio(stmt: FinancialStatement) -> RatioResult:
    """DR = Total Debt / Total Assets × 100"""
    value = _safe_div(stmt.get_total_debt(), stmt.total_assets)
    status = _status_lower_better(value, Decimal("0.40"), Decimal("0.60"))
    texts = {
        "good": "Assets mostly equity-financed. Low risk.",
        "warning": "Balanced financing structure.",
        "bad": "High proportion of debt financing.",
        "n/a": "Need Total Debt (or Total Liabilities) and Total Assets.",
    }
    return RatioResult(
        name="Debt Ratio",
        abbreviation="DR",
        value=value,
        formatted=_pct(value),
        unit="%",
        status=status,
        interpretation=texts[status],
        category="solvency",
        formula="Total Debt / Total Assets × 100",
    )


def debt_to_equity(stmt: FinancialStatement) -> RatioResult:
    """D/E = Total Debt / Shareholders' Equity"""
    value = _safe_div(stmt.get_total_debt(), stmt.equity)
    status = _status_lower_better(value, Decimal("1.0"), Decimal("2.0"))
    texts = {
        "good": "Conservative leverage.",
        "warning": "Moderate leverage.",
        "bad": "High leverage – elevated financial risk.",
        "n/a": "Need Total Debt (or Total Liabilities) and Equity.",
    }
    return RatioResult(
        name="Debt-to-Equity",
        abbreviation="D/E",
        value=value,
        formatted=_num(value),
        unit="x",
        status=status,
        interpretation=texts[status],
        category="solvency",
        formula="Total Debt / Shareholders' Equity",
    )


def equity_ratio(stmt: FinancialStatement) -> RatioResult:
    """ER = Shareholders' Equity / Total Assets × 100"""
    value = _safe_div(stmt.equity, stmt.total_assets)
    status = _status_higher_better(value, Decimal("0.50"), Decimal("0.30"))
    texts = {
        "good": "Strong equity base.",
        "warning": "Moderate equity cushion.",
        "bad": "Thin equity buffer.",
        "n/a": "Need Equity and Total Assets.",
    }
    return RatioResult(
        name="Equity Ratio",
        abbreviation="ER",
        value=value,
        formatted=_pct(value),
        unit="%",
        status=status,
        interpretation=texts[status],
        category="solvency",
        formula="Shareholders' Equity / Total Assets × 100",
    )


def equity_multiplier(stmt: FinancialStatement) -> RatioResult:
    """EM = Average Total Assets / Average Shareholders' Equity (DuPont leverage factor)"""
    value = _safe_div(stmt.get_average_assets(), stmt.get_average_equity())
    # Moderate leverage is often fine; very high multiplies risk
    status = _status_lower_better(value, Decimal("2.0"), Decimal("3.0"))
    texts = {
        "good": "Conservative financial leverage (DuPont equity multiplier).",
        "warning": "Moderate leverage — ROE is amplified by debt.",
        "bad": "High equity multiplier — elevated financial risk.",
        "n/a": "Need (Average) Total Assets and (Average) Equity.",
    }
    return RatioResult(
        name="Equity Multiplier",
        abbreviation="EM",
        value=value,
        formatted=_num(value),
        unit="x",
        status=status,
        interpretation=texts[status],
        category="solvency",
        formula="Average Total Assets / Average Shareholders' Equity",
        source_statement="balance_sheet",
    )


def interest_coverage(stmt: FinancialStatement) -> RatioResult:
    """ICR = EBIT / Interest Expense"""
    value = _safe_div(stmt.get_ebit(), stmt.interest_expense)
    status = _status_higher_better(value, Decimal("3.0"), Decimal("1.5"))
    texts = {
        "good": "Comfortable ability to cover interest.",
        "warning": "Adequate but limited interest coverage.",
        "bad": "Weak interest coverage – debt service risk.",
        "n/a": "Need EBIT (or Operating Income) and Interest Expense.",
    }
    return RatioResult(
        name="Interest Coverage Ratio",
        abbreviation="ICR",
        value=value,
        formatted=_num(value),
        unit="x",
        status=status,
        interpretation=texts[status],
        category="solvency",
        formula="EBIT / Interest Expense",
    )


# ===========================================================================
# 4. EFFICIENCY
# ===========================================================================

def asset_turnover(stmt: FinancialStatement) -> RatioResult:
    """ATO = Revenue / Average Total Assets"""
    value = _safe_div(stmt.revenue, stmt.get_average_assets())
    status = _status_higher_better(value, Decimal("1.0"), Decimal("0.5"))
    texts = {
        "good": "Efficient asset utilization.",
        "warning": "Moderate asset turnover.",
        "bad": "Low asset turnover.",
        "n/a": "Need Revenue and (Average) Total Assets.",
    }
    return RatioResult(
        name="Asset Turnover",
        abbreviation="ATO",
        value=value,
        formatted=_num(value),
        unit="x",
        status=status,
        interpretation=texts[status],
        category="efficiency",
        formula="Revenue / Average Total Assets",
    )


def receivables_turnover(stmt: FinancialStatement) -> RatioResult:
    """RT = Net Credit Sales / Average Accounts Receivable"""
    value = _safe_div(stmt.get_net_credit_sales(), stmt.get_average_receivables())
    status = _status_higher_better(value, Decimal("8.0"), Decimal("4.0"))
    texts = {
        "good": "Efficient collection of receivables.",
        "warning": "Average collection efficiency.",
        "bad": "Slow collection of receivables.",
        "n/a": "Need Net Credit Sales (or Revenue) and (Average) Receivables.",
    }
    return RatioResult(
        name="Receivables Turnover",
        abbreviation="RT",
        value=value,
        formatted=_num(value),
        unit="x",
        status=status,
        interpretation=texts[status],
        category="efficiency",
        formula="Net Credit Sales / Average Accounts Receivable",
    )


def inventory_turnover(stmt: FinancialStatement) -> RatioResult:
    """ITR = COGS / Average Inventory"""
    value = _safe_div(stmt.cogs, stmt.get_average_inventory())
    status = _status_higher_better(value, Decimal("6.0"), Decimal("3.0"))
    texts = {
        "good": "Efficient inventory management.",
        "warning": "Moderate inventory turnover.",
        "bad": "Slow-moving inventory.",
        "n/a": "Need COGS and (Average) Inventory.",
    }
    return RatioResult(
        name="Inventory Turnover",
        abbreviation="ITR",
        value=value,
        formatted=_num(value),
        unit="x",
        status=status,
        interpretation=texts[status],
        category="efficiency",
        formula="COGS / Average Inventory",
        source_statement="mixed",
    )


def days_sales_outstanding(stmt: FinancialStatement) -> RatioResult:
    """DSO = 365 × Average Receivables / Net Credit Sales"""
    sales = stmt.get_net_credit_sales()
    ar = stmt.get_average_receivables()
    value = (
        _safe_div(Decimal("365") * ar, sales)
        if ar is not None and sales is not None
        else None
    )
    status = _status_lower_better(value, Decimal("45"), Decimal("60"))
    texts = {
        "good": "Customers pay promptly — efficient collections.",
        "warning": "Collection period is moderate; monitor receivables.",
        "bad": "Slow collections — cash tied up in receivables.",
        "n/a": "Need (Average) Receivables and Net Credit Sales (or Revenue).",
    }
    return RatioResult(
        name="Days Sales Outstanding",
        abbreviation="DSO",
        value=value,
        formatted=_num(value, "0.1"),
        unit="days",
        status=status,
        interpretation=texts[status],
        category="efficiency",
        formula="365 × Average Receivables / Net Credit Sales",
        source_statement="mixed",
    )


def days_inventory_outstanding(stmt: FinancialStatement) -> RatioResult:
    """DIO = 365 × Average Inventory / COGS"""
    inv = stmt.get_average_inventory()
    value = _safe_div(Decimal("365") * inv, stmt.cogs) if inv is not None else None
    status = _status_lower_better(value, Decimal("60"), Decimal("90"))
    texts = {
        "good": "Inventory turns quickly — low holding days.",
        "warning": "Moderate inventory days; room to tighten stock.",
        "bad": "Inventory sits too long — risk of obsolescence or excess capital.",
        "n/a": "Need (Average) Inventory and COGS.",
    }
    return RatioResult(
        name="Days Inventory Outstanding",
        abbreviation="DIO",
        value=value,
        formatted=_num(value, "0.1"),
        unit="days",
        status=status,
        interpretation=texts[status],
        category="efficiency",
        formula="365 × Average Inventory / COGS",
        source_statement="mixed",
    )


def days_payable_outstanding(stmt: FinancialStatement) -> RatioResult:
    """DPO = 365 × Average Accounts Payable / COGS"""
    ap = stmt.get_average_payables()
    value = _safe_div(Decimal("365") * ap, stmt.cogs) if ap is not None else None
    # Higher DPO is generally better (supplier financing), within reason
    status = _status_higher_better(value, Decimal("30"), Decimal("20"))
    texts = {
        "good": "Favourable payment terms — good use of supplier credit.",
        "warning": "Moderate payable days; limited supplier financing.",
        "bad": "Paying suppliers very quickly — little working-capital benefit.",
        "n/a": "Need (Average) Accounts Payable and COGS.",
    }
    return RatioResult(
        name="Days Payable Outstanding",
        abbreviation="DPO",
        value=value,
        formatted=_num(value, "0.1"),
        unit="days",
        status=status,
        interpretation=texts[status],
        category="efficiency",
        formula="365 × Average Accounts Payable / COGS",
        source_statement="mixed",
    )


def cash_conversion_cycle(stmt: FinancialStatement) -> RatioResult:
    """CCC = DSO + DIO − DPO"""
    dso_r = days_sales_outstanding(stmt)
    dio_r = days_inventory_outstanding(stmt)
    dpo_r = days_payable_outstanding(stmt)
    if dso_r.value is None or dio_r.value is None or dpo_r.value is None:
        value = None
    else:
        value = dso_r.value + dio_r.value - dpo_r.value
    status = _status_lower_better(value, Decimal("60"), Decimal("90"))
    texts = {
        "good": "Short cash conversion cycle — efficient working capital.",
        "warning": "Moderate cash conversion cycle; working capital can be tightened.",
        "bad": "Long cash conversion cycle — cash tied up in operations.",
        "n/a": "Need Receivables, Inventory, Accounts Payable, and COGS (plus sales).",
    }
    return RatioResult(
        name="Cash Conversion Cycle",
        abbreviation="CCC",
        value=value,
        formatted=_num(value, "0.1"),
        unit="days",
        status=status,
        interpretation=texts[status],
        category="efficiency",
        formula="DSO + DIO − DPO",
        source_statement="mixed",
    )


def return_on_invested_capital(stmt: FinancialStatement) -> RatioResult:
    """ROIC = EBIT / Invested Capital (Debt + Equity − Cash)"""
    ebit = stmt.get_ebit()
    invested = stmt.get_invested_capital()
    value = _safe_div(ebit, invested)
    status = _status_higher_better(value, Decimal("0.10"), Decimal("0.05"))
    texts = {
        "good": "Strong return on capital employed in the business.",
        "warning": "Moderate return on invested capital.",
        "bad": "Low return on invested capital — capital may be under-earning.",
        "n/a": "Need EBIT (or Operating Income) and Debt + Equity (cash optional).",
    }
    return RatioResult(
        name="Return on Invested Capital",
        abbreviation="ROIC",
        value=value,
        formatted=_pct(value),
        unit="%",
        status=status,
        interpretation=texts[status],
        category="profitability",
        formula="EBIT / (Total Debt + Equity − Cash & Equivalents)",
        source_statement="mixed",
    )


# ===========================================================================
# 5. CASH FLOW (requires cash-flow statement fields)
# ===========================================================================

def operating_cash_flow_ratio(stmt: FinancialStatement) -> RatioResult:
    """OCFR = Operating Cash Flow / Current Liabilities"""
    value = _safe_div(stmt.operating_cash_flow, stmt.current_liabilities)
    status = _status_higher_better(value, Decimal("0.40"), Decimal("0.20"))
    texts = {
        "good": "Strong operating cash coverage of short-term obligations.",
        "warning": "Modest cash coverage of current liabilities.",
        "bad": "Operating cash flow may not adequately cover short-term debts.",
        "n/a": "Need Operating Cash Flow and Current Liabilities.",
    }
    return RatioResult(
        name="Operating Cash Flow Ratio",
        abbreviation="OCFR",
        value=value,
        formatted=_num(value),
        unit="x",
        status=status,
        interpretation=texts[status],
        category="cash_flow",
        formula="Operating Cash Flow / Current Liabilities",
        source_statement="cash_flow",
    )


def cash_flow_margin(stmt: FinancialStatement) -> RatioResult:
    """CFM = Operating Cash Flow / Revenue"""
    value = _safe_div(stmt.operating_cash_flow, stmt.revenue)
    status = _status_higher_better(value, Decimal("0.10"), Decimal("0.05"))
    texts = {
        "good": "Healthy conversion of revenue into operating cash.",
        "warning": "Moderate cash generation relative to sales.",
        "bad": "Weak operating cash relative to revenue.",
        "n/a": "Need Operating Cash Flow and Revenue.",
    }
    return RatioResult(
        name="Cash Flow Margin",
        abbreviation="CFM",
        value=value,
        formatted=_pct(value),
        unit="%",
        status=status,
        interpretation=texts[status],
        category="cash_flow",
        formula="Operating Cash Flow / Revenue × 100",
        source_statement="cash_flow",
    )


def free_cash_flow_margin(stmt: FinancialStatement) -> RatioResult:
    """FCFM = Free Cash Flow / Revenue"""
    fcf = stmt.get_free_cash_flow()
    value = _safe_div(fcf, stmt.revenue)
    status = _status_higher_better(value, Decimal("0.05"), Decimal("0.00"))
    texts = {
        "good": "Positive free cash flow margin — cash left after reinvestment.",
        "warning": "Thin or break-even free cash flow relative to sales.",
        "bad": "Negative or very low free cash flow margin.",
        "n/a": "Need Free Cash Flow (or OCF + CapEx) and Revenue.",
    }
    return RatioResult(
        name="Free Cash Flow Margin",
        abbreviation="FCFM",
        value=value,
        formatted=_pct(value),
        unit="%",
        status=status,
        interpretation=texts[status],
        category="cash_flow",
        formula="Free Cash Flow / Revenue × 100",
        source_statement="cash_flow",
    )


def cash_conversion_ratio(stmt: FinancialStatement) -> RatioResult:
    """CCR = Operating Cash Flow / Net Income (quality of earnings)"""
    value = _safe_div(stmt.operating_cash_flow, stmt.net_income)
    # Higher is generally better (cash backs reported profit); >1 is strong
    status = _status_higher_better(value, Decimal("1.00"), Decimal("0.80"))
    texts = {
        "good": "Earnings are well supported by operating cash flow.",
        "warning": "Cash conversion of earnings is moderate.",
        "bad": "Reported profit is not fully backed by operating cash.",
        "n/a": "Need Operating Cash Flow and Net Income.",
    }
    return RatioResult(
        name="Cash Conversion Ratio",
        abbreviation="CCR",
        value=value,
        formatted=_num(value),
        unit="x",
        status=status,
        interpretation=texts[status],
        category="cash_flow",
        formula="Operating Cash Flow / Net Income",
        source_statement="cash_flow",
    )


# ===========================================================================
# Public API
# ===========================================================================

ALL_RATIO_FUNCTIONS = [
    # Liquidity (balance sheet)
    current_ratio,
    quick_ratio,
    cash_ratio,
    # Profitability (income statement + mixed)
    gross_margin,
    operating_margin,
    net_margin,
    return_on_assets,
    return_on_equity,
    return_on_invested_capital,
    # Solvency (balance sheet + mixed) — EM is the DuPont leverage factor
    debt_ratio,
    debt_to_equity,
    equity_ratio,
    equity_multiplier,
    interest_coverage,
    # Efficiency (mixed) — includes working-capital days & CCC
    asset_turnover,
    receivables_turnover,
    inventory_turnover,
    days_sales_outstanding,
    days_inventory_outstanding,
    days_payable_outstanding,
    cash_conversion_cycle,
    # Cash flow (cash flow statement + mixed)
    operating_cash_flow_ratio,
    cash_flow_margin,
    free_cash_flow_margin,
    cash_conversion_ratio,
]


def calculate_all_ratios(stmt: FinancialStatement) -> list[RatioResult]:
    """Calculate all supported ratios (core + working-capital days + ROIC + cash-flow)."""
    return [fn(stmt) for fn in ALL_RATIO_FUNCTIONS]
