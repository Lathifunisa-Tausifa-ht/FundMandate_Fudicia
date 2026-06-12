"""Screener.in company profile crawler using crawl4ai.

This module uses crawl4ai's AsyncWebCrawler to fetch a Screener.in company page
and then extracts only the company name and key metrics from the profile.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urljoin
import requests

try:
    # Playwright is optional; if not installed we'll fallback
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    async_playwright = None  # type: ignore
    PLAYWRIGHT_AVAILABLE = False

from bs4 import BeautifulSoup

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
except ImportError as exc:
    raise ImportError(
        "crawl4ai is required for screener_crawler.py. "
        "Install crawl4ai in the server environment before using this module."
    ) from exc

BASE_SCREENER_URL = "https://www.screener.in/company"


def _normalize_symbol(symbol: str) -> str:
    if not symbol:
        raise ValueError("Company symbol must be provided")

    cleaned = str(symbol).strip().upper()
    cleaned = re.sub(r"[^A-Z0-9]", "", cleaned)
    if not cleaned:
        raise ValueError("Company symbol must contain alphanumeric characters")
    return cleaned


def _build_screener_url(symbol: str, consolidated: bool = True) -> str:
    symbol = _normalize_symbol(symbol)
    suffix = "consolidated/" if consolidated else ""
    return f"{BASE_SCREENER_URL}/{symbol}/{suffix}"


def _build_quick_ratios_url(symbol: str, consolidated: bool = True) -> str:
    symbol = _normalize_symbol(symbol)
    suffix = "consolidated/" if consolidated else ""
    return f"https://www.screener.in/user/quick_ratios/?next=/company/{symbol}/{suffix}"


METRIC_LABEL_CANONICAL: Dict[str, str] = {
    "Price to Earning": "Price to Earnings",
    "Price to Earnings": "Price to Earnings",
    "Dividend yield": "Dividend Yield",
    "Dividend Yield": "Dividend Yield",
    "Debt to equity": "Debt to Equity",
    "Debt to Equity": "Debt to Equity",
    "Return on equity": "ROE",
    "ROE": "ROE",
    "EVEBITDA": "EV/EBITDA",
    "EV/EBITDA": "EV/EBITDA",
    "Return over 6months": "Return over 6 Months",
    "Return over 5years": "Return over 5 Years",
    "Profit Var 5Yrs": "Profit Var 5 Yrs",
    "Profit Var 3Yrs": "Profit Var 3 Yrs",
    "Market Cap": "Market Cap",
    "Current Price": "Current Price",
    "High / Low": "High / Low",
    "Book Value": "Book Value",
    "Dividend Yield": "Dividend Yield",
    "ROCE": "ROCE",
    "ROE": "ROE",
    "Face Value": "Face Value",
}

DESIRED_MAIN_PAGE_METRICS: List[str] = [
    "Market Cap",
    "Current Price",
    "High / Low",
    "Stock P/E",
    "Book Value",
    "Dividend Yield",
    "ROCE",
    "ROE",
    "Face Value",
]

DESIRED_QUICK_PAGE_METRICS: List[str] = [
    "Debt to equity",
    "EVEBITDA",
    "Return over 6months",
    "Profit Var 5Yrs",
    "Return over 5years",
    "Profit growth",
    "Price to book value",
    "Return on assets",
]

METRIC_ALIAS_MAP: Dict[str, List[str]] = {
    "Stock P/E": ["Price to Earnings", "Price to Earning"],
    "Price to Earnings": ["Stock P/E", "Price to Earning"],
    "Dividend Yield": ["Dividend yield"],
    "Debt to Equity": ["Debt to equity"],
    "ROE": ["Return on equity"],
    "EV/EBITDA": ["EVEBITDA"],
    "Return over 6 Months": ["Return over 6months"],
    "Return over 5 Years": ["Return over 5years"],
    "Profit Var 5 Yrs": ["Profit Var 5Yrs"],
}

QUICK_RATIO_ANCHOR_PART = "/user/quick_ratios/"


def _normalize_metric_label(label: str) -> str:
    normalized = re.sub(r"\s+", " ", label.strip())
    if not normalized:
        return normalized
    return METRIC_LABEL_CANONICAL.get(normalized, normalized)


def _expand_metric_aliases(metrics: Dict[str, str]) -> Dict[str, str]:
    expanded = dict(metrics)
    for name, value in list(metrics.items()):
        for alias in METRIC_ALIAS_MAP.get(name, []):
            if alias not in expanded:
                expanded[alias] = value
    return expanded


def _extract_main_page_metrics(soup: BeautifulSoup) -> Dict[str, str]:
    raw_metrics: Dict[str, str] = {}
    for li in soup.select("div.company-ratios li"):
        label_node = li.select_one("span.name")
        value_node = li.select_one("span.value, span.nowrap.value")
        if not label_node or value_node is None:
            continue

        label = _normalize_metric_label(label_node.get_text(strip=True))
        value = value_node.get_text(" ", strip=True)
        if label and value:
            raw_metrics[label] = value

    selected: Dict[str, str] = {}
    for wanted in DESIRED_MAIN_PAGE_METRICS:
        if wanted in raw_metrics:
            selected[wanted] = raw_metrics[wanted]
        else:
            for candidate in raw_metrics:
                if candidate.lower() == wanted.lower():
                    selected[wanted] = raw_metrics[candidate]
                    break
    return selected


def _extract_quick_page_metrics(soup: BeautifulSoup) -> Dict[str, str]:
    raw_metrics: Dict[str, str] = {}
    
    # Try to extract from label > span structure
    for label in soup.select("label"):
        label_text = label.get_text(" ", strip=True)
        if not label_text:
            continue
        
        # Look for span with value within or after label
        value_span = label.select_one("span")
        if value_span:
            value_text = value_span.get_text(" ", strip=True)
            # Remove the label text from value if it's duplicated
            if value_text.startswith(label_text):
                value_text = value_text[len(label_text):].strip(" :–—")
            
            label_norm = _normalize_metric_label(label_text)
            for wanted in DESIRED_QUICK_PAGE_METRICS:
                if label_norm.lower() == wanted.lower() and value_text:
                    raw_metrics[wanted] = value_text
                    break
    
    # Try to extract from table rows (label-value pairs)
    if not raw_metrics:
        for row in soup.select("tr"):
            cells = row.select("td, th")
            if len(cells) >= 2:
                label_text = cells[0].get_text(" ", strip=True)
                value_text = cells[1].get_text(" ", strip=True)
                label = _normalize_metric_label(label_text)
                
                for wanted in DESIRED_QUICK_PAGE_METRICS:
                    if label.lower() == wanted.lower() and value_text:
                        raw_metrics[wanted] = value_text
                        break
    
    # Fallback: search for metric names in divs/spans with nearby values
    if not raw_metrics:
        for element in soup.select("div, span, li"):
            text = element.get_text(" ", strip=True)
            if not text or len(text) > 200:
                continue
            
            for wanted in DESIRED_QUICK_PAGE_METRICS:
                if wanted.lower() in text.lower():
                    # Extract value after the metric name
                    parts = re.split(rf"{re.escape(wanted)}\s*[:–—]*\s*", text, flags=re.IGNORECASE)
                    if len(parts) > 1:
                        value = parts[1].strip(" :–—\n\r\t")
                        # Clean up value - take first word/number if too long
                        value_clean = value.split()[0] if value.split() else value
                        if value_clean and len(value_clean) < 50:
                            raw_metrics[wanted] = value_clean
    
    return raw_metrics


def _is_login_gate(soup: BeautifulSoup, status_code: Optional[int]) -> bool:
    if status_code in {301, 302, 303, 307, 308}:
        return True

    title = soup.title.get_text(strip=True) if soup.title else ""
    if re.search(r"\b(register|login|sign in|sign up)\b", title, re.I):
        return True

    if soup.find("form", attrs={"action": re.compile(r"/login|/register|/user/quick_ratios", re.I)}):
        return True

    if soup.find(string=re.compile(r"register|login|sign in|sign up", re.I)):
        return True

    return False


def _find_edit_ratios_url(soup: BeautifulSoup) -> Optional[str]:
    for anchor in soup.select("a[href]"):
        href = anchor.get("href")
        if href and QUICK_RATIO_ANCHOR_PART in href:
            return urljoin(BASE_SCREENER_URL, href)
    return None

















def _build_login_url(symbol: str, consolidated: bool = True) -> str:
    symbol = _normalize_symbol(symbol)
    suffix = "consolidated/" if consolidated else ""
    next_path = f"/user/quick_ratios/?next=/company/{symbol}/{suffix}"
    return f"https://www.screener.in/login/?next={quote(next_path, safe='')}"


async def _playwright_fetch_html_with_cookies(
    url: str,
    cookies: Dict[str, str],
    headless: bool,
    delay: int,
) -> Tuple[str, Optional[int]]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        ck_list = [
            {"name": k, "value": v, "domain": "screener.in", "path": "/"}
            for k, v in cookies.items()
        ]
        if ck_list:
            await context.add_cookies(ck_list)
        page = await context.new_page()
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(delay * 1000)
        html = await page.content()
        status = resp.status if resp else None
        await browser.close()
        return html, status


async def _playwright_login_and_fetch_html(
    symbol: str,
    credentials: Dict[str, str],
    headless: bool,
    delay: int,
    consolidated: bool,
) -> Tuple[str, Optional[int]]:
    login_url = _build_login_url(symbol, consolidated=consolidated)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_selector('form', timeout=15000)
        await page.fill('input[name="username"]', credentials.get("username", ""))
        await page.fill('input[name="password"]', credentials.get("password", ""))

        submit = page.locator('button[type="submit"]')
        if await submit.count() > 0:
            async with page.expect_navigation(wait_until="domcontentloaded", timeout=60000) as nav_info:
                await submit.first.click()
            nav_response = await nav_info.value
        else:
            await page.press('input[name="password"]', 'Enter')
            nav_response = await page.wait_for_navigation(wait_until="domcontentloaded", timeout=60000)

        # Wait for the page content to render after login, especially the quick ratios area.
        try:
            await page.wait_for_selector('div.company-ratios', timeout=15000)
        except Exception:
            await page.wait_for_timeout(delay * 1000)

        html = await page.content()
        status = nav_response.status if nav_response else None
        await browser.close()
        return html, status


def parse_screener_profile_html(html: str, company_url: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    company_name = soup.find("h1")
    extracted: Dict[str, Any] = {
        "company_url": company_url,
        "company_name": company_name.get_text(strip=True) if company_name else None,
        "main_page_metrics": _extract_main_page_metrics(soup),
    }
    return extracted


async def crawl_screener_company_profile_async(
    symbol: str,
    consolidated: bool = True,
    headless: bool = True,
    delay: int = 2,
    cookies: Optional[Dict[str, str]] = None,
    login_credentials: Optional[Dict[str, str]] = None,
    use_playwright: bool = True,
) -> Dict[str, Any]:
    """Crawl Screener.in and return extracted company profile data asynchronously."""
    profile_url = _build_screener_url(symbol, consolidated=consolidated)
    browser_config = BrowserConfig(headless=headless, verbose=False)

    # Initialize variables for safe return even if an error occurs
    edit_ratios_url: str = ""
    quick_title: Optional[str] = None
    quick_status: Optional[int] = None
    quick_gate: bool = False
    quick_metrics: Dict[str, str] = {}
    quick_error: Optional[str] = None
    main_soup = None
    main_metrics: Dict[str, str] = {}

    async with AsyncWebCrawler(config=browser_config) as crawler:
        main_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            keep_attrs=["id", "class"],
            keep_data_attributes=True,
            delay_before_return_html=delay,
            wait_for="div.company-ratios",
            wait_for_timeout=12000,
        )
        main_result = await crawler.arun(url=profile_url, config=main_config)

        if not getattr(main_result, "success", False):
            return {
                "success": False,
                "error": getattr(main_result, "error", "Unknown crawl error"),
                "company_url": profile_url,
            }

        main_html = getattr(main_result, "html", None) or getattr(main_result, "cleaned_html", None) or getattr(main_result, "text", "")
        main_soup = BeautifulSoup(main_html, "html.parser")
        main_metrics = _extract_main_page_metrics(main_soup)
        edit_ratios_url = _find_edit_ratios_url(main_soup) or _build_quick_ratios_url(symbol, consolidated=consolidated)

        quick_html = ""
        quick_status: Optional[int] = None

        # If cookies are provided, try Playwright first (if available), then requests.
        if cookies:
            if use_playwright and PLAYWRIGHT_AVAILABLE:
                try:
                    quick_html, quick_status = await _playwright_fetch_html_with_cookies(
                        edit_ratios_url,
                        cookies,
                        headless=headless,
                        delay=delay,
                    )
                except Exception:
                    quick_html = ""
                    quick_status = None

            # Fallback to requests session if Playwright not used or failed
            if not quick_html:
                try:
                    def _fetch_with_cookies(url: str, ck: Dict[str, str]):
                        sess = requests.Session()
                        # attach provided cookies
                        for k, v in ck.items():
                            sess.cookies.set(k, v)
                        headers = {"User-Agent": "Mozilla/5.0 (compatible)"}
                        resp = sess.get(url, headers=headers, timeout=20)
                        return resp

                    resp = await asyncio.to_thread(_fetch_with_cookies, edit_ratios_url, cookies)
                    quick_html = resp.text or ""
                    quick_status = resp.status_code
                except Exception:
                    quick_html = ""
                    quick_status = None

            # If cookies fetched a login gate, try credential-based login if available.
            if login_credentials and PLAYWRIGHT_AVAILABLE:
                quick_soup = BeautifulSoup(quick_html, "html.parser") if quick_html else None
                if quick_soup and _is_login_gate(quick_soup, quick_status):
                    try:
                        quick_html, quick_status = await _playwright_login_and_fetch_html(
                            symbol=symbol,
                            credentials=login_credentials,
                            headless=headless,
                            delay=delay,
                            consolidated=consolidated,
                        )
                    except Exception:
                        quick_html = quick_html or ""
                        quick_status = quick_status

        # If login credentials are provided and quick ratios were not fetched at all, try Playwright login.
        if not quick_html and login_credentials and PLAYWRIGHT_AVAILABLE:
            try:
                quick_html, quick_status = await _playwright_login_and_fetch_html(
                    symbol=symbol,
                    credentials=login_credentials,
                    headless=headless,
                    delay=delay,
                    consolidated=consolidated,
                )
            except Exception:
                quick_html = quick_html or ""
                quick_status = quick_status

        # Fallback to crawler if we didn't get HTML from requests
        if not quick_html:
            quick_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                keep_attrs=["id", "class"],
                keep_data_attributes=True,
                delay_before_return_html=delay,
                wait_for="body",
                wait_for_timeout=12000,
            )
            quick_result = await crawler.arun(url=edit_ratios_url, config=quick_config)
            quick_html = getattr(quick_result, "html", None) or getattr(quick_result, "cleaned_html", None) or ""
            quick_status = quick_status or getattr(quick_result, "status_code", None)

        quick_soup = BeautifulSoup(quick_html, "html.parser")
        quick_title = quick_soup.title.get_text(strip=True) if quick_soup.title else None
        quick_gate = _is_login_gate(quick_soup, quick_status)
        quick_metrics = {} if quick_gate else _extract_quick_page_metrics(quick_soup)
        quick_error = (
            "Login or registration required to access quick ratios"
            if quick_gate
            else None
        )

    return {
        "success": True,
        "company_url": profile_url,
        "quick_ratios_url": edit_ratios_url,
        "quick_ratios_page_title": quick_title,
        "quick_ratios_page_status": quick_status,
        "quick_ratios_requires_login": quick_gate,
        "quick_ratios_error": quick_error,
        "profile": {
            "company_url": profile_url,
            "company_name": main_soup.find("h1").get_text(strip=True) if main_soup.find("h1") else None,
            "main_page_metrics": main_metrics,
            "quick_page_metrics": quick_metrics,
        },
    }


def crawl_screener_company_profile(
    symbol: str,
    consolidated: bool = True,
    headless: bool = True,
    delay: int = 2,
    cookies: Optional[Dict[str, str]] = None,
    login_credentials: Optional[Dict[str, str]] = None,
    use_playwright: bool = True,
) -> Dict[str, Any]:
    """Synchronous wrapper around the async Screener.in crawler."""
    return asyncio.run(
        crawl_screener_company_profile_async(
            symbol=symbol,
            consolidated=consolidated,
            headless=headless,
            delay=delay,
            cookies=cookies,
            login_credentials=login_credentials,
            use_playwright=use_playwright,
        )
    )


if __name__ == "__main__":
    sample_symbol = "TCS"
    # Add your credentials here if needed for login testing
    sample_credentials = {
        "username": "your_username_here",
        "password": "your_password_here",
    }
    # Or add session cookies
    sample_cookies = {
        "csrftoken": "kYbOsnWv0TSHmVCHZGXKuoQVOsj18gyO",
        "sessionid": "te07z68trqqo8isyhx7zdmbtj49i54ms",
    }
    print("Crawling Screener.in profile for", sample_symbol)
    # Uncomment to test with credentials:
    # result = crawl_screener_company_profile(sample_symbol, login_credentials=sample_credentials)
    # Or test with cookies:
    result = crawl_screener_company_profile(sample_symbol, cookies=sample_cookies)
    print(result)
