from utils.tools import fetch_companies_from_yfinance

payload = '{"mandate_id": 3, "additionalProp1": {"geography": "US", "sector": "technology", "industry": "software & IT services"}}'

# Tool is a Tool object; call its underlying function
result_json = fetch_companies_from_yfinance.func(payload)
print(result_json)