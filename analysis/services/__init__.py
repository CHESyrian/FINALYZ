"""
Analysis domain services (pure Python).

Public API:
    from analysis.services import FinancialStatement, analyze, calculate_all_ratios
"""

from .models import AnalysisResult, FinancialStatement, RatioResult
from .ratios import calculate_all_ratios
from .analyzer import analyze
from .excel_parser import parse_excel, ParsedExcel
from .mapper import (
    auto_map_headers,
    apply_mapping,
    MAPPABLE_FIELDS,
    MAPPABLE_FIELD_GROUPS,
    COLUMN_ALIASES,
)
from .sample_data import get_sample_statement, get_sample_form_initial

__all__ = [
    "FinancialStatement",
    "RatioResult",
    "AnalysisResult",
    "calculate_all_ratios",
    "analyze",
    "parse_excel",
    "ParsedExcel",
    "auto_map_headers",
    "apply_mapping",
    "MAPPABLE_FIELDS",
    "MAPPABLE_FIELD_GROUPS",
    "COLUMN_ALIASES",
    "get_sample_statement",
    "get_sample_form_initial",
]
