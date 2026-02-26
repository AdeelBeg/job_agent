"""
SQLite Database Layer
Tracks all jobs: scraped, matched, applied, status.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = "data/jobs.db"
Path("data").mkdir(exist_ok=True)


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            location TEXT,
            url TEXT UNIQUE,
            source TEXT,
            description TEXT,
            salary REAL,
            match_score REAL,
            cover_letter TEXT,
            resume_summary TEXT,
            required_skills TEXT,
            status TEXT DEFAULT 'pending',
            applied_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT DEFAULT CURRENT_TIMESTAMP,
            scraped INTEGER,
            matched INTEGER,
            applied INTEGER,
            errors INTEGER
        );
    """)
    conn.commit()
    conn.close()
    print("  ✅ Database initialized")


def upsert_job(job: dict):
    conn = get_connection()
    conn.execute("""
        INSERT OR IGNORE INTO jobs
            (id, title, company, location, url, source, description, salary,
             match_score, cover_letter, resume_summary, required_skills, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
    """, (
        job["id"],
        job.get("title"),
        job.get("company"),
        job.get("location"),
        job.get("url"),
        job.get("source"),
        job.get("description"),
        job.get("salary"),
        job.get("match_score"),
        job.get("cover_letter"),
        job.get("resume_summary"),
        json.dumps(job.get("required_skills", [])),
    ))
    conn.commit()
    conn.close()


def is_seen(url: str) -> bool:
    conn = get_connection()
    cur = conn.execute("SELECT 1 FROM jobs WHERE url = ?", (url,))
    result = cur.fetchone() is not None
    conn.close()
    return result


def update_status(job_id: str, status: str):
    conn = get_connection()
    conn.execute(
        "UPDATE jobs SET status = ?, applied_at = ? WHERE id = ?",
        (status, datetime.now().isoformat(), job_id)
    )
    conn.commit()
    conn.close()


def get_all_jobs(status: str = None) -> list:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    if status:
        rows = conn.execute("SELECT * FROM jobs WHERE status = ? ORDER BY match_score DESC", (status,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_run(stats: dict):
    conn = get_connection()
    conn.execute("""
        INSERT INTO runs (scraped, matched, applied, errors)
        VALUES (?, ?, ?, ?)
    """, (stats.get("scraped", 0), stats.get("matched", 0),
          stats.get("applied", 0), stats.get("errors", 0)))
    conn.commit()
    conn.close()
