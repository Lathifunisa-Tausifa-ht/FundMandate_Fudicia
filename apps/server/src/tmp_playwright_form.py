import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        resp = await page.goto('https://www.screener.in/register/?next=/user/quick_ratios/%3Fnext%3D/company/TCS/consolidated/', wait_until='domcontentloaded', timeout=60000)
        title = await page.title()
        url = page.url
        print('status', resp.status if resp else None)
        print('url', url)
        print('title', title)
        print('body snippet:', (await page.content())[:800])
        await browser.close()

asyncio.run(test())
