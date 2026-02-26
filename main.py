"""
🤖 Autonomous Job Application Agent — Main Orchestrator

Run manually:   python main.py
Run scheduled:  python main.py --schedule
Test mode:      python main.py --dry-run
"""

import asyncio
import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

load_dotenv()

# Local agents
from agents.scraper import JobScraper
from agents.scorer import JobScorer
from agents.tailor import ResumeTailor
from agents.applier import AutoApplier
from agents.notifier import TelegramNotifier
from agents.database import init_db, upsert_job, is_seen, update_status, log_run

MAX_JOBS = int(os.getenv("MAX_JOBS_PER_RUN", "15"))


def load_resume() -> str:
    path = Path("data/resume.txt")
    if not path.exists():
        print("⚠️  data/resume.txt not found! Please add your resume as plain text.")
        return ""
    return path.read_text(encoding="utf-8")


def load_user_info() -> dict:
    path = Path("data/user_info.json")
    if not path.exists():
        print("⚠️  data/user_info.json not found!")
        return {}
    with open(path) as f:
        return json.load(f)


async def run_pipeline(dry_run: bool = False):
    print(f"\n{'='*60}")
    print(f"🤖 Job Agent Starting — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    resume = load_resume()
    user_info = load_user_info()

    if not resume:
        print("❌ Cannot proceed without resume. Exiting.")
        return

    stats = {"scraped": 0, "matched": 0, "applied": 0, "skipped": 0, "errors": 0}

    # ── Step 1: Scrape ───────────────────────────────────────────────────────
    print("\n🔍 Step 1: Scraping jobs...")
    scraper = JobScraper()
    all_jobs = scraper.fetch_all()
    stats["scraped"] = len(all_jobs)

    # Filter already-seen jobs
    new_jobs = [j for j in all_jobs if not is_seen(j["url"])]
    print(f"  📋 {len(new_jobs)} new (unseen) jobs to process")

    # ── Step 2: Score & Filter ───────────────────────────────────────────────
    print("\n🎯 Step 2: Scoring against your resume...")
    scorer = JobScorer(resume_text=resume)
    matched_jobs = scorer.filter_and_rank(new_jobs)
    stats["matched"] = len(matched_jobs)

    if not matched_jobs:
        print("  😔 No matching jobs found today. Try lowering MATCH_THRESHOLD.")
        return

    # Cap to daily limit
    to_process = matched_jobs[:MAX_JOBS]
    print(f"  📌 Processing top {len(to_process)} matches")

    # ── Step 3 & 4: Tailor + Notify/Apply ───────────────────────────────────
    print("\n✍️  Step 3: Tailoring applications...")
    tailor = ResumeTailor()
    notifier = TelegramNotifier()
    applier = AutoApplier(user_info)

    for i, job in enumerate(to_process, 1):
        print(f"\n  [{i}/{len(to_process)}] {job['title']} @ {job['company']}")
        print(f"          Score: {job['match_score']*100:.1f}% | {scorer.explain_match(job)}")

        if dry_run:
            print("          [DRY RUN] Skipping tailor + apply")
            upsert_job(job)
            continue

        try:
            # Generate tailored content
            cover_letter = tailor.generate_cover_letter(resume, job)
            resume_summary = tailor.tailor_resume_summary(resume, job)
            required_skills = tailor.extract_key_skills_from_jd(job)

            job["cover_letter"] = cover_letter
            job["resume_summary"] = resume_summary
            job["required_skills"] = required_skills

            # Save to DB
            upsert_job(job)

            # Send Telegram notification
            sent = notifier.send_job_card(job, cover_letter)
            if sent:
                print("          📱 Telegram notification sent")

            # Auto-apply if enabled
            auto_apply = os.getenv("AUTO_APPLY", "false").lower() == "true"
            if auto_apply:
                print("          🚀 Auto-applying...")
                result = await applier.apply(job, cover_letter)
                status = result.get("status", "error")
                update_status(job["id"], status)
                print(f"          Result: {status}")
                if status in ["submitted", "form_filled"]:
                    stats["applied"] += 1
                else:
                    stats["errors"] += 1
            else:
                update_status(job["id"], "notified")
                print("          ⏳ Waiting for your Telegram approval")

        except Exception as e:
            stats["errors"] += 1
            print(f"          ❌ Error: {e}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"✅ Pipeline Complete!")
    print(f"   Scraped:  {stats['scraped']} jobs")
    print(f"   Matched:  {stats['matched']} jobs")
    print(f"   Applied:  {stats['applied']} jobs")
    print(f"   Errors:   {stats['errors']}")
    print(f"{'='*60}\n")

    log_run(stats)
    notifier.send_summary(stats)


def main():
    parser = argparse.ArgumentParser(description="Autonomous Job Application Agent")
    parser.add_argument("--schedule", action="store_true", help="Run on daily schedule")
    parser.add_argument("--dry-run", action="store_true", help="Scrape and score only, no API calls")
    args = parser.parse_args()

    init_db()

    if args.schedule:
        print("⏰ Scheduler started — runs daily at 8:00 AM")
        print("   Press Ctrl+C to stop\n")
        scheduler = BlockingScheduler()
        scheduler.add_job(
            lambda: asyncio.run(run_pipeline(dry_run=args.dry_run)),
            "cron",
            hour=8, minute=0,
            id="daily_job_hunt"
        )
        # Also run immediately on start
        asyncio.run(run_pipeline(dry_run=args.dry_run))
        scheduler.start()
    else:
        asyncio.run(run_pipeline(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
