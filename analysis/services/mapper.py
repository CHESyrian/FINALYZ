"""
Column mapping and normalization.

Maps user-selected Excel columns → FinancialStatement fields.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .models import FinancialStatement

# Canonical field → list of common header aliases (lowercase)
COLUMN_ALIASES: dict[str, list[str]] = {
    "revenue": [
        "revenue", "total revenue", "net sales", "sales", "turnover",
        "net revenue", "total sales", "operating revenue",
    ],
    "cogs": [
        "cogs", "cost of goods sold", "cost of sales", "cost of revenue",
        "cost of products sold", "cost of services",
    ],
    "gross_profit": [
        "gross profit", "gross income", "gross margin",
    ],
    "operating_income": [
        "operating income", "operating profit", "ebit", "operating earnings",
        "income from operations",
    ],
    "interest_expense": [
        "interest expense", "interest cost", "finance costs", "interest paid",
    ],
    "net_income": [
        "net income", "net profit", "net earnings", "profit after tax",
        "pat", "net income (loss)", "profit for the period",
    ],
    "current_assets": [
        "current assets", "total current assets",
    ],
    "cash": [
        "cash", "cash and bank", "cash at bank",
    ],
    "cash_equivalents": [
        "cash equivalents", "cash and cash equivalents", "cash & equivalents",
        "cash and short-term investments",
    ],
    "inventory": [
        "inventory", "inventories", "stock",
    ],
    "prepaid_expenses": [
        "prepaid expenses", "prepayments", "prepaid",
    ],
    "receivables": [
        "receivables", "accounts receivable", "trade receivables",
        "accounts receivable, net", "trade debtors", "ar",
    ],
    "total_assets": [
        "total assets", "assets",
    ],
    "current_liabilities": [
        "current liabilities", "total current liabilities",
    ],
    "accounts_payable": [
        "accounts payable", "trade payables", "trade payable",
        "payables", "accounts payable, trade", "ap", "creditors",
    ],
    "total_liabilities": [
        "total liabilities", "liabilities",
    ],
    "total_debt": [
        "total debt", "debt", "interest bearing debt", "borrowings",
        "total borrowings", "long-term debt",
    ],
    "equity": [
        "equity", "shareholders equity", "shareholders' equity",
        "stockholders equity", "total equity", "owners equity",
        "net assets", "total shareholders' equity",
    ],
    "operating_cash_flow": [
        "operating cash flow", "cash from operations", "cash from operating activities",
        "net cash from operating activities", "cfo", "ocf", "cash flow from operations",
    ],
    "capital_expenditures": [
        "capital expenditures", "capex", "capital expenditure",
        "purchases of property plant and equipment", "ppe purchases",
        "additions to property plant and equipment",
    ],
    "free_cash_flow": [
        "free cash flow", "fcf",
    ],
    "investing_cash_flow": [
        "investing cash flow", "cash from investing", "cash from investing activities",
        "net cash from investing activities",
    ],
    "financing_cash_flow": [
        "financing cash flow", "cash from financing", "cash from financing activities",
        "net cash from financing activities",
    ],
    "average_total_assets": [
        "average total assets", "avg total assets", "average assets",
        "mean total assets", "average of total assets",
    ],
    "average_equity": [
        "average equity", "avg equity", "average shareholders equity",
        "average stockholders equity", "mean equity",
    ],
}

# Fields we can map (order for UI) — flat list for backward compatibility
MAPPABLE_FIELDS: list[tuple[str, str]] = [
    ("revenue", "Revenue (Net Sales) *"),
    ("cogs", "COGS"),
    ("gross_profit", "Gross Profit"),
    ("operating_income", "Operating Income / EBIT"),
    ("interest_expense", "Interest Expense"),
    ("net_income", "Net Income"),
    ("current_assets", "Current Assets"),
    ("cash", "Cash"),
    ("cash_equivalents", "Cash Equivalents"),
    ("inventory", "Inventory"),
    ("prepaid_expenses", "Prepaid Expenses"),
    ("receivables", "Accounts Receivable"),
    ("total_assets", "Total Assets"),
    ("current_liabilities", "Current Liabilities"),
    ("accounts_payable", "Accounts Payable"),
    ("total_liabilities", "Total Liabilities"),
    ("total_debt", "Total Debt"),
    ("equity", "Shareholders' Equity"),
    ("operating_cash_flow", "Operating Cash Flow (OCF)"),
    ("capital_expenditures", "Capital Expenditures (CapEx)"),
    ("free_cash_flow", "Free Cash Flow"),
    ("investing_cash_flow", "Investing Cash Flow"),
    ("financing_cash_flow", "Financing Cash Flow"),
    ("average_total_assets", "Average Total Assets"),
    ("average_equity", "Average Equity"),
]

# Grouped for Excel mapping UI (statement-aware)
MAPPABLE_FIELD_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "Income Statement",
        [
            ("revenue", "Revenue (Net Sales) *"),
            ("cogs", "COGS"),
            ("gross_profit", "Gross Profit"),
            ("operating_income", "Operating Income / EBIT"),
            ("interest_expense", "Interest Expense"),
            ("net_income", "Net Income"),
        ],
    ),
    (
        "Balance Sheet – Assets",
        [
            ("current_assets", "Current Assets"),
            ("cash", "Cash"),
            ("cash_equivalents", "Cash Equivalents"),
            ("inventory", "Inventory"),
            ("prepaid_expenses", "Prepaid Expenses"),
            ("receivables", "Accounts Receivable"),
            ("total_assets", "Total Assets"),
        ],
    ),
    (
        "Balance Sheet – Liabilities & Equity",
        [
            ("current_liabilities", "Current Liabilities"),
            ("accounts_payable", "Accounts Payable"),
            ("total_liabilities", "Total Liabilities"),
            ("total_debt", "Total Debt"),
            ("equity", "Shareholders' Equity"),
        ],
    ),
    (
        "Cash Flow Statement",
        [
            ("operating_cash_flow", "Operating Cash Flow (OCF)"),
            ("capital_expenditures", "Capital Expenditures (CapEx)"),
            ("free_cash_flow", "Free Cash Flow"),
            ("investing_cash_flow", "Investing Cash Flow"),
            ("financing_cash_flow", "Financing Cash Flow"),
        ],
    ),
    (
        "Averages (optional)",
        [
            ("average_total_assets", "Average Total Assets"),
            ("average_equity", "Average Equity"),
        ],
    ),
]


def auto_map_headers(headers: list[str]) -> dict[str, str]:
    """
    Try to automatically map Excel headers to canonical fields.

    Returns dict: canonical_field → original_header
    """
    mapping: dict[str, str] = {}
    used_headers: set[str] = set()

    normalized = {h: h.strip().lower() for h in headers}

    for field, aliases in COLUMN_ALIASES.items():
        for header, lower in normalized.items():
            if header in used_headers:
                continue
            if lower in aliases or any(alias in lower for alias in aliases):
                mapping[field] = header
                used_headers.add(header)
                break

    return mapping


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    s = str(value).strip()
    if not s or s in ("-", "—", "n/a", "N/A", "NA"):
        return None
    # Remove common formatting
    s = s.replace(",", "").replace(" ", "").replace("%", "")
    # Handle parentheses for negatives: (123) → -123
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def apply_mapping(
    headers: list[str],
    rows: list[list[Any]],
    mapping: dict[str, str],
    *,
    company_name: str | None = None,
    period: str | None = None,
    row_index: int = 0,
) -> FinancialStatement:
    """
    Apply column mapping to a specific data row and build FinancialStatement.

    Parameters
    ----------
    headers : list of column headers
    rows : data rows
    mapping : canonical_field → header_name
    row_index : which data row to use (default first)
    """
    if not rows:
        raise ValueError("No data rows found in the Excel file.")

    if row_index >= len(rows):
        row_index = 0

    header_index = {h: i for i, h in enumerate(headers)}
    row = rows[row_index]

    values: dict[str, Decimal | None] = {}
    for field, header in mapping.items():
        if not header or header not in header_index:
            values[field] = None
            continue
        idx = header_index[header]
        values[field] = _to_decimal(row[idx] if idx < len(row) else None)

    revenue = values.get("revenue")
    if revenue is None or revenue <= 0:
        raise ValueError(
            "Revenue is required and must be > 0. "
            "Please map a column to Revenue and ensure the value is positive."
        )

    return FinancialStatement(
        revenue=revenue,
        cogs=values.get("cogs"),
        gross_profit=values.get("gross_profit"),
        operating_income=values.get("operating_income"),
        interest_expense=values.get("interest_expense"),
        net_income=values.get("net_income"),
        current_assets=values.get("current_assets"),
        cash=values.get("cash"),
        cash_equivalents=values.get("cash_equivalents"),
        inventory=values.get("inventory"),
        prepaid_expenses=values.get("prepaid_expenses"),
        receivables=values.get("receivables"),
        total_assets=values.get("total_assets"),
        current_liabilities=values.get("current_liabilities"),
        accounts_payable=values.get("accounts_payable"),
        total_liabilities=values.get("total_liabilities"),
        total_debt=values.get("total_debt"),
        equity=values.get("equity"),
        average_total_assets=values.get("average_total_assets"),
        average_equity=values.get("average_equity"),
        operating_cash_flow=values.get("operating_cash_flow"),
        capital_expenditures=values.get("capital_expenditures"),
        free_cash_flow=values.get("free_cash_flow"),
        investing_cash_flow=values.get("investing_cash_flow"),
        financing_cash_flow=values.get("financing_cash_flow"),
        company_name=company_name,
        period=period,
    )
