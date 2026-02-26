"""
Agent 4: Auto Applier
Uses Playwright to automate form filling.
Supports: RemoteOK, Lever (used by 1000+ startups), Greenhouse, Workable

IMPORTANT SETTINGS:
- AUTO_APPLY=false → saves filled form screenshots for YOUR review before submitting
- AUTO_APPLY=true  → submits automatically (use carefully!)
"""

import asyncio
import os
import json
from pathlib import Path
from playwright.async_api import async_playwright, Page
from dotenv import load_dotenv

load_dotenv()

AUTO_APPLY = os.getenv("AUTO_APPLY", "false").lower() == "true"
SCREENSHOTS_DIR = Path("logs/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class AutoApplier:
    def __init__(self, user_info: dict):
        self.user = user_info
        self.auto_apply = AUTO_APPLY

    async def apply(self, job: dict, cover_letter: str) -> dict:
        """Route to the right applier based on the job URL."""
        url = job.get("url", "")
        result = {"job_id": job["id"], "status": "skipped", "error": None}

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,  # True for server deployment
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
                ctx = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await ctx.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)

                if "lever.co" in url:
                    result = await self._apply_lever(page, job, cover_letter)
                elif "greenhouse.io" in url:
                    result = await self._apply_greenhouse(page, job, cover_letter)
                elif "workable.com" in url:
                    result = await self._apply_workable(page, job, cover_letter)
                else:
                    result = await self._apply_generic(page, job, cover_letter)

                await browser.close()
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            print(f"  [Applier Error] {job['title']}: {e}")

        return result

    # ── Lever (most common ATS for startups) ────────────────────────────────
    async def _apply_lever(self, page: Page, job: dict, cover_letter: str) -> dict:
        try:
            await self._fill_if_exists(page, '[name="name"]', self.user["name"])
            await self._fill_if_exists(page, '[name="email"]', self.user["email"])
            await self._fill_if_exists(page, '[name="phone"]', self.user["phone"])
            await self._fill_if_exists(page, '[name="location"]', self.user["location"])
            await self._fill_if_exists(page, '[name="org"]', self.user.get("current_company", ""))
            await self._fill_if_exists(page, '[name="urls[LinkedIn]"]', self.user.get("linkedin", ""))
            await self._fill_if_exists(page, '[name="urls[GitHub]"]', self.user.get("github", ""))
            await self._fill_textarea(page, cover_letter)
            await self._upload_cv(page)
            return await self._finalize(page, job)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Greenhouse ───────────────────────────────────────────────────────────
    async def _apply_greenhouse(self, page: Page, job: dict, cover_letter: str) -> dict:
        try:
            await self._fill_if_exists(page, '#first_name', self.user["name"].split()[0])
            await self._fill_if_exists(page, '#last_name', self.user["name"].split()[-1])
            await self._fill_if_exists(page, '#email', self.user["email"])
            await self._fill_if_exists(page, '#phone', self.user["phone"])
            await self._fill_textarea(page, cover_letter)
            await self._upload_cv(page)
            return await self._finalize(page, job)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Workable ─────────────────────────────────────────────────────────────
    async def _apply_workable(self, page: Page, job: dict, cover_letter: str) -> dict:
        try:
            # Click apply button first
            apply_btn = page.locator('text=Apply for this job').first
            if await apply_btn.count() > 0:
                await apply_btn.click()
                await page.wait_for_load_state("networkidle")

            await self._fill_if_exists(page, '[name="firstname"]', self.user["name"].split()[0])
            await self._fill_if_exists(page, '[name="lastname"]', self.user["name"].split()[-1])
            await self._fill_if_exists(page, '[name="email"]', self.user["email"])
            await self._fill_if_exists(page, '[name="phone"]', self.user["phone"])
            await self._fill_textarea(page, cover_letter)
            await self._upload_cv(page)
            return await self._finalize(page, job)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Generic fallback ─────────────────────────────────────────────────────
    async def _apply_generic(self, page: Page, job: dict, cover_letter: str) -> dict:
        try:
            await self._fill_if_exists(page, 'input[type="text"][name*="name"]', self.user["name"])
            await self._fill_if_exists(page, 'input[type="email"]', self.user["email"])
            await self._fill_if_exists(page, 'input[type="tel"]', self.user["phone"])
            await self._fill_textarea(page, cover_letter)
            await self._upload_cv(page)
            return await self._finalize(page, job)
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Helpers ───────────────────────────────────────────────────────────────
    async def _fill_if_exists(self, page: Page, selector: str, value: str):
        try:
            loc = page.locator(selector).first
            if await loc.count() > 0 and value:
                await loc.fill(str(value))
        except:
            pass

    async def _fill_textarea(self, page: Page, cover_letter: str):
        try:
            ta = page.locator('textarea').first
            if await ta.count() > 0:
                await ta.fill(cover_letter)
        except:
            pass

    async def _upload_cv(self, page: Page):
        try:
            file_input = page.locator('input[type="file"]').first
            if await file_input.count() > 0:
                cv_path = self.user.get("cv_path", "data/resume.pdf")
                if Path(cv_path).exists():
                    await file_input.set_input_files(cv_path)
        except:
            pass

    async def _finalize(self, page: Page, job: dict) -> dict:
        screenshot_path = str(SCREENSHOTS_DIR / f"{job['id']}.png")
        await page.screenshot(path=screenshot_path, full_page=True)

        if self.auto_apply:
            # Try to find and click submit button
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Submit")',
                'button:has-text("Apply")',
                'button:has-text("Send Application")',
            ]
            for sel in submit_selectors:
                btn = page.locator(sel).first
                if await btn.count() > 0:
                    await btn.click()
                    await page.wait_for_timeout(2000)
                    final_screenshot = str(SCREENSHOTS_DIR / f"{job['id']}_submitted.png")
                    await page.screenshot(path=final_screenshot)
                    return {"status": "submitted", "screenshot": final_screenshot}
            return {"status": "form_filled", "screenshot": screenshot_path, "error": "Submit button not found"}
        else:
            return {"status": "review_needed", "screenshot": screenshot_path}
