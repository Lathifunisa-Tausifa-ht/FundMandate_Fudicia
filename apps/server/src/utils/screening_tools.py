# screening_tools.py
import asyncio
import io
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.tools import StructuredTool

from database.models import Company, Sourcing

# ============================================================================
# LOGGING SETUP - COMPREHENSIVE TRACKING
# ============================================================================
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Create loggers for different components
screening_logger = logging.getLogger("screening")
parameter_logger = logging.getLogger("parameter_screening")
company_logger = logging.getLogger("company_details")

# File handlers with timestamps
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
screening_handler = logging.FileHandler(LOG_DIR / f"screening_{timestamp}.log")
parameter_handler = logging.FileHandler(LOG_DIR / f"parameter_screening_{timestamp}.log")
company_handler = logging.FileHandler(LOG_DIR / f"company_details_{timestamp}.log")

# Format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
screening_handler.setFormatter(formatter)
parameter_handler.setFormatter(formatter)
company_handler.setFormatter(formatter)

screening_logger.addHandler(screening_handler)
screening_logger.setLevel(logging.DEBUG)
parameter_logger.addHandler(parameter_handler)
parameter_logger.setLevel(logging.DEBUG)
company_logger.addHandler(company_handler)
company_logger.setLevel(logging.DEBUG)

# Also add console handlers for visibility using UTF-8 safe output
console_formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
try:
    console_stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    console_handler = logging.StreamHandler(console_stream)
except Exception:
    console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)
screening_logger.addHandler(console_handler)
parameter_logger.addHandler(console_handler)


# ============================================================================
# PER-PARAMETER SCREENING FUNCTIONS
# ============================================================================
def screen_parameter_revenue(company: dict, constraint_str: str) -> dict:
    """
    Screen a company against REVENUE constraint.
    
    Returns:
        {
            "param": "revenue",
            "status": "pass" | "fail" | "null",
            "company_value": float | None,
            "threshold": float,
            "operator": str,
            "reason": str
        }
    """
    try:
        operator, threshold = parse_constraint(constraint_str)
        company_value = get_company_value(company, "revenue")
        
        result = {
            "param": "revenue",
            "constraint": constraint_str,
            "company_value": company_value,
            "threshold": threshold,
            "operator": operator,
        }
        
        if company_value is None:
            result["status"] = "null"
            result["reason"] = f"Revenue data not available"
        elif compare_values(company_value, operator, threshold):
            result["status"] = "pass"
            result["reason"] = f"Revenue {company_value:.2f}M {operator} {threshold:.2f}M [PASS]"
        else:
            result["status"] = "fail"
            result["reason"] = f"Revenue {company_value:.2f}M does NOT {operator} {threshold:.2f}M [FAIL]"
        
        parameter_logger.debug(f"Revenue screening: company_id={company.get('company_id')} | {result}")
        return result
    except Exception as e:
        parameter_logger.error(f"Error screening revenue: {e}", exc_info=True)
        return {
            "param": "revenue",
            "status": "error",
            "reason": str(e),
            "company_value": None,
            "threshold": 0,
            "operator": ""
        }


def screen_parameter_ebitda(company: dict, constraint_str: str) -> dict:
    """Screen a company against EBITDA constraint."""
    try:
        operator, threshold = parse_constraint(constraint_str)
        company_value = get_company_value(company, "ebitda")
        
        result = {
            "param": "ebitda",
            "constraint": constraint_str,
            "company_value": company_value,
            "threshold": threshold,
            "operator": operator,
        }
        
        if company_value is None:
            result["status"] = "null"
            result["reason"] = f"EBITDA data not available"
        elif compare_values(company_value, operator, threshold):
            result["status"] = "pass"
            result["reason"] = f"EBITDA {company_value:.2f}M {operator} {threshold:.2f}M [PASS]"
        else:
            result["status"] = "fail"
            result["reason"] = f"EBITDA {company_value:.2f}M does NOT {operator} {threshold:.2f}M [FAIL]"
        
        parameter_logger.debug(f"EBITDA screening: company_id={company.get('company_id')} | {result}")
        return result
    except Exception as e:
        parameter_logger.error(f"Error screening ebitda: {e}", exc_info=True)
        return {
            "param": "ebitda",
            "status": "error",
            "reason": str(e),
            "company_value": None,
            "threshold": 0,
            "operator": ""
        }


def screen_parameter_net_income(company: dict, constraint_str: str) -> dict:
    """Screen a company against NET_INCOME constraint."""
    try:
        operator, threshold = parse_constraint(constraint_str)
        company_value = get_company_value(company, "net_income")
        
        result = {
            "param": "net_income",
            "constraint": constraint_str,
            "company_value": company_value,
            "threshold": threshold,
            "operator": operator,
        }
        
        if company_value is None:
            result["status"] = "null"
            result["reason"] = f"Net Income data not available"
        elif compare_values(company_value, operator, threshold):
            result["status"] = "pass"
            result["reason"] = f"Net Income {company_value:.2f}M {operator} {threshold:.2f}M [PASS]"
        else:
            result["status"] = "fail"
            result["reason"] = f"Net Income {company_value:.2f}M does NOT {operator} {threshold:.2f}M [FAIL]"
        
        parameter_logger.debug(f"Net Income screening: company_id={company.get('company_id')} | {result}")
        return result
    except Exception as e:
        parameter_logger.error(f"Error screening net_income: {e}", exc_info=True)
        return {
            "param": "net_income",
            "status": "error",
            "reason": str(e),
            "company_value": None,
            "threshold": 0,
            "operator": ""
        }


def screen_parameter_market_cap(company: dict, constraint_str: str) -> dict:
    """Screen a company against MARKET_CAP constraint."""
    try:
        operator, threshold = parse_constraint(constraint_str)
        company_value = get_company_value(company, "market_cap")
        
        result = {
            "param": "market_cap",
            "constraint": constraint_str,
            "company_value": company_value,
            "threshold": threshold,
            "operator": operator,
        }
        
        if company_value is None:
            result["status"] = "null"
            result["reason"] = f"Market Cap data not available"
        elif compare_values(company_value, operator, threshold):
            result["status"] = "pass"
            result["reason"] = f"Market Cap {company_value:.2f}M {operator} {threshold:.2f}M [PASS]"
        else:
            result["status"] = "fail"
            result["reason"] = f"Market Cap {company_value:.2f}M does NOT {operator} {threshold:.2f}M [FAIL]"
        
        parameter_logger.debug(f"Market Cap screening: company_id={company.get('company_id')} | {result}")
        return result
    except Exception as e:
        parameter_logger.error(f"Error screening market_cap: {e}", exc_info=True)
        return {
            "param": "market_cap",
            "status": "error",
            "reason": str(e),
            "company_value": None,
            "threshold": 0,
            "operator": ""
        }


def screen_parameter_gross_profit_margin(company: dict, constraint_str: str) -> dict:
    """Screen a company against GROSS_PROFIT_MARGIN constraint."""
    try:
        operator, threshold = parse_constraint(constraint_str)
        company_value = get_company_value(company, "gross_profit_margin")
        
        result = {
            "param": "gross_profit_margin",
            "constraint": constraint_str,
            "company_value": company_value,
            "threshold": threshold,
            "operator": operator,
        }
        
        if company_value is None:
            result["status"] = "null"
            result["reason"] = f"Gross Profit Margin data not available"
        elif compare_values(company_value, operator, threshold):
            result["status"] = "pass"
            result["reason"] = f"Gross Profit Margin {company_value*100:.2f}% {operator} {threshold*100:.2f}% [PASS]"
        else:
            result["status"] = "fail"
            result["reason"] = f"Gross Profit Margin {company_value*100:.2f}% does NOT {operator} {threshold*100:.2f}% [FAIL]"
        
        parameter_logger.debug(f"Gross Profit Margin screening: company_id={company.get('company_id')} | {result}")
        return result
    except Exception as e:
        parameter_logger.error(f"Error screening gross_profit_margin: {e}", exc_info=True)
        return {
            "param": "gross_profit_margin",
            "status": "error",
            "reason": str(e),
            "company_value": None,
            "threshold": 0,
            "operator": ""
        }


def screen_parameter_return_on_equity(company: dict, constraint_str: str) -> dict:
    """Screen a company against RETURN_ON_EQUITY constraint."""
    try:
        operator, threshold = parse_constraint(constraint_str)
        company_value = get_company_value(company, "return_on_equity")
        
        result = {
            "param": "return_on_equity",
            "constraint": constraint_str,
            "company_value": company_value,
            "threshold": threshold,
            "operator": operator,
        }
        
        if company_value is None:
            result["status"] = "null"
            result["reason"] = f"Return on Equity data not available"
        elif compare_values(company_value, operator, threshold):
            result["status"] = "pass"
            result["reason"] = f"Return on Equity {company_value*100:.2f}% {operator} {threshold*100:.2f}% [PASS]"
        else:
            result["status"] = "fail"
            result["reason"] = f"Return on Equity {company_value*100:.2f}% does NOT {operator} {threshold*100:.2f}% [FAIL]"
        
        parameter_logger.debug(f"Return on Equity screening: company_id={company.get('company_id')} | {result}")
        return result
    except Exception as e:
        parameter_logger.error(f"Error screening return_on_equity: {e}", exc_info=True)
        return {
            "param": "return_on_equity",
            "status": "error",
            "reason": str(e),
            "company_value": None,
            "threshold": 0,
            "operator": ""
        }


def screen_parameter_debt_to_equity(company: dict, constraint_str: str) -> dict:
    """Screen a company against DEBT_TO_EQUITY constraint."""
    try:
        operator, threshold = parse_constraint(constraint_str)
        company_value = get_company_value(company, "debt_to_equity")
        
        result = {
            "param": "debt_to_equity",
            "constraint": constraint_str,
            "company_value": company_value,
            "threshold": threshold,
            "operator": operator,
        }
        
        if company_value is None:
            result["status"] = "null"
            result["reason"] = f"Debt to Equity data not available"
        elif compare_values(company_value, operator, threshold):
            result["status"] = "pass"
            result["reason"] = f"Debt to Equity {company_value:.2f} {operator} {threshold:.2f} [PASS]"
        else:
            result["status"] = "fail"
            result["reason"] = f"Debt to Equity {company_value:.2f} does NOT {operator} {threshold:.2f} [FAIL]"
        
        parameter_logger.debug(f"Debt to Equity screening: company_id={company.get('company_id')} | {result}")
        return result
    except Exception as e:
        parameter_logger.error(f"Error screening debt_to_equity: {e}", exc_info=True)
        return {
            "param": "debt_to_equity",
            "status": "error",
            "reason": str(e),
            "company_value": None,
            "threshold": 0,
            "operator": ""
        }


def screen_parameter_pe_ratio(company: dict, constraint_str: str) -> dict:
    """Screen a company against PE_RATIO constraint."""
    try:
        operator, threshold = parse_constraint(constraint_str)
        company_value = get_company_value(company, "pe_ratio")
        
        result = {
            "param": "pe_ratio",
            "constraint": constraint_str,
            "company_value": company_value,
            "threshold": threshold,
            "operator": operator,
        }
        
        if company_value is None:
            result["status"] = "null"
            result["reason"] = f"P/E Ratio data not available"
        elif compare_values(company_value, operator, threshold):
            result["status"] = "pass"
            result["reason"] = f"P/E Ratio {company_value:.2f} {operator} {threshold:.2f} [PASS]"
        else:
            result["status"] = "fail"
            result["reason"] = f"P/E Ratio {company_value:.2f} does NOT {operator} {threshold:.2f} [FAIL]"
        
        parameter_logger.debug(f"P/E Ratio screening: company_id={company.get('company_id')} | {result}")
        return result
    except Exception as e:
        parameter_logger.error(f"Error screening pe_ratio: {e}", exc_info=True)
        return {
            "param": "pe_ratio",
            "status": "error",
            "reason": str(e),
            "company_value": None,
            "threshold": 0,
            "operator": ""
        }


def screen_parameter_price_to_book(company: dict, constraint_str: str) -> dict:
    """Screen a company against PRICE_TO_BOOK constraint."""
    try:
        operator, threshold = parse_constraint(constraint_str)
        company_value = get_company_value(company, "price_to_book")
        
        result = {
            "param": "price_to_book",
            "constraint": constraint_str,
            "company_value": company_value,
            "threshold": threshold,
            "operator": operator,
        }
        
        if company_value is None:
            result["status"] = "null"
            result["reason"] = f"Price to Book data not available"
        elif compare_values(company_value, operator, threshold):
            result["status"] = "pass"
            result["reason"] = f"Price to Book {company_value:.2f} {operator} {threshold:.2f} [PASS]"
        else:
            result["status"] = "fail"
            result["reason"] = f"Price to Book {company_value:.2f} does NOT {operator} {threshold:.2f} [FAIL]"
        
        parameter_logger.debug(f"Price to Book screening: company_id={company.get('company_id')} | {result}")
        return result
    except Exception as e:
        parameter_logger.error(f"Error screening price_to_book: {e}", exc_info=True)
        return {
            "param": "price_to_book",
            "status": "error",
            "reason": str(e),
            "company_value": None,
            "threshold": 0,
            "operator": ""
        }


def screen_parameter_dividend_yield(company: dict, constraint_str: str) -> dict:
    """Screen a company against DIVIDEND_YIELD constraint."""
    try:
        operator, threshold = parse_constraint(constraint_str)
        company_value = get_company_value(company, "dividend_yield")
        
        result = {
            "param": "dividend_yield",
            "constraint": constraint_str,
            "company_value": company_value,
            "threshold": threshold,
            "operator": operator,
        }
        
        if company_value is None:
            result["status"] = "null"
            result["reason"] = f"Dividend Yield data not available"
        elif compare_values(company_value, operator, threshold):
            result["status"] = "pass"
            result["reason"] = f"Dividend Yield {company_value*100:.2f}% {operator} {threshold*100:.2f}% [PASS]"
        else:
            result["status"] = "fail"
            result["reason"] = f"Dividend Yield {company_value*100:.2f}% does NOT {operator} {threshold*100:.2f}% [FAIL]"
        
        parameter_logger.debug(f"Dividend Yield screening: company_id={company.get('company_id')} | {result}")
        return result
    except Exception as e:
        parameter_logger.error(f"Error screening dividend_yield: {e}", exc_info=True)
        return {
            "param": "dividend_yield",
            "status": "error",
            "reason": str(e),
            "company_value": None,
            "threshold": 0,
            "operator": ""
        }


def screen_parameter_growth(company: dict, constraint_str: str) -> dict:
    """Screen a company against GROWTH constraint."""
    try:
        operator, threshold = parse_constraint(constraint_str)
        company_value = get_company_value(company, "growth")
        
        result = {
            "param": "growth",
            "constraint": constraint_str,
            "company_value": company_value,
            "threshold": threshold,
            "operator": operator,
        }
        
        if company_value is None:
            result["status"] = "null"
            result["reason"] = f"Growth data not available"
        elif compare_values(company_value, operator, threshold):
            result["status"] = "pass"
            result["reason"] = f"Growth {company_value*100:.2f}% {operator} {threshold*100:.2f}% [PASS]"
        else:
            result["status"] = "fail"
            result["reason"] = f"Growth {company_value*100:.2f}% does NOT {operator} {threshold*100:.2f}% [FAIL]"
        
        parameter_logger.debug(f"Growth screening: company_id={company.get('company_id')} | {result}")
        return result
    except Exception as e:
        parameter_logger.error(f"Error screening growth: {e}", exc_info=True)
        return {
            "param": "growth",
            "status": "error",
            "reason": str(e),
            "company_value": None,
            "threshold": 0,
            "operator": ""
        }


# Mapping of parameter names to screening functions
PARAMETER_SCREENING_FUNCTIONS = {
    "revenue": screen_parameter_revenue,
    "ebitda": screen_parameter_ebitda,
    "net_income": screen_parameter_net_income,
    "market_cap": screen_parameter_market_cap,
    "gross_profit_margin": screen_parameter_gross_profit_margin,
    "return_on_equity": screen_parameter_return_on_equity,
    "debt_to_equity": screen_parameter_debt_to_equity,
    "pe_ratio": screen_parameter_pe_ratio,
    "price_to_book": screen_parameter_price_to_book,
    "dividend_yield": screen_parameter_dividend_yield,
    "growth": screen_parameter_growth,
}



# ============================================================================
# ACTUAL ASYNC IMPLEMENTATIONS - WITH COMPREHENSIVE LOGGING
# ============================================================================
async def _scale_liquidity_screening_impl(
        mandate_id: int,
        mandate_parameters: dict[str, Any] | None = None,
        company_id_list: list[int] | None = None
) -> str:
    """
    Screen companies against SCALE & LIQUIDITY mandate parameters.

    Args:
        mandate_id: Fund mandate ID
        mandate_parameters: Screening parameters (revenue, ebitda, net_income, market_cap). If None, defaults to empty dict.
        company_id_list: Optional list of specific company IDs to screen

    Returns:
        JSON string with passed and conditional companies with PER-PARAMETER screening results
    """
    try:
        # Log tool input
        tool_input = {
            "mandate_id": mandate_id,
            "mandate_parameters": mandate_parameters,
            "company_id_list": company_id_list
        }
        screening_logger.info(f"[SCALE/LIQUIDITY TOOL] Input: {json.dumps(tool_input, default=str)}")
        
        # Handle None mandate_parameters
        if mandate_parameters is None:
            mandate_parameters = {}

        # Filter only scale/liquidity parameters
        scale_liquidity_params = {
            k: v for k, v in mandate_parameters.items()
            if k.lower() in ["revenue", "ebitda", "net_income", "market_cap"]
        }

        if not scale_liquidity_params:
            screening_logger.info("[SCALE/LIQUIDITY TOOL] No scale/liquidity params in mandate. Skipping.")
            result = {
                "passed_companies": [],
                "conditional_companies": [],
                "tool_used": "scale_liquidity",
                "parameters_screened": [],
                "total_parameters": 0
            }
            screening_logger.info(f"[SCALE/LIQUIDITY TOOL] Output: {json.dumps(result)}")
            return json.dumps(result)

        screening_logger.info("[SCALE/LIQUIDITY TOOL] Starting screening")
        screening_logger.info(f"  - Mandate ID: {mandate_id}")
        screening_logger.info(f"  - Parameters to screen: {list(scale_liquidity_params.keys())}")
        if company_id_list:
            screening_logger.info(f"  - Company IDs to screen: {company_id_list}")

        # Await async DB helper
        companies_data = await get_companies_by_mandate_id(mandate_id, company_id_list)

        if not companies_data:
            result = {
                "passed_companies": [],
                "conditional_companies": [],
                "tool_used": "scale_liquidity",
                "parameters_screened": [],
                "total_parameters": len(scale_liquidity_params)
            }
            screening_logger.warning("[SCALE/LIQUIDITY TOOL] No companies fetched from DB")
            screening_logger.info(f"[SCALE/LIQUIDITY TOOL] Output: {json.dumps(result)}")
            return json.dumps(result)

        screening_logger.info(
            f"[SCALE/LIQUIDITY TOOL] Screening {len(companies_data)} companies against {len(scale_liquidity_params)} scale/liquidity parameters")

        # Screen companies using per-parameter functions
        screening_results = screen_companies_advanced(scale_liquidity_params, companies_data)
        passed_companies = screening_results.get("passed", [])
        conditional_companies = screening_results.get("conditional", [])
        failed_companies = screening_results.get("failed", [])

        screening_logger.info("[SCALE/LIQUIDITY TOOL] Screening Results:")
        screening_logger.info(f"   Passed: {len(passed_companies)} companies")
        screening_logger.info(f"   Conditional: {len(conditional_companies)} companies")
        screening_logger.info(f"   Failed: {len(failed_companies)} companies")

        # Format output with company_id already present
        passed_list = []
        for company in passed_companies:
            company_data = company["company_details"].copy()
            company_data["status"] = "Pass"
            company_data["reason"] = company.get("reason", "")
            company_data["parameter_results"] = company.get("parameter_results", [])
            company_data["company_name"] = company.get("company_name", "Unknown")
            company_data["Company"] = company_data["company_name"]
            passed_list.append(company_data)

        conditional_list = []
        for company in conditional_companies:
            company_data = company["company_details"].copy()
            company_data["status"] = "Conditional"
            company_data["reason"] = company.get("reason", "")
            company_data["null_parameters"] = company.get("null_parameters", [])
            company_data["parameter_results"] = company.get("parameter_results", [])
            company_data["company_name"] = company.get("company_name", "Unknown")
            company_data["Company"] = company_data["company_name"]
            conditional_list.append(company_data)

        failed_list = []
        for company in failed_companies:
            company_data = company["company_details"].copy()
            company_data["status"] = "Fail"
            company_data["reason"] = company.get("reason", "")
            company_data["parameter_results"] = company.get("parameter_results", [])
            company_data["company_name"] = company.get("company_name", "Unknown")
            company_data["Company"] = company_data["company_name"]
            failed_list.append(company_data)

        screening_logger.info(
            f"[SCALE/LIQUIDITY TOOL] Returning {len(passed_list)} passed + {len(conditional_list)} conditional + {len(failed_list)} failed companies\n")

        result = {
            "passed_companies": passed_list,
            "conditional_companies": conditional_list,
            "failed_companies": failed_list,
            "tool_used": "scale_liquidity",
            "passed_count": len(passed_list),
            "conditional_count": len(conditional_list),
            "failed_count": len(failed_list),
            "parameters_screened": list(scale_liquidity_params.keys()),
            "total_parameters": len(scale_liquidity_params),
            "total_companies_screened": len(companies_data)
        }
        
        screening_logger.info(f"[SCALE/LIQUIDITY TOOL] Output Summary: {len(passed_list)} passed, {len(conditional_list)} conditional")
        return json.dumps(result, default=str)

    except Exception as e:
        screening_logger.error(f"[SCALE/LIQUIDITY TOOL] Error: {str(e)}", exc_info=True)
        result = {
            "passed_companies": [],
            "conditional_companies": [],
            "tool_used": "scale_liquidity",
            "error": str(e),
            "parameters_screened": [],
            "total_parameters": 0
        }
        return json.dumps(result)


async def _profitability_valuation_screening_impl(
        mandate_id: int,
        mandate_parameters: dict[str, Any] | None = None,
        company_id_list: list[int] | None = None
) -> str:
    """
    Screen companies against PROFITABILITY & VALUATION mandate parameters.

    Args:
        mandate_id: Fund mandate ID
        mandate_parameters: Screening parameters (gross_profit_margin, return_on_equity, debt_to_equity, pe_ratio, price_to_book, dividend_yield, growth). If None, defaults to empty dict.
        company_id_list: Optional list of specific company IDs to screen

    Returns:
        JSON string with passed and conditional companies with PER-PARAMETER screening results
    """
    try:
        # Log tool input
        tool_input = {
            "mandate_id": mandate_id,
            "mandate_parameters": mandate_parameters,
            "company_id_list": company_id_list
        }
        screening_logger.info(f"[PROFITABILITY/VALUATION TOOL] Input: {json.dumps(tool_input, default=str)}")
        
        # Handle None mandate_parameters
        if mandate_parameters is None:
            mandate_parameters = {}

        # Filter only profitability/valuation parameters
        prof_val_params = {
            k: v for k, v in mandate_parameters.items()
            if k.lower() in [
                "gross_profit_margin", "return_on_equity", "debt_to_equity",
                "pe_ratio", "price_to_book", "dividend_yield", "growth"
            ]
        }

        if not prof_val_params:
            screening_logger.info("[PROFITABILITY/VALUATION TOOL] No profitability/valuation params in mandate. Skipping.")
            result = {
                "passed_companies": [],
                "conditional_companies": [],
                "tool_used": "profitability_valuation",
                "parameters_screened": [],
                "total_parameters": 0
            }
            screening_logger.info(f"[PROFITABILITY/VALUATION TOOL] Output: {json.dumps(result)}")
            return json.dumps(result)

        screening_logger.info("[PROFITABILITY/VALUATION TOOL] Starting screening")
        screening_logger.info(f"  - Mandate ID: {mandate_id}")
        screening_logger.info(f"  - Parameters to screen: {list(prof_val_params.keys())}")
        if company_id_list:
            screening_logger.info(f"  - Company IDs to screen: {company_id_list}")

        # Await async DB helper
        companies_data = await get_companies_by_mandate_id(mandate_id, company_id_list)

        if not companies_data:
            result = {
                "passed_companies": [],
                "conditional_companies": [],
                "tool_used": "profitability_valuation",
                "parameters_screened": [],
                "total_parameters": len(prof_val_params)
            }
            screening_logger.warning("[PROFITABILITY/VALUATION TOOL] No companies fetched from DB")
            screening_logger.info(f"[PROFITABILITY/VALUATION TOOL] Output: {json.dumps(result)}")
            return json.dumps(result)

        screening_logger.info(
            f"[PROFITABILITY/VALUATION TOOL] Screening {len(companies_data)} companies against {len(prof_val_params)} profitability/valuation parameters")

        # Screen companies using per-parameter functions
        screening_results = screen_companies_advanced(prof_val_params, companies_data)
        passed_companies = screening_results.get("passed", [])
        conditional_companies = screening_results.get("conditional", [])
        failed_companies = screening_results.get("failed", [])

        screening_logger.info("[PROFITABILITY/VALUATION TOOL] Screening Results:")
        screening_logger.info(f"  Passed: {len(passed_companies)} companies")
        screening_logger.info(f"  Conditional: {len(conditional_companies)} companies")
        screening_logger.info(f"  Failed: {len(failed_companies)} companies")

        # Format output with company_id already present
        passed_list = []
        for company in passed_companies:
            company_data = company["company_details"].copy()
            company_data["status"] = "Pass"
            company_data["reason"] = company.get("reason", "")
            company_data["parameter_results"] = company.get("parameter_results", [])
            company_data["company_name"] = company.get("company_name", "Unknown")
            company_data["Company"] = company_data["company_name"]
            passed_list.append(company_data)

        conditional_list = []
        for company in conditional_companies:
            company_data = company["company_details"].copy()
            company_data["status"] = "Conditional"
            company_data["reason"] = company.get("reason", "")
            company_data["null_parameters"] = company.get("null_parameters", [])
            company_data["parameter_results"] = company.get("parameter_results", [])
            company_data["company_name"] = company.get("company_name", "Unknown")
            company_data["Company"] = company_data["company_name"]
            conditional_list.append(company_data)

        failed_list = []
        for company in failed_companies:
            company_data = company["company_details"].copy()
            company_data["status"] = "Fail"
            company_data["reason"] = company.get("reason", "")
            company_data["parameter_results"] = company.get("parameter_results", [])
            company_data["company_name"] = company.get("company_name", "Unknown")
            company_data["Company"] = company_data["company_name"]
            failed_list.append(company_data)

        screening_logger.info(
            f"[PROFITABILITY/VALUATION_TOOL] Returning {len(passed_list)} passed + {len(conditional_list)} conditional + {len(failed_list)} failed companies\n")

        result = {
            "passed_companies": passed_list,
            "conditional_companies": conditional_list,
            "failed_companies": failed_list,
            "tool_used": "profitability_valuation",
            "passed_count": len(passed_list),
            "conditional_count": len(conditional_list),
            "failed_count": len(failed_list),
            "parameters_screened": list(prof_val_params.keys()),
            "total_parameters": len(prof_val_params),
            "total_companies_screened": len(companies_data)
        }
        
        screening_logger.info(f"[PROFITABILITY/VALUATION TOOL] Output Summary: {len(passed_list)} passed, {len(conditional_list)} conditional")
        return json.dumps(result, default=str)

    except Exception as e:
        screening_logger.error(f"[PROFITABILITY/VALUATION TOOL] Error: {str(e)}", exc_info=True)
        result = {
            "passed_companies": [],
            "conditional_companies": [],
            "tool_used": "profitability_valuation",
            "error": str(e),
            "parameters_screened": [],
            "total_parameters": 0
        }
        return json.dumps(result)


# ============================================================================
# HELPER FUNCTIONS (Preserved from mandate_screening.py)
# ============================================================================
def parse_constraint(constraint_str: str) -> tuple:
    """Parse constraint - handles $, %, B, M, T and converts all thresholds into MILLIONS."""
    try:
        constraint_str = str(constraint_str).strip()
        constraint_str = constraint_str.replace("&amp;gt;", "&gt;").replace("&amp;lt;", "&lt;")

        # Special cases
        if constraint_str.lower() == "positive":
            return ">", 0

        if constraint_str.lower() in ["", "-", "na", "n/a", "none", "null"]:
            return "skip", 0

        if "not required" in constraint_str.lower():
            return "skip", 0

        constraint_str = constraint_str.replace("&amp;amp;gt;", "&gt;").replace("&amp;amp;lt;", "&lt;")

        # Extract operator and number - now handles $ and other currency symbols
        match = re.search(r'([><]=?|==|!=|=)\s*[\$]*\s*([\d.]+)', constraint_str)
        if not match:
            return ">", 0

        operator = match.group(1)
        threshold = float(match.group(2))

        # Identify units
        has_dollar = '$' in constraint_str
        has_billion = 'B' in constraint_str.upper() and 'M' not in constraint_str.upper()
        has_trillion = 'T' in constraint_str.upper()
        has_million = 'M' in constraint_str.upper()
        has_percent = '%' in constraint_str

        # Convert currency amounts -> millions
        if has_dollar:
            if has_billion:
                threshold = threshold * 1000
            elif has_trillion:
                threshold = threshold * 1000000
            elif not has_million:
                threshold = threshold / 1_000_000

        # Convert % -> decimal
        if has_percent:
            if threshold > 1:
                threshold = threshold / 100

        return operator, threshold

    except Exception:
        return ">", 0


def _lookup_company_field(company: dict, keys: list[str]) -> Any:
    """Return the first non-null value for the provided company keys."""
    for key in keys:
        if key in company and company[key] is not None:
            return company[key]
    return None


def get_company_value(company: dict, param_name: str) -> float | None:
    """Get numeric value from company - ALL VALUES IN MILLIONS"""
    try:
        param_lower = param_name.lower()

        # Handle REVENUE
        if param_lower == "revenue":
            revenue = _lookup_company_field(company, ["Revenue", "revenue", "revenue_usd", "revenue_m", "Revenue USD", "Revenue (M)"])
            if revenue is None:
                return None
            parsed = parse_value(revenue)
            company_logger.debug(f"Revenue lookup: raw='{revenue}', parsed={parsed}")
            return parsed

        # Handle NET INCOME
        if param_lower == "net_income":
            net_income = _lookup_company_field(company, ["Net Income", "net_income", "net income", "NetIncome"])
            if net_income is None:
                return None
            parsed = parse_value(net_income)
            company_logger.debug(f"Net Income lookup: raw='{net_income}', parsed={parsed}")
            return parsed

        # Handle MARKET CAP
        if param_lower == "market_cap":
            market_cap = _lookup_company_field(company, ["Market Cap", "market_cap", "market cap", "marketcap"])
            if market_cap is None:
                return None
            parsed = parse_value(market_cap)
            company_logger.debug(f"Market Cap lookup: raw='{market_cap}', parsed={parsed}")
            return parsed

        # Handle EBITDA
        if param_lower == "ebitda":
            ebitda_raw = _lookup_company_field(company, ["EBITDA", "ebitda", "EBITDA (M)", "ebitda_m"])
            if ebitda_raw is None:
                return None
            parsed = parse_value(ebitda_raw)
            company_logger.debug(f"EBITDA lookup: raw='{ebitda_raw}', parsed={parsed}")
            return parsed

        # Handle GROSS PROFIT MARGIN
        if param_lower == "gross_profit_margin":
            gpm = _lookup_company_field(company, ["Gross Profit Margin", "gross_profit_margin", "gross profit margin", "Gross Profit Margin (%)", "gross_profit_margin_percent"])
            if gpm is None:
                return None
            parsed = parse_value(gpm)
            if parsed is None:
                return None
            if parsed > 1:
                parsed = parsed / 100
            company_logger.debug(f"Gross Profit Margin lookup: raw='{gpm}', parsed={parsed}")
            return parsed

        # Handle RETURN ON EQUITY
        if param_lower == "return_on_equity":
            roe = _lookup_company_field(company, ["Return on Equity", "return_on_equity", "return on equity", "Return On Equity (%)", "return_on_equity_percent"])
            if roe is None:
                return None
            parsed = parse_value(roe)
            if parsed is None:
                return None
            if parsed > 1:
                parsed = parsed / 100
            company_logger.debug(f"Return on Equity lookup: raw='{roe}', parsed={parsed}")
            return parsed

        # Standard field mapping
        field_map = {
            "debt_to_equity": ["Debt / Equity", "debt_to_equity", "debt_equity", "DebtToEquity"],
            "pe_ratio": ["P/E Ratio", "pe_ratio", "PE Ratio", "pe_ratio_x"],
            "price_to_book": ["Price/Book", "price_to_book", "price_book", "Price to Book"],
            "dividend_yield": ["Dividend Yield", "dividend_yield", "dividend_yield_percent", "Dividend Yield (%)"]
        }

        fields = field_map.get(param_lower, [param_name])

        for field in fields:
            if field in company:
                value = company[field]
                if value is None:
                    continue
                parsed = parse_value(value)
                company_logger.debug(f"{param_name} lookup: field='{field}', raw='{value}', parsed={parsed}")
                if parsed is not None:
                    return parsed

        company_logger.debug(f"No value found for param '{param_name}' in company_id={company.get('company_id')}")
        return None
    except Exception as e:
        company_logger.error(f"Error getting value for {param_name}: {e}")
        return None


def parse_value(value: Any) -> float | None:
    """Parse various value formats (B, M, T, %) - RETURNS VALUE IN MILLIONS"""
    try:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            value_str = str(value).strip()

            # Remove newlines, %, $, commas, and whitespace within units
            value_str = value_str.replace("\n", "").replace("%", "").replace("$", "").replace(",", "").replace(" ", "")
            # Normalize decimals before unit suffixes, e.g. "244.12B" -> "24412B"
            value_str = re.sub(r'(\d)\.(\d+)([BMTbmtKk])', r'\1\2\3', value_str)
            # Strip out any trailing non-numeric text like currency codes
            value_str = re.sub(r'[^0-9.\-+KMBTkmbt]', '', value_str)

            match = re.match(r'^([+-]?\d+(?:\.\d+)?)([KMBT]?)$', value_str, re.IGNORECASE)
            if not match:
                company_logger.debug(f"parse_value: no regex match for '{value_str}' (original: '{value}')")
                return None

            number = float(match.group(1))
            unit = match.group(2).upper()

            if unit == 'T':
                result = number * 1000000
            elif unit == 'B':
                result = number * 1000
            elif unit == 'M':
                result = number
            elif unit == 'K':
                result = number / 1000
            else:
                result = number

            company_logger.debug(f"parse_value: '{value}' -> '{value_str}' -> {result}")
            return result

        company_logger.debug(f"parse_value: unsupported type {type(value)} for value '{value}'")
        return None
    except Exception as e:
        company_logger.error(f"parse_value error for '{value}': {e}")
        return None


# ============================================================================
# UPDATED SCREENING FUNCTION - PRESERVE COMPANY_ID
# ============================================================================
# Deprecated simple screening path removed. Use screen_companies_advanced for per-parameter results.

def compare_values(actual: float, operator: str, threshold: float) -> bool:
    """Compare actual vs threshold"""
    try:
        if actual is None or threshold is None:
            return False

        if operator == ">" and threshold == 0:
            return actual > 0
        elif operator == ">":
            return actual > threshold
        elif operator == ">=":
            return actual >= threshold
        elif operator == "<":
            return actual < threshold
        elif operator == "<=":
            return actual <= threshold
        elif operator == "==":
            return actual == threshold
        return False
    except Exception:
        return False


# ============================================================================
# ADVANCED SCREENING WITH PER-PARAMETER RESULTS
# ============================================================================
def screen_companies_advanced(mandate_parameters: dict, companies: list) -> dict:
    """
    Screen companies using per-parameter functions.
    Returns pass/conditional/fail with detailed per-parameter results.
    """
    passed_companies = []
    conditional_companies = []
    failed_companies = []

    try:
        if not mandate_parameters or not companies:
            screening_logger.warning("No parameters or companies to screen")
            return {"passed": [], "conditional": []}

        for company in companies:
            try:
                company_id = company.get("company_id")
                
                # Validate and extract company name with better handling
                company_name = extract_validated_company_name(company)
                company_logger.info(f"Screening company_id={company_id}, name={company_name}")
                
                sector = company.get("Sector", company.get("sector", "Unknown")).strip()

                # Run all parameter screening functions
                parameter_results = []
                all_passed = True
                all_non_null_passed = True
                null_params = []
                pass_reasons = []

                for param_name, constraint_str in mandate_parameters.items():
                    if "not required" in str(constraint_str).lower():
                        parameter_results.append({
                            "param": param_name,
                            "status": "skipped",
                            "reason": "Parameter marked as not required"
                        })
                        continue

                    # Get appropriate screening function
                    param_lower = param_name.lower()
                    screening_func = PARAMETER_SCREENING_FUNCTIONS.get(param_lower)

                    if not screening_func:
                        parameter_logger.warning(f"No screening function for parameter: {param_name}")
                        parameter_results.append({
                            "param": param_name,
                            "status": "error",
                            "reason": f"No screening function available"
                        })
                        continue

                    # Screen this parameter
                    param_result = screening_func(company, constraint_str)
                    parameter_results.append(param_result)

                    # Track overall status
                    if param_result["status"] == "null":
                        all_passed = False
                        null_params.append(param_name)
                    elif param_result["status"] == "fail":
                        all_passed = False
                        all_non_null_passed = False
                        break
                    elif param_result["status"] == "pass":
                        pass_reasons.append(param_result["reason"])

                # Determine overall company status
                if all_passed:
                    # All parameters passed
                    reason_text = " | ".join(pass_reasons) if pass_reasons else "Meets all mandate criteria"
                    passed_companies.append({
                        "company_name": company_name,
                        "sector": sector,
                        "company_id": company_id,
                        "status": "Pass",
                        "reason": reason_text,
                        "parameter_results": parameter_results,
                        "company_details": company
                    })
                    company_logger.info(f"PASSED: company_id={company_id}, name={company_name}")
                elif all_non_null_passed and null_params:
                    # Parameters passed but some data missing
                    reason_text = " | ".join(pass_reasons) if pass_reasons else "Meets required criteria"
                    missing_data_text = ", ".join(null_params)
                    full_reason = f"Missing data for: {missing_data_text}. Other metrics: {reason_text}"

                    conditional_companies.append({
                        "company_name": company_name,
                        "sector": sector,
                        "company_id": company_id,
                        "status": "Conditional",
                        "reason": full_reason,
                        "null_parameters": null_params,
                        "parameter_results": parameter_results,
                        "company_details": company
                    })
                    company_logger.info(f"CONDITIONAL: company_id={company_id}, name={company_name}, missing: {missing_data_text}")
                else:
                    # Company failed on at least one required parameter — record as failed
                    failing_reasons = [pr.get("reason") for pr in parameter_results if pr.get("status") == "fail"]
                    fail_reason = " | ".join(failing_reasons) if failing_reasons else "Failed required parameter(s)"
                    failed_companies.append({
                        "company_name": company_name,
                        "sector": sector,
                        "company_id": company_id,
                        "status": "Fail",
                        "reason": fail_reason,
                        "parameter_results": parameter_results,
                        "company_details": company
                    })
                    company_logger.info(f"FAILED: company_id={company_id}, name={company_name}, reason: {fail_reason}")

            except Exception as e:
                company_logger.error(f"Error screening company {company.get('company_id')}: {e}", exc_info=True)

        screening_logger.info(f"Advanced screening complete: {len(passed_companies)} passed, {len(conditional_companies)} conditional, {len(failed_companies)} failed")
        return {"passed": passed_companies, "conditional": conditional_companies, "failed": failed_companies}

    except Exception as e:
        screening_logger.error(f"Fatal error in screen_companies_advanced: {e}", exc_info=True)
        return {"passed": [], "conditional": []}


def extract_validated_company_name(company: dict) -> str:
    """
    Extract and validate company name from company dict.
    Ensures we get real names from DB, not generic placeholders.
    """
    try:
        # Try multiple keys to find real company name
        name_keys = ["Company", "Company ", "Company Name", "company_name", "company", "Name", "name"]
        
        for key in name_keys:
            if key in company and company[key]:
                name = str(company[key]).strip()
                if name and name.lower() not in ["unknown", "company1", "company", "n/a", ""]:
                    company_logger.debug(f"Found valid company name: '{name}' from key '{key}'")
                    return name
        
        # Fallback
        company_logger.warning(f"Could not find valid company name for company_id={company.get('company_id')}. Using 'Unknown'")
        return "Unknown"
    except Exception as e:
        company_logger.error(f"Error extracting company name: {e}")
        return "Unknown"


# ============================================================================
# OPTIMIZED: DATABASE HELPER - FETCH COMPANIES WITH COMPANY_ID (ASYNC)
# ============================================================================
async def get_companies_by_mandate_id(mandate_id: int, company_id_list: list[int] = None) -> list[dict[str, Any]]:
    """
    OPTIMIZED: Fetch companies from Sourcing table with company_id already embedded.
    Can filter by specific company IDs if provided.
    Logs all DB operations comprehensively.

    Args:
        mandate_id: Fund mandate ID
        company_id_list: Optional list of specific company IDs to fetch

    Returns:
        List of company_data dicts (each with company_id already in it).
    """
    try:
        # Log DB fetch input
        screening_logger.info(f"[DB FETCH] Starting fetch for mandate_id={mandate_id}")
        if company_id_list:
            screening_logger.info(f"[DB FETCH] Filtering to specific company_ids: {company_id_list}")

        # Build filter query
        filter_kwargs = {
            "fund_mandate_id": mandate_id,
            "deleted_at__isnull": True
        }

        # Query Sourcing table (async ORM call)
        if company_id_list and len(company_id_list) > 0:
            sourcing_records = await Sourcing.filter(**filter_kwargs).filter(company_id__in=company_id_list).all()
            screening_logger.info(f"[DB FETCH] Fetched {len(sourcing_records)} specific companies from DB")
        else:
            sourcing_records = await Sourcing.filter(**filter_kwargs).all()
            screening_logger.info(f"[DB FETCH] Fetched {len(sourcing_records)} total companies from DB")

        company_ids = [sourcing.company_id for sourcing in sourcing_records]
        company_name_map = {}
        if company_ids:
            companies = await Company.filter(id__in=company_ids).all()
            company_name_map = {company.id: company.company_name for company in companies if company.company_name}

        companies_list = []

        for idx, sourcing in enumerate(sourcing_records, 1):
            company_id = sourcing.company_id
            company_data = sourcing.company_data

            # Handle different data formats
            if isinstance(company_data, str):
                try:
                    company_data = json.loads(company_data)
                except json.JSONDecodeError:
                    screening_logger.warning(f"[DB FETCH] Record {idx}: Failed to parse JSON for company_id={company_id}, skipping")
                    continue
            elif isinstance(company_data, dict):
                pass
            else:
                screening_logger.warning(f"[DB FETCH] Record {idx}: Unknown data format for company_id={company_id}, skipping")
                continue

            # Add company_id if not already present
            if "company_id" not in company_data:
                company_data["company_id"] = company_id

            # Add canonical company_name/Company fields where possible
            company_name = company_data.get("company_name") or company_data.get("Company") or company_data.get("company") or company_data.get("Name")
            if not company_name:
                company_name = company_name_map.get(company_id)

            company_name = str(company_name).strip() if company_name else "Unknown"
            company_data["company_name"] = company_name
            company_data["Company"] = company_name

            # Validate and log company name
            validated_name = extract_validated_company_name(company_data)
            company_logger.debug(f"[DB FETCH] Record {idx}: company_id={company_id}, name={validated_name}")

            companies_list.append(company_data)

        return companies_list

    except Exception as e:
        screening_logger.error(f"[DB FETCH] Error fetching companies by mandate_id: {e}", exc_info=True)
        return []


# ============================================================================
# SYNC WRAPPER FUNCTIONS FOR STRUCTURED TOOLS - WITH PROPER ASYNC HANDLING
# ============================================================================

def _run_async(coro):
    """Run async coroutine safely in both sync and async contexts."""
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running (e.g., in FastAPI), we can't use run_until_complete
            # Use nest_asyncio if available, otherwise raise an error
            try:
                import nest_asyncio
                nest_asyncio.apply()
                return asyncio.run(coro)
            except ImportError:
                # Fallback: Create a new thread to run the coroutine
                import threading
                result = [None]
                exception = [None]

                def run_in_thread():
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        result[0] = new_loop.run_until_complete(coro)
                    except Exception as e:
                        exception[0] = e
                    finally:
                        new_loop.close()

                thread = threading.Thread(target=run_in_thread)
                thread.start()
                thread.join()

                if exception[0]:
                    raise exception[0]
                return result[0]
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop in current thread, create new one
        return asyncio.run(coro)


def scale_liquidity_screening_tool_sync(
        mandate_id: int,
        mandate_parameters: dict[str, Any] | None = None,
        company_id_list: list[int] | None = None
) -> str:
    """Screen companies against SCALE & LIQUIDITY mandate parameters (sync wrapper)."""
    if mandate_parameters is None:
        mandate_parameters = {}
    screening_logger.info(f"[SCALE/LIQUIDITY SYNC] Wrapper called for mandate_id={mandate_id}")
    screening_logger.debug(f"[SCALE/LIQUIDITY SYNC] Parameters: {mandate_parameters}")
    result_str = _run_async(_scale_liquidity_screening_impl(mandate_id, mandate_parameters, company_id_list))
    screening_logger.debug(f"[SCALE/LIQUIDITY SYNC] Wrapper returning result")
    return result_str


def profitability_valuation_screening_tool_sync(
        mandate_id: int,
        mandate_parameters: dict[str, Any] | None = None,
        company_id_list: list[int] | None = None
) -> str:
    """Screen companies against PROFITABILITY & VALUATION mandate parameters (sync wrapper)."""
    if mandate_parameters is None:
        mandate_parameters = {}
    screening_logger.info(f"[PROFITABILITY/VALUATION SYNC] Wrapper called for mandate_id={mandate_id}")
    screening_logger.debug(f"[PROFITABILITY/VALUATION SYNC] Parameters: {mandate_parameters}")
    result_str = _run_async(_profitability_valuation_screening_impl(mandate_id, mandate_parameters, company_id_list))
    screening_logger.debug(f"[PROFITABILITY/VALUATION SYNC] Wrapper returning result")
    return result_str


# ============================================================================
# CREATE STRUCTURED TOOLS FOR LANGGRAPH
# ============================================================================
scale_liquidity_screening_tool = StructuredTool.from_function(
    func=scale_liquidity_screening_tool_sync,
    name="scale_liquidity_screening_tool",
    description="Screen companies against SCALE & LIQUIDITY mandate parameters (revenue, ebitda, net_income, market_cap). Fetches from database and returns JSON with passed and conditional companies.",
)

profitability_valuation_screening_tool = StructuredTool.from_function(
    func=profitability_valuation_screening_tool_sync,
    name="profitability_valuation_screening_tool",
    description="Screen companies against PROFITABILITY & VALUATION mandate parameters (gross_profit_margin, return_on_equity, debt_to_equity, pe_ratio, price_to_book, dividend_yield, growth). Fetches from database and returns JSON with passed and conditional companies.",
)