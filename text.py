import asyncio
from playwright.async_api import async_playwright


async def test():
    async with async_playwright() as p:
        # Opens a real visible Chrome window
        browser = await p.chromium.launch(headless=False, slow_mo=800)
        page = await browser.new_page()

        # Watch it navigate
        print("Opening RemoteOK...")
        await page.goto("https://remoteok.com/remote-ai-jobs")
        await page.wait_for_timeout(2000)

        # Watch it click the first job
        print("Clicking first job...")
        first_job = page.locator(".job").first
        await first_job.click()
        await page.wait_for_timeout(2000)

        print("Done! Closing in 3 seconds...")
        await page.wait_for_timeout(3000)
        await browser.close()


asyncio.run(test())
