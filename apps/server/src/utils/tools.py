import asyncio  # If needed for testing
import json
import os
from datetime import datetime
from pathlib import Path
from difflib import get_close_matches

import fitz
from langchain_classic.tools import tool
from rapidfuzz import process

import requests
import yfinance as yf

from utils.gpt_4_llm import get_azure_chat_openai
import os
import sys
from dotenv import load_dotenv
load_dotenv()

LLM = get_azure_chat_openai()

# Removed static mappings - using LLM only for semantic normalization

def normalize_value(user_input: str, db_values: list) -> str | None:
    """Normalize user input semantically by aligning with DB values using LLM only.

    Strategy:
    1. Exact DB value match (case-insensitive)
    2. LLM semantic mapping
    3. Fuzzy fallback on the LLM response
    4. Return None if no strong DB match exists
    """
    if not user_input:
        return None

    normalized_input = user_input.strip()
    normalized_input_lower = normalized_input.lower()

    # 1. Exact DB value match (case-insensitive)
    for db_value in db_values:
        if db_value and db_value.strip().lower() == normalized_input_lower:
            return db_value

    # 2. LLM semantic mapping
    if db_values:
        db_list_str = ", ".join([f"'{v}'" for v in db_values])
        prompt = f"""You are a mapping assistant. Map user input to exactly one value from this list.

User input: '{normalized_input}'
Database options: [{db_list_str}]

Rules:
- Choose the best semantically equivalent option.
- Prefer exact semantics over substring.
- If no good match exists, respond with 'none'.
- Output must be exactly one item from the database options or 'none'.

Examples:
- 'America' -> 'US'
- 'United states of america' -> 'US'
- 'Tech' -> 'Technology'
- 'software & it' -> 'Software & IT Services'
"""
        try:
            llm_response = LLM.invoke(prompt).content.strip()
            if llm_response and llm_response.lower() != 'none':
                llm_response_lower = llm_response.strip().lower()
                for db_value in db_values:
                    if db_value.strip().lower() == llm_response_lower:
                        return db_value

                # If LLM returns a semantically equivalent label, try fuzzy match against DB values
                fuzzy_match = process.extractOne(llm_response_lower, [v.lower() for v in db_values], score_cutoff=85)
                if fuzzy_match:
                    best_text = fuzzy_match[0]
                    for db_value in db_values:
                        if db_value.strip().lower() == best_text:
                            return db_value
        except Exception as e:
            print(f"LLM mapping failed: {e}")

    # 3. Fuzzy matching fallback on the original input
    if db_values:
        fuzzy_match = process.extractOne(normalized_input_lower, [v.lower() for v in db_values], score_cutoff=85)
        if fuzzy_match:
            best_text = fuzzy_match[0]
            for db_value in db_values:
                if db_value.strip().lower() == best_text:
                    return db_value

    # 4. No reliable match
    return None

# =================================Old up================
@tool
def scan_mandate_folder_and_parse() -> dict:
    """Scan input_fund_mandate/ → Extract LATEST PDF → Return dict with name + full text."""
    folder = Path(__file__).parent.parent / "input_fund_mandate"

    pdfs = list(folder.glob("*.pdf"))
    print(f"🔍 Found PDFs: {[p.name for p in pdfs]}")

    if not pdfs:
        return {"error": f"No PDF in {folder.absolute()}", "pdfs": []}

    latest = max(pdfs, key=os.path.getmtime)
    doc = fitz.open(latest)
    text = "".join(page.get_text() for page in doc)
    doc.close()

    print(f"✅ Parsed {latest.name}: {len(text)} chars")
    return {
        "pdf_name": latest.name,
        "full_text": text,
        "char_count": len(text)
    }


@tool
def extract_dynamic_criteria(raw_text: str, capability_params: str) -> str:
    """Extract criteria using dynamic capability_params → subprocess_name as keys."""
    try:
        # Parse capability_params JSON
        params = json.loads(capability_params)
        print(f"🔍 Processing {len(params)} subprocesses")

        # Build dynamic template
        dynamic_template = {
            "mandate": {
                "fund_name": "[fund name - e.g. 'ABC Fund']",
                "fund_size": "[fund size - e.g. '500 million USD']"
            }
        }

        for subprocess_id, details in params.items():
            subprocess_name = details['subprocess_name']
            data_elements = details['data_elements']
            dynamic_template["mandate"][subprocess_name] = {
                field: "" for field in data_elements
            }

        template_json = json.dumps(dynamic_template, indent=2)

        # LLM extraction prompt
        prompt = f"""Extract fund mandate criteria from PDF into EXACT JSON template.
Fill ONLY fields in template. Empty string "" if not found.
Please return JSON ONLY, no raw answers. Also ensure you make the dynamic fields as per capability_params.

For the Country names, Try to understand and match 
Eg : "United States", "USA", "U.S." → "US"

CRITICAL: For FINANCIAL PARAMETERS, detect thresholds and convert to SYMBOLS:

EXAMPLES FROM PDF TEXT → JSON OUTPUT:
• "ARR must exceed $35M" → "ARR": "> $35M USD"
• "Revenue over 50 million" → "Revenue": "> $50M USD" 
• "Market cap above $1B" → "Market Cap": "> $1B USD"
• "Less than 10% burn rate" → "Burn Rate": "< 10%"
• "EBITDA margin of 25-30%" → "EBITDA Margin": "= 25-30%"
• "P/E ratio between 15-20x" → "P/E Ratio": "= 15-20x"
• "Minimum $100M AUM" → "AUM": ">= $100M USD"

RULES:
1. Use >, <, >=, <=, = symbols ALWAYS for numbers
2. Keep USD, %, B, M suffixes
3. "Must be", "exceed", "above", "over" → >
4. "Less than", "below", "under" → <
5. "Between X-Y", "range X-Y" → "= X-Y"
6. Exact match → =
7. If u can find no value put '-' 
8. For Net Income use "positive" or "negative" only if specified, else use symbols as above


PDF TEXT (search carefully):
{raw_text}

EXACT JSON TEMPLATE:
{template_json}"""

        result = LLM.invoke(prompt).content.strip()
        print(f"✅ Dynamic extraction: {len(result)} chars")
        return result

    except json.JSONDecodeError as e:
        return f'{{"error": "Invalid capability_params JSON: {str(e)}"}}'
    except Exception as e:
        return f'{{"error": "Extraction failed: {str(e)}"}}'


from langchain_core.tools import Tool
from tortoise.transactions import in_transaction

from database.models import Company, FundMandate, Sourcing


async def _async_load_and_filter_companies(user_filters_json: str) -> str:
    try:
        input_data = json.loads(user_filters_json)
        mandate_id = input_data.get("mandate_id")

        # 🚀 VALIDATE REQUIRED fund_mandate_id
        if not mandate_id:
            return json.dumps({
                "error": "fund_mandate_id REQUIRED. Format: {\"fund_mandate_id\": 1, \"additionalProp1\": {...}}"
            }, separators=(',', ':'))

        # Verify FundMandate exists
        fund_mandate = await FundMandate.get_or_none(id=mandate_id)
        if not fund_mandate:
            return json.dumps({
                "error": f"FundMandate id={mandate_id} not found"
            }, separators=(',', ':'))

        # Use 'additionalProp1' as the filters payload. If missing, treat as empty dict (fetch all companies).
        filters = input_data.get("additionalProp1") or {}

        # Normalize filters using semantic matching
        # Get unique DB values for normalization
        all_countries = await Company.filter(deleted_at__isnull=True).distinct().values_list('country', flat=True)
        all_sectors = await Company.filter(deleted_at__isnull=True).distinct().values_list('sector', flat=True)
        all_industries = await Company.filter(deleted_at__isnull=True).distinct().values_list('industry', flat=True)

        normalized_filters = {}
        priority_filter_values = [
            (["geography", "country"], "country", list(all_countries)),
            (["sector"], "sector", list(all_sectors)),
            (["industry"], "industry", list(all_industries))
        ]

        for input_keys, actual_col, db_values in priority_filter_values:
            for input_key in input_keys:
                if input_key in filters:
                    normalized_value = normalize_value(filters[input_key], db_values)
                    if normalized_value is None:
                        return json.dumps({
                            "total_companies": 0,
                            "qualified": [],
                            "filters_applied": {},
                            "matched_count": 0,
                            "sourcing_saved_ids": [],
                            "mandate_id": mandate_id,
                            "source": "database",
                            "query_executed_at": datetime.utcnow().isoformat(),
                            "warning": f"Unable to normalize filter '{input_key}' to any DB value"
                        }, default=str)
                    normalized_filters[actual_col] = normalized_value
                    break  # Use the first matching key

        filter_conditions = {}
        if 'country' in normalized_filters:
            filter_conditions['country__iexact'] = normalized_filters['country']
        if 'sector' in normalized_filters:
            filter_conditions['sector__iexact'] = normalized_filters['sector']
        if 'industry' in normalized_filters:
            filter_conditions['industry__iexact'] = normalized_filters['industry']

        async with in_transaction():
            total_companies = await Company.filter(deleted_at__isnull=True).count()

            if total_companies == 0:
                return json.dumps({
                    "total_companies": 0,
                    "qualified": [],
                    "message": "No companies in DB"
                }, default=str)

            # Choose query: if filter_conditions empty, fetch all companies (limit 100)
            if filter_conditions:
                filtered_query = Company.filter(deleted_at__isnull=True, **filter_conditions).limit(50)
            else:
                filtered_query = Company.filter(deleted_at__isnull=True).limit(100)

            filtered_companies = await filtered_query
            matched_count = len(filtered_companies)

            # � Save EACH company to Sourcing table (skip or update existing to avoid UNIQUE constraint)
            saved_sourcing_ids = []
            qualified = []
            for c in filtered_companies:
                company_data = {
                    **getattr(c, 'attributes', {}),
                    "Risks": c.risks if c.risks else {}
                }

                # Always create new - allows same company with different mandates
                sourcing = await Sourcing.create(
                    company_id=c.id,
                    company_data=company_data,
                    fund_mandate=fund_mandate,
                    selected_parameters=normalized_filters
                )
                saved_sourcing_ids.append(sourcing.company_id)

                # Build qualified entry with both id and company_id and a canonical Company name
                qualified.append({
                    "id": c.id,
                    "company_id": c.id,
                    "Company": getattr(c, 'company_name', None) or getattr(c, 'Company ', None) or '',
                    **getattr(c, 'attributes', {})
                })

        result = {
            "total_companies": total_companies,
            "qualified": qualified,
            "filters_applied": normalized_filters,
            "matched_count": matched_count,
            "sourcing_saved_ids": saved_sourcing_ids,  # [45,46,47]
            "mandate_id": mandate_id,
            "source": "database",
            "query_executed_at": datetime.utcnow().isoformat()
        }
        return json.dumps(result, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)}, separators=(',', ':'))


# ✅ SYNC WRAPPER for ToolNode (LangGraph v1.0.7)
def sync_load_and_filter_companies(user_filters_json: str) -> str:
    """Sync wrapper - LangGraph ToolNode calls this."""
    return asyncio.run(_async_load_and_filter_companies(user_filters_json))

# ✅ EXPORT THE TOOL (exact name your agent expects)
load_and_filter_companies = Tool(
    name="load_and_filter_companies",
    description="""Load companies from DATABASE → Filter by user filters → JSON with IDs (ACCURATE).
    Expects valid JSON: {"geography": "U.S.", "sector": "technology", "industry": "Software"} or {"additionalProp1": {...}}.
    Returns: total_companies, qualified list with IDs, filter details.""",
    func=sync_load_and_filter_companies,
)


# ===== New: External source via Yahoo Finance (yfinance + Yahoo search) =====
def _fetch_companies_from_yfinance(user_filters_json: str) -> str:
    """Search Yahoo Finance by sector/industry/geography and return company details via yfinance.

    Input: JSON string with keys: {"mandate_id": ..., "additionalProp1": {"geography":..., "sector":..., "industry":...}}
    Output: JSON string similar to existing local companies_list format under key `qualified`.
    """
    try:
        data = json.loads(user_filters_json)
        filters = data.get("additionalProp1", {}) or {}

        # Build a simple query from filters
        qparts = []
        for k in ("industry", "sector", "geography", "country"):
            v = filters.get(k) or filters.get(k.capitalize())
            if v:
                qparts.append(str(v))

        query = " ".join(qparts).strip() or ""

        # Yahoo Finance search endpoint
        search_url = (
            f"https://query2.finance.yahoo.com/v1/finance/search?q={requests.utils.quote(query)}&quotesCount=50&newsCount=0"
        )
        symbols = []
        try:
            r = requests.get(search_url, timeout=10)
            if r.ok:
                js = r.json()
                for item in js.get("quotes", []):
                    sym = item.get("symbol")
                    if sym:
                        symbols.append(sym)
        except Exception:
            # fallback: empty symbol list
            symbols = []

        # Deduplicate and limit
        symbols = list(dict.fromkeys(symbols))[:50]

        companies = []
        for sym in symbols:
            try:
                t = yf.Ticker(sym)
                info = t.info or {}
            except Exception:
                info = {}

            company = {
                "Company ": info.get("longName") or info.get("shortName") or sym,
                "Country": info.get("country") or filters.get("geography") or "",
                "Sector": info.get("sector") or "",
                "Industry": info.get("industry") or "",
                "Revenue": info.get("totalRevenue") or info.get("regularMarketPreviousClose") or None,
                "Dividend Yield": info.get("dividendYield"),
                "5-Years Growth": None,
                "Net Income": info.get("netIncome") or info.get("netIncomeToCommon") or None,
                "Total Assets": info.get("totalAssets"),
                "Total Equity": None,
                "EPS / Forecast": (
                    (str(info.get("trailingEps")) if info.get("trailingEps") is not None else "")
                    + "/"
                    + (str(info.get("forwardEps")) if info.get("forwardEps") is not None else "")
                ).strip("/"),
                "EBITDA": info.get("ebitda") or None,
                "1-Year Change": info.get("52WeekChange"),
                "P/E Ratio": info.get("trailingPE") or info.get("forwardPE"),
                "Debt / Equity": info.get("debtToEquity"),
                "Price/Book": info.get("priceToBook") or info.get("bookValue"),
                "Return on Equity": info.get("returnOnEquity"),
                "Market Cap": info.get("marketCap"),
                "Gross Profit Margin": info.get("grossMargins"),
                "Risks": {"source": "yahoo", "symbol": sym},
            }
            companies.append(company)

        result = {
            "total_companies": len(companies),
            "qualified": companies,
            "filters_applied": filters,
            "mandate_id": data.get("mandate_id"),
            "source": "yfinance",
            "query_executed_at": datetime.utcnow().isoformat(),
        }
        return json.dumps(result, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)}, separators=(",", ":"))
import os
import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def _fetch_companies_from_yfinance(user_filters_json: str) -> str:
    try:
        input_data = json.loads(user_filters_json)
        filters = input_data.get("additionalProp1", {}) or {}

        geography = filters.get("geography", "")
        sector_filter = filters.get("sector", "").lower()
        industry_filter = filters.get("industry", "").lower()

        api_key = os.getenv("FMP_API_KEY")

        def safe_get(url, params=None):
            try:
                return requests.get(url, params=params, timeout=15)
            except requests.exceptions.SSLError:
                return requests.get(url, params=params, timeout=15, verify=False)

        # ✅ STEP 1: Get all stocks (FREE)
        stock_list_url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={api_key}"
        response = safe_get(stock_list_url)

        try:
            stock_list = response.json()
        except Exception:
            return json.dumps({"error": "Invalid JSON response", "raw": response.text})

# ✅ Validate it's a list
        if not isinstance(stock_list, list):
            return json.dumps({
        "error": "Expected list from FMP",
        "response": stock_list
    })

# ✅ Safe slicing
        stock_list = stock_list[:50]

        results = []
        
        for stock in stock_list[:50]:  # limit to avoid huge calls
            symbol = stock.get("symbol")
            if not symbol:
                continue

            try:
                profile = safe_get(
                    f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={api_key}"
                ).json()[0]

                # ✅ Apply filters manually
                if geography and profile.get("country") != geography:
                    continue
                if sector_filter and sector_filter not in (profile.get("sector") or "").lower():
                    continue
                if industry_filter and industry_filter not in (profile.get("industry") or "").lower():
                    continue

                # ✅ GET EVERYTHING
                key_metrics = safe_get(
                    f"https://financialmodelingprep.com/api/v3/key-metrics/{symbol}?limit=1&apikey={api_key}"
                ).json()

                ratios = safe_get(
                    f"https://financialmodelingprep.com/api/v3/ratios/{symbol}?limit=1&apikey={api_key}"
                ).json()

                financials = safe_get(
                    f"https://financialmodelingprep.com/api/v3/income-statement/{symbol}?limit=1&apikey={api_key}"
                ).json()

                balance = safe_get(
                    f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{symbol}?limit=1&apikey={api_key}"
                ).json()

                # normalize safely
                key_metrics = key_metrics[0] if key_metrics else {}
                ratios = ratios[0] if ratios else {}
                financials = financials[0] if financials else {}
                balance = balance[0] if balance else {}

                # ✅ Merge EVERYTHING
                company_data = {
                    "Company": profile.get("companyName"),
                    "Symbol": symbol,
                    "Country": profile.get("country"),
                    "Sector": profile.get("sector"),
                    "Industry": profile.get("industry"),

                    "Profile": profile,
                    "Financials": financials,
                    "BalanceSheet": balance,
                    "KeyMetrics": key_metrics,
                    "Ratios": ratios
                }

                results.append(company_data)

                if len(results) >= 10:
                    break

            except Exception:
                continue

        return json.dumps({
            "qualified": results,
            "mandate_id": input_data.get("mandate_id"),
            "source": "fmp-free"
        }, default=str)

    except Exception as e:
        return json.dumps({"error": str(e)})

# Sync wrapper and Tool export
def sync_fetch_companies_from_yfinance(user_filters_json: str) -> str:
    return _fetch_companies_from_yfinance(user_filters_json)


fetch_companies_from_yfinance = Tool(
    name="fetch_companies_from_yfinance",
    description=(
        "Fetch companies using Yahoo Finance search + yfinance fundamentals."
        " Input JSON: {\\\"mandate_id\\\":1, \\\"additionalProp1\\\":{...}}."
    ),
    func=sync_fetch_companies_from_yfinance,
)