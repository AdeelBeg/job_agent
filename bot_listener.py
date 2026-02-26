"""
Telegram Bot Listener
=====================
Runs 24/7 on Railway/Render and listens for button clicks from Telegram.

When you click ✅ Apply → triggers Playwright to fill and submit the form
When you click ❌ Skip  → marks job as skipped in database
When you click 👀 Review → sends you the job link

Deploy: Railway.app or Render.com (both free)
Local:  python bot_listener.py
"""

import os
import json
import asyncio
import logging
import traceback
from dotenv import load_dotenv
import telebot
from telebot import types

load_dotenv()

# ── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)

# ── Bot Init ──────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")


# ── Helpers ───────────────────────────────────────────────────────────────────
def load_user_info() -> dict:
    path = "data/user_info.json"
    if not os.path.exists(path):
        log.error("data/user_info.json not found")
        return {}
    with open(path) as f:
        return json.load(f)


def get_job_by_id(job_id: str) -> dict | None:
    """Fetch job from SQLite by ID."""
    try:
        from agents.database import get_all_jobs
        jobs = get_all_jobs()
        return next((j for j in jobs if j["id"] == job_id), None)
    except Exception as e:
        log.error(f"DB error fetching job {job_id}: {e}")
        return None


def send_message(chat_id: str, text: str, reply_markup=None):
    """Safe message sender with error handling."""
    try:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)
    except Exception as e:
        log.error(f"Failed to send message: {e}")


# ── Button Click Handler ───────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: True)
def handle_button_click(call):
    """Handles all inline button clicks from Telegram job cards."""
    try:
        log.info(f"Button clicked: {call.data}")

        # Parse action and job_id from callback data
        # Format: "apply_abc123" / "skip_abc123" / "review_abc123"
        parts = call.data.split("_", 1)
        if len(parts) != 2:
            bot.answer_callback_query(call.id, "Invalid action")
            return

        action, job_id = parts
        chat_id = call.message.chat.id

        # Fetch job from database
        job = get_job_by_id(job_id)
        if not job:
            bot.answer_callback_query(call.id, "⚠️ Job not found in database")
            send_message(chat_id, f"⚠️ Could not find job `{job_id}` in database.\nIt may have been deleted.")
            return

        title = job.get("title", "Unknown Role")
        company = job.get("company", "Unknown Company")

        # ── Handle each action ────────────────────────────────────────────────
        if action == "apply":
            handle_apply(call, job, chat_id, title, company)

        elif action == "skip":
            handle_skip(call, job, chat_id, title, company)

        elif action == "review":
            handle_review(call, job, chat_id, title, company)

        else:
            bot.answer_callback_query(call.id, "Unknown action")

    except Exception as e:
        log.error(f"Error handling button click: {traceback.format_exc()}")
        try:
            bot.answer_callback_query(call.id, "❌ Error occurred")
            send_message(call.message.chat.id, f"❌ *Error:* {str(e)[:200]}")
        except:
            pass


def handle_apply(call, job: dict, chat_id, title: str, company: str):
    """Handle Apply button — triggers Playwright form filler."""
    from agents.applier import AutoApplier
    from agents.database import update_status

    bot.answer_callback_query(call.id, "🚀 Starting application...")

    # Edit the original message to show processing state
    try:
        bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=None  # Remove buttons while processing
        )
    except:
        pass

    send_message(chat_id, f"⏳ *Applying to {title} @ {company}...*\nFilling form with Playwright, please wait.")

    try:
        user_info = load_user_info()
        if not user_info:
            send_message(chat_id, "❌ *Error:* `data/user_info.json` not found on the server.")
            return

        cover_letter = job.get("cover_letter", "")
        if not cover_letter:
            send_message(chat_id, "⚠️ No cover letter found for this job. Proceeding with blank cover letter.")

        # Run async Playwright applier
        applier = AutoApplier(user_info)
        result = asyncio.run(applier.apply(job, cover_letter))

        status = result.get("status", "error")
        error = result.get("error", "")
        screenshot = result.get("screenshot", "")

        if status == "submitted":
            update_status(job["id"], "submitted")
            send_message(
                chat_id,
                f"✅ *Successfully Applied!*\n\n"
                f"*Role:* {title}\n"
                f"*Company:* {company}\n"
                f"*Link:* {job.get('url', 'N/A')}\n\n"
                f"_Screenshot saved in GitHub Actions artifacts._"
            )
            log.info(f"Applied: {title} @ {company}")

        elif status == "form_filled":
            update_status(job["id"], "review_needed")
            send_message(
                chat_id,
                f"📋 *Form Filled — Submit Manually*\n\n"
                f"*Role:* {title}\n"
                f"*Company:* {company}\n\n"
                f"The form was filled but the submit button could not be found automatically.\n"
                f"🔗 Please submit manually: {job.get('url', 'N/A')}"
            )
            log.warning(f"Form filled but not submitted: {title} @ {company}")

        elif status == "review_needed":
            update_status(job["id"], "review_needed")
            send_message(
                chat_id,
                f"👀 *Needs Manual Review*\n\n"
                f"*Role:* {title}\n"
                f"*Link:* {job.get('url', 'N/A')}\n\n"
                f"AUTO\\_APPLY is disabled. Form was prepared but not submitted."
            )

        else:
            update_status(job["id"], "error")
            send_message(
                chat_id,
                f"❌ *Application Failed*\n\n"
                f"*Role:* {title}\n"
                f"*Error:* {error[:200] if error else 'Unknown error'}\n\n"
                f"Try applying manually: {job.get('url', 'N/A')}"
            )
            log.error(f"Apply failed: {title} @ {company} — {error}")

    except Exception as e:
        update_status(job["id"], "error")
        send_message(
            chat_id,
            f"❌ *Unexpected Error*\n\n"
            f"*Role:* {title}\n"
            f"*Error:* {str(e)[:300]}\n\n"
            f"Apply manually: {job.get('url', 'N/A')}"
        )
        log.error(f"Unexpected error in handle_apply: {traceback.format_exc()}")


def handle_skip(call, job: dict, chat_id, title: str, company: str):
    """Handle Skip button — marks job as skipped."""
    from agents.database import update_status

    bot.answer_callback_query(call.id, "⏭️ Skipped")
    update_status(job["id"], "skipped")

    # Remove buttons from original message
    try:
        bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=call.message.message_id,
            reply_markup=None
        )
    except:
        pass

    send_message(chat_id, f"⏭️ *Skipped*\n_{title} @ {company}_")
    log.info(f"Skipped: {title} @ {company}")


def handle_review(call, job: dict, chat_id, title: str, company: str):
    """Handle Review button — sends job details and link."""
    bot.answer_callback_query(call.id, "Here are the details 👇")

    cover_letter = job.get("cover_letter", "Not generated")
    skills = job.get("required_skills", "[]")

    try:
        skill_list = json.loads(skills) if isinstance(skills, str) else skills
        skills_text = ", ".join(skill_list[:8]) if skill_list else "N/A"
    except:
        skills_text = "N/A"

    message = (
        f"📋 *{title}*\n"
        f"🏢 {company}\n"
        f"📍 {job.get('location', 'Remote')}\n"
        f"🎯 Match: *{job.get('match_score', 0)*100:.0f}%*\n"
        f"🔗 {job.get('url', 'N/A')}\n\n"
        f"*Required Skills:*\n{skills_text}\n\n"
        f"*Cover Letter:*\n{cover_letter[:600]}..."
    )

    # Show action buttons again
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Apply Now", callback_data=f"apply_{job['id']}"),
        types.InlineKeyboardButton("❌ Skip", callback_data=f"skip_{job['id']}"),
    )

    send_message(chat_id, message, reply_markup=markup)
    log.info(f"Reviewed: {title} @ {company}")


# ── Slash Commands ─────────────────────────────────────────────────────────────
@bot.message_handler(commands=["start", "help"])
def handle_start(message):
    send_message(
        message.chat.id,
        "🤖 *Job Agent Bot*\n\n"
        "I apply to jobs for you automatically.\n\n"
        "*Commands:*\n"
        "/status — Show application stats\n"
        "/pending — List jobs waiting for your approval\n"
        "/applied — List submitted applications\n"
        "/help — Show this message"
    )


@bot.message_handler(commands=["status"])
def handle_status(message):
    try:
        from agents.database import get_all_jobs
        jobs = get_all_jobs()

        total = len(jobs)
        applied = len([j for j in jobs if j["status"] == "submitted"])
        pending = len([j for j in jobs if j["status"] == "notified"])
        skipped = len([j for j in jobs if j["status"] == "skipped"])
        errors = len([j for j in jobs if j["status"] == "error"])

        send_message(
            message.chat.id,
            f"📊 *Application Stats*\n\n"
            f"📋 Total found: *{total}*\n"
            f"✅ Applied: *{applied}*\n"
            f"⏳ Pending approval: *{pending}*\n"
            f"⏭️ Skipped: *{skipped}*\n"
            f"❌ Errors: *{errors}*"
        )
    except Exception as e:
        send_message(message.chat.id, f"❌ Error fetching stats: {e}")


@bot.message_handler(commands=["pending"])
def handle_pending(message):
    try:
        from agents.database import get_all_jobs
        pending_jobs = [j for j in get_all_jobs() if j["status"] == "notified"]

        if not pending_jobs:
            send_message(message.chat.id, "✅ No pending jobs — all caught up!")
            return

        send_message(message.chat.id, f"⏳ *{len(pending_jobs)} Pending Jobs:*")

        for job in pending_jobs[:10]:  # Max 10
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("✅ Apply", callback_data=f"apply_{job['id']}"),
                types.InlineKeyboardButton("❌ Skip", callback_data=f"skip_{job['id']}"),
            )
            send_message(
                message.chat.id,
                f"*{job['title']}* @ {job['company']}\n"
                f"Score: {job.get('match_score', 0)*100:.0f}% | {job.get('source', 'unknown')}\n"
                f"🔗 {job.get('url', 'N/A')}",
                reply_markup=markup
            )
    except Exception as e:
        send_message(message.chat.id, f"❌ Error: {e}")


@bot.message_handler(commands=["applied"])
def handle_applied(message):
    try:
        from agents.database import get_all_jobs
        applied_jobs = [j for j in get_all_jobs() if j["status"] == "submitted"]

        if not applied_jobs:
            send_message(message.chat.id, "📭 No submitted applications yet.")
            return

        text = f"✅ *{len(applied_jobs)} Submitted Applications:*\n\n"
        for job in applied_jobs[:15]:
            text += f"• *{job['title']}* @ {job['company']}\n"

        send_message(message.chat.id, text)
    except Exception as e:
        send_message(message.chat.id, f"❌ Error: {e}")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("=" * 50)
    log.info("🤖 Job Agent Bot Listener Started")
    log.info("Waiting for Telegram button clicks...")
    log.info("Commands: /start /status /pending /applied")
    log.info("=" * 50)

    # Send startup notification
    if CHAT_ID:
        try:
            bot.send_message(
                CHAT_ID,
                "✅ *Bot Listener Started*\n_Ready to process your job applications._",
                parse_mode="Markdown"
            )
        except:
            pass

    # Start polling — runs forever
    bot.infinity_polling(timeout=60, long_polling_timeout=30)
