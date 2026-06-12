import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto('https://www.screener.in/register/?next=/user/quick_ratios/%3Fnext%3D/company/TCS/consolidated/', wait_until='domcontentloaded', timeout=60000)
        forms = await page.query_selector_all('form')
        print('forms', len(forms))
        for i, form in enumerate(forms, 1):
            action = await form.get_attribute('action')
            print('form', i, 'action', action)
            inputs = await form.query_selector_all('input')
            for inp in inputs:
                name = await inp.get_attribute('name')
                itype = await inp.get_attribute('type')
                value = await inp.get_attribute('value')
                print('  input', name, itype, value)
        await browser.close()

asyncio.run(test())
