import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  # Set this to Supabase URL


def get_connection():
    if DATABASE_URL:
        # Cloud PostgreSQL (Supabase)
        import psycopg2

        return psycopg2.connect(DATABASE_URL), "postgres"
    else:
        # Local SQLite fallback
        import sqlite3
        from pathlib import Path

        Path("data").mkdir(exist_ok=True)
        return sqlite3.connect("data/jobs.db"), "sqlite"


def init_db():
    conn, db_type = get_connection()
    cur = conn.cursor()

    if db_type == "postgres":
        cur.execute(
            """
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            );
            CREATE TABLE IF NOT EXISTS runs (
                id SERIAL PRIMARY KEY,
                run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                scraped INTEGER,
                matched INTEGER,
                applied INTEGER,
                errors INTEGER
            );
        """
        )
    else:
        cur.executescript(
            """
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
        """
        )

    conn.commit()
    conn.close()
    print("  ✅ Database initialized")


def upsert_job(job: dict):
    conn, db_type = get_connection()
    cur = conn.cursor()

    if db_type == "postgres":
        cur.execute(
            """
            INSERT INTO jobs
                (id, title, company, location, url, source, description, salary,
                 match_score, cover_letter, resume_summary, required_skills, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')
            ON CONFLICT (id) DO NOTHING
        """,
            (
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
            ),
        )
    else:
        cur.execute(
            """
            INSERT OR IGNORE INTO jobs
                (id, title, company, location, url, source, description, salary,
                 match_score, cover_letter, resume_summary, required_skills, status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'pending')
        """,
            (
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
            ),
        )

    conn.commit()
    conn.close()


def is_seen(url: str) -> bool:
    conn, db_type = get_connection()
    cur = conn.cursor()
    placeholder = "%s" if db_type == "postgres" else "?"
    cur.execute(f"SELECT 1 FROM jobs WHERE url = {placeholder}", (url,))
    result = cur.fetchone() is not None
    conn.close()
    return result


def update_status(job_id: str, status: str):
    conn, db_type = get_connection()
    cur = conn.cursor()
    placeholder = "%s" if db_type == "postgres" else "?"
    cur.execute(
        f"UPDATE jobs SET status = {placeholder}, applied_at = {placeholder} WHERE id = {placeholder}",
        (status, datetime.now().isoformat(), job_id),
    )
    conn.commit()
    conn.close()


def get_all_jobs(status: str = None) -> list:
    conn, db_type = get_connection()
    cur = conn.cursor()

    if db_type == "postgres":
        cur.execute("SELECT * FROM jobs ORDER BY match_score DESC NULLS LAST")
        columns = [desc[0] for desc in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    else:
        import sqlite3

        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if status:
            cur.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY match_score DESC",
                (status,),
            )
        else:
            cur.execute("SELECT * FROM jobs ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]

    conn.close()
    return rows


def log_run(stats: dict):
    conn, db_type = get_connection()
    cur = conn.cursor()
    placeholder = "%s" if db_type == "postgres" else "?"
    cur.execute(
        f"INSERT INTO runs (scraped, matched, applied, errors) VALUES ({placeholder},{placeholder},{placeholder},{placeholder})",
        (
            stats.get("scraped", 0),
            stats.get("matched", 0),
            stats.get("applied", 0),
            stats.get("errors", 0),
        ),
    )
    conn.commit()
    conn.close()
