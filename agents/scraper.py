"""
Agent 1: Job Scraper
Pulls jobs from RemoteOK RSS, Adzuna API, and We Work Remotely.
All free sources, no scraping restrictions.
"""

import feedparser
import requests
import hashlib
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()


def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:10]


class JobScraper:
    def __init__(self):
        self.adzuna_id = os.getenv("ADZUNA_APP_ID")
        self.adzuna_key = os.getenv("ADZUNA_APP_KEY")
        self.country = os.getenv("ADZUNA_COUNTRY", "gb")
        self.keywords = [k.strip() for k in os.getenv("JOB_KEYWORDS", "ai engineer").split(",")]

    # ─── Source 1: RemoteOK RSS (completely free) ───────────────────────────
    def fetch_remoteok(self) -> list:
        jobs = []
        tags = ["ai", "machine-learning", "python", "llm", "data-science"]
        for tag in tags:
            try:
                feed = feedparser.parse(f"https://remoteok.com/remote-{tag}-jobs.rss")
                for e in feed.entries:
                    jobs.append({
                        "id": make_id(e.link),
                        "title": e.get("title", ""),
                        "company": e.get("author", "Unknown"),
                        "description": BeautifulSoup(e.get("summary", ""), "lxml").get_text(),
                        "url": e.link,
                        "location": "Remote",
                        "source": "remoteok",
                    })
            except Exception as ex:
                print(f"[RemoteOK] Error for tag {tag}: {ex}")
        return jobs

    # ─── Source 2: We Work Remotely RSS (free) ──────────────────────────────
    def fetch_weworkremotely(self) -> list:
        jobs = []
        feeds = [
            "https://weworkremotely.com/categories/remote-programming-jobs.rss",
            "https://weworkremotely.com/categories/remote-data-science-jobs.rss",
        ]
        for url in feeds:
            try:
                feed = feedparser.parse(url)
                for e in feed.entries:
                    jobs.append({
                        "id": make_id(e.link),
                        "title": e.get("title", ""),
                        "company": e.get("author", "Unknown"),
                        "description": BeautifulSoup(e.get("summary", ""), "lxml").get_text(),
                        "url": e.link,
                        "location": "Remote",
                        "source": "weworkremotely",
                    })
            except Exception as ex:
                print(f"[WWR] Error: {ex}")
        return jobs

    # ─── Source 3: Adzuna API (free tier = 250 calls/month) ─────────────────
    def fetch_adzuna(self) -> list:
        if not self.adzuna_id or not self.adzuna_key:
            print("[Adzuna] No credentials — skipping.")
            return []
        jobs = []
        for keyword in self.keywords:
            try:
                url = f"https://api.adzuna.com/v1/api/jobs/{self.country}/search/1"
                params = {
                    "app_id": self.adzuna_id,
                    "app_key": self.adzuna_key,
                    "what": keyword,
                    "results_per_page": 20,
                    "content-type": "application/json",
                }
                r = requests.get(url, params=params, timeout=10)
                for item in r.json().get("results", []):
                    jobs.append({
                        "id": make_id(item.get("redirect_url", "")),
                        "title": item.get("title", ""),
                        "company": item.get("company", {}).get("display_name", "Unknown"),
                        "description": item.get("description", ""),
                        "url": item.get("redirect_url", ""),
                        "location": item.get("location", {}).get("display_name", ""),
                        "salary": item.get("salary_min"),
                        "source": "adzuna",
                    })
            except Exception as ex:
                print(f"[Adzuna] Error for '{keyword}': {ex}")
        return jobs

    # ─── Source 4: GitHub Jobs via public search ─────────────────────────────
    def fetch_github_careers(self) -> list:
        """Scrape public GitHub job board - no auth needed"""
        jobs = []
        try:
            url = "https://jobs.github.com/positions.json?description=machine+learning&location=remote"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                for item in r.json():
                    jobs.append({
                        "id": make_id(item.get("url", "")),
                        "title": item.get("title", ""),
                        "company": item.get("company", "Unknown"),
                        "description": BeautifulSoup(item.get("description", ""), "lxml").get_text(),
                        "url": item.get("url", ""),
                        "location": item.get("location", ""),
                        "source": "github",
                    })
        except Exception as ex:
            print(f"[GitHub] Error: {ex}")
        return jobs

    # ─── Main fetch with deduplication ──────────────────────────────────────
    def fetch_all(self) -> list:
        print("  → Fetching RemoteOK...")
        jobs = self.fetch_remoteok()
        print(f"     {len(jobs)} found")

        print("  → Fetching We Work Remotely...")
        wwr = self.fetch_weworkremotely()
        print(f"     {len(wwr)} found")
        jobs += wwr

        print("  → Fetching Adzuna...")
        adzuna = self.fetch_adzuna()
        print(f"     {len(adzuna)} found")
        jobs += adzuna

        # Deduplicate by URL
        seen = set()
        unique = []
        for j in jobs:
            if j["url"] not in seen and j["url"]:
                seen.add(j["url"])
                unique.append(j)

        print(f"  ✅ Total unique jobs: {len(unique)}")
        return unique
