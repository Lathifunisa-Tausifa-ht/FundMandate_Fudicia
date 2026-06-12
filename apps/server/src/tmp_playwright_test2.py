import asyncio
from playwright.async_api import async_playwright

cookies = {
    'csrftoken': 'kYbOsnWv0TSHmVCHZGXKuoQVOsj18gyO',
    'sessionid': 'te07z68trqqo8isyhx7zdmbtj49i54ms',
}

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        ck_list = [
            {'name': k, 'value': v, 'domain': 'screener.in', 'path': '/'}
            for k, v in cookies.items()
        ]
        await context.add_cookies(ck_list)
        page = await context.new_page()
        resp = await page.goto('https://www.screener.in/user/quick_ratios/?next=/company/TCS/consolidated/', wait_until='domcontentloaded', timeout=60000)
        await page.wait_for_timeout(5000)
        title = await page.title()
        url = page.url
        content = await page.content()
        print('status', resp.status if resp else None)
        print('url', url)
        print('title', title)
        print('login indicator', 'login' in title.lower() or 'register' in title.lower())
        print('snippet', content[:300])
        await browser.close()

asyncio.run(test())
