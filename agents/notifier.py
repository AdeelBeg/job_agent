"""
Telegram Bot Notifier
Sends you a card for each matched job with approve/skip buttons.
Approve → triggers auto-apply. Skip → marks as rejected.
"""

import os
import telebot
from telebot import types
from dotenv import load_dotenv

load_dotenv()


class TelegramNotifier:
    def __init__(self):
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if token:
            self.bot = telebot.TeleBot(token)
        else:
            self.bot = None
            print("  [Telegram] No bot token — notifications disabled")

    def send_job_card(self, job: dict, cover_letter: str = "") -> bool:
        if not self.bot or not self.chat_id:
            return False

        score_bar = self._score_bar(job.get("match_score", 0))
        salary_text = f"💰 {job.get('salary', 'Not listed')}" if job.get("salary") else ""

        message = f"""
🚀 *New Job Match!*

*{job['title']}*
🏢 {job['company']}
📍 {job.get('location', 'Remote')}
{salary_text}

{score_bar}
Match Score: *{job.get('match_score', 0)*100:.0f}%*

🔗 [View Job]({job['url']})

*Cover Letter Preview:*
_{cover_letter[:280].replace('_', ' ')}..._
"""
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("✅ Apply Now", callback_data=f"apply_{job['id']}"),
            types.InlineKeyboardButton("❌ Skip", callback_data=f"skip_{job['id']}"),
            types.InlineKeyboardButton("👀 Review", callback_data=f"review_{job['id']}"),
        )

        try:
            self.bot.send_message(
                self.chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=markup,
                disable_web_page_preview=False,
            )
            return True
        except Exception as e:
            print(f"  [Telegram] Send failed: {e}")
            return False

    def send_summary(self, stats: dict):
        if not self.bot or not self.chat_id:
            return
        msg = f"""
📊 *Daily Job Hunt Summary*

🔍 Jobs scraped: {stats.get('scraped', 0)}
🎯 Jobs matched: {stats.get('matched', 0)}
✅ Applied: {stats.get('applied', 0)}
❌ Skipped: {stats.get('skipped', 0)}
⚠️ Errors: {stats.get('errors', 0)}

_Next run: tomorrow 8:00 AM_
"""
        try:
            self.bot.send_message(self.chat_id, msg, parse_mode="Markdown")
        except:
            pass

    def send_error(self, message: str):
        if not self.bot or not self.chat_id:
            return
        try:
            self.bot.send_message(self.chat_id, f"⚠️ *Agent Error*\n{message}", parse_mode="Markdown")
        except:
            pass

    def _score_bar(self, score: float) -> str:
        filled = int(score * 10)
        return "🟩" * filled + "⬜" * (10 - filled)
