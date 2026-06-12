###Took S&p 500 companies list and profile data from wikipedia and financial modeling prep respectively. This is used as a sourcing tool for company data based on user input filters.###


#### Not to be used because the fin_mod_prep data is just the basic data not the financial data. 

import json
import os
import re
import warnings
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from langchain_classic.tools import tool

WIKI_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
FMP_PROFILE_URL = "https://financialmodelingprep.com/stable/profile"
CACHE_FILE = Path(__file__).parent / "snp500_companies.json"
FMP_PROFILE_FILE = Path(__file__).parent / "filtered_company_profiles.json"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = text.replace("&", "and")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def save_sp500_rows(rows: list[dict[str, str]]) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def load_cached_sp500_rows() -> list[dict[str, str]]:
    if not CACHE_FILE.exists():
        return []
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def normalize_filter_tokens(value: str) -> list[str]:
    normalized = normalize_text(value)
    return [token for token in normalized.split() if len(token) > 1]


def matches_filter(candidate: str, filter_value: str) -> bool:
    candidate_norm = normalize_text(candidate)
    filter_norm = normalize_text(filter_value)
    if not filter_norm:
        return True
    if filter_norm in candidate_norm or candidate_norm in filter_norm:
        return True

    candidate_tokens = normalize_filter_tokens(candidate_norm)
    filter_tokens = normalize_filter_tokens(filter_norm)
    if all(token in candidate_tokens for token in filter_tokens):
        return True
    if any(token in candidate_norm for token in filter_tokens):
        return True

    return False


def extract_sp500_table_rows() -> list[dict[str, str]]:
    """Fetch and parse the main S&P 500 Wikipedia table."""
    headers = {
        "User-Agent": "Fund-Mandate/1.0 (+https://github.com)",
        "Accept": "text/html,application/xhtml+xml",
    }
    verify_bundle = os.getenv("WIKI_CA_BUNDLE")
    if verify_bundle == "":
        verify_bundle = True
    disable_verify = str(os.getenv("WIKI_DISABLE_VERIFY", "false")).lower() in ("1", "true", "yes")
    cached_rows = load_cached_sp500_rows()

    try:
        response = requests.get(WIKI_SP500_URL, headers=headers, timeout=20, verify=verify_bundle)
        response.raise_for_status()
    except requests.exceptions.SSLError as ssl_error:
        if disable_verify:
            warnings.warn("Wikipedia SSL verification failed; retrying with verify=False because WIKI_DISABLE_VERIFY is true", UserWarning)
            response = requests.get(WIKI_SP500_URL, headers=headers, timeout=20, verify=False)
            response.raise_for_status()
        elif cached_rows:
            warnings.warn("Wikipedia SSL verification failed; returning cached S&P 500 rows instead", UserWarning)
            return cached_rows
        else:
            raise ssl_error
    except requests.exceptions.RequestException as request_error:
        if cached_rows:
            warnings.warn(f"Wikipedia request failed; returning cached S&P 500 rows instead: {request_error}", UserWarning)
            return cached_rows
        raise request_error

    soup = BeautifulSoup(response.content, "html.parser")
    tables = soup.find_all("table", class_=lambda value: value and "wikitable" in value and "sortable" in value)

    target_table = None
    for table in tables:
        caption = table.find("caption")
        if caption and "S&P 500 component stocks" in caption.get_text():
            target_table = table
            break

    if target_table is None:
        if tables:
            target_table = tables[0]
        else:
            raise ValueError("Unable to find S&P 500 wikitable on page")

    header_row = target_table.find("tr")
    header_cells = [th.get_text(strip=True) for th in header_row.find_all("th")] if header_row else []
    header_map = {}
    for idx, header in enumerate(header_cells):
        normalized = normalize_text(header)
        if "symbol" in normalized:
            header_map[idx] = "Symbol"
        elif "security" in normalized:
            header_map[idx] = "Security"
        elif "gics sector" in normalized or "gicssector" in normalized:
            header_map[idx] = "GICS Sector"
        elif "gics sub-industry" in normalized or "gics sub industry" in normalized or "gicssubindustry" in normalized:
            header_map[idx] = "GICS Sub-Industry"
        elif "headquarters location" in normalized or "headquarterslocation" in normalized:
            header_map[idx] = "Headquarters Location"

    rows = []
    for row in target_table.find_all("tr")[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 5:
            continue

        row_data: dict[str, str] = {
            "Symbol": "",
            "Security": "",
            "GICS Sector": "",
            "GICS Sub-Industry": "",
            "Headquarters Location": "",
        }
        for idx, cell in enumerate(cells):
            if idx not in header_map:
                continue
            text = cell.get_text(separator=" ", strip=True)
            row_data[header_map[idx]] = text

        if row_data["Symbol"]:
            rows.append(row_data)

    save_sp500_rows(rows)
    return rows


def parse_sp500_wikipedia_table_impl() -> str:
    """Fetch and parse the S&P 500 component stocks table from Wikipedia."""
    try:
        rows = extract_sp500_table_rows()
        return json.dumps({"total_companies": len(rows), "companies": rows}, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


def filter_sp500_by_input_impl(user_filters_json: str) -> str:
    """Filter S&P 500 companies by input sector and industry from Wikipedia."""
    try:
        payload = json.loads(user_filters_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {str(e)}"})

    filters = payload.get("additionalProp1") or {}
    sector_input = normalize_text(filters.get("sector", ""))
    industry_input = normalize_text(filters.get("industry", ""))
    mandate_id = payload.get("mandate_id")

    if not sector_input or not industry_input:
        return json.dumps({"error": "sector and industry are required in additionalProp1"})

    companies = load_cached_sp500_rows() or extract_sp500_table_rows()
    matched = []
    for company in companies:
        sector_value = company.get("GICS Sector", "")
        industry_value = company.get("GICS Sub-Industry", "")
        if matches_filter(sector_value, filters.get("sector", "")) and matches_filter(industry_value, filters.get("industry", "")):
            matched.append(company)

    result = {
        "mandate_id": mandate_id,
        "source": "wikipedia-sp500",
        "total_companies": len(companies),
        "matched_count": len(matched),
        "qualified": matched,
    }
    return json.dumps(result, indent=2)


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return
    try:
        with env_path.open("r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass


def get_fmp_api_key() -> str:
    if not os.getenv("FMP_API_KEY"):
        load_env_file(ENV_FILE)
    return os.getenv("FMP_API_KEY", "demo")


def save_fmp_company_profiles(profiles: list[dict[str, Any]]) -> None:
    try:
        with open(FMP_PROFILE_FILE, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def fetch_fmp_profiles(symbols: list[str]) -> list[dict[str, Any]]:
    api_key = get_fmp_api_key()
    headers = {
        "User-Agent": "Fund-Mandate/1.0 (+https://github.com)",
        "Accept": "application/json",
    }
    verify_bundle = os.getenv("FMP_CA_BUNDLE")
    if verify_bundle == "":
        verify_bundle = True
    disable_verify = str(os.getenv("FMP_DISABLE_VERIFY", "true")).lower() in ("1", "true", "yes")
    verify = False if disable_verify else (verify_bundle if verify_bundle is not None else True)

    profiles: list[dict[str, Any]] = []
    for symbol in symbols:
        params = {
            "symbol": symbol,
            "apikey": api_key,
        }
        try:
            response = requests.get(FMP_PROFILE_URL, headers=headers, params=params, timeout=20, verify=verify)
            response.raise_for_status()
        except requests.exceptions.SSLError as ssl_error:
            if disable_verify:
                warnings.warn("FMP SSL verification failed; retrying with verify=False because FMP_DISABLE_VERIFY is true", UserWarning)
                response = requests.get(FMP_PROFILE_URL, headers=headers, params=params, timeout=20, verify=False)
                response.raise_for_status()
            else:
                raise ssl_error
        except requests.exceptions.RequestException as request_error:
            warnings.warn(f"FMP profile request failed for {symbol}: {request_error}", UserWarning)
            continue

        data = response.json()
        if isinstance(data, dict) and data.get("Error Message"):
            warnings.warn(f"FMP error response for {symbol}: {data}", UserWarning)
            continue
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            profiles.append(data[0])
        elif isinstance(data, dict) and data:
            profiles.append(data)
        else:
            warnings.warn(f"Unexpected FMP profile format for {symbol}: {data}", UserWarning)

    return profiles


def fetch_filtered_company_profiles_impl(user_filters_json: str) -> str:
    """Fetch company profiles from FMP for filtered S&P 500 symbols and save to JSON."""
    try:
        payload = json.loads(user_filters_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {str(e)}"})

    mandate_id = payload.get("mandate_id")
    filtered_result = json.loads(filter_sp500_by_input_impl(user_filters_json))
    if filtered_result.get("error"):
        return json.dumps(filtered_result, indent=2)

    companies = filtered_result.get("qualified", [])
    symbols = [company.get("Symbol") for company in companies if company.get("Symbol")]
    if not symbols:
        return json.dumps({
            "mandate_id": mandate_id,
            "source": "financialmodelingprep",
            "matched_count": 0,
            "profiles_saved": False,
            "message": "No filtered symbols were found to fetch profiles for.",
        }, indent=2)

    try:
        profiles = fetch_fmp_profiles(symbols)
        save_fmp_company_profiles(profiles)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

    return json.dumps({
        "mandate_id": mandate_id,
        "source": "financialmodelingprep",
        "filtered_symbols": symbols,
        "profiles_count": len(profiles),
        "saved_file": str(FMP_PROFILE_FILE),
        "profiles": profiles,
    }, indent=2)


parse_sp500_wikipedia_table = tool(parse_sp500_wikipedia_table_impl)
filter_sp500_by_input = tool(filter_sp500_by_input_impl)
fetch_filtered_company_profiles = tool(fetch_filtered_company_profiles_impl)


if __name__ == "__main__":
    sample_input = {
        "additionalProp1": {
            "geography": "US",
            "sector": "Real Estate",
            "industry": "REITs",
        },
        "mandate_id": "3",
    }

    print("=== TEST: parse_sp500_wikipedia_table ===")
    print(parse_sp500_wikipedia_table_impl())
    print("\n=== TEST: filter_sp500_by_input ===")
    print(filter_sp500_by_input_impl(json.dumps(sample_input)))
    print("\n=== TEST: fetch_filtered_company_profiles ===")
    print(fetch_filtered_company_profiles_impl(json.dumps(sample_input)))
