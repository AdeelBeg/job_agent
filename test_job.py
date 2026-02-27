# debug_job.py
import os
from dotenv import load_dotenv

load_dotenv()

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Show all job IDs in database
cur.execute("SELECT id, title, company FROM jobs LIMIT 10")
rows = cur.fetchall()

print("=== JOBS IN DATABASE ===")
for row in rows:
    print(f"ID: [{row[0]}] len={len(row[0])} | {row[1]} @ {row[2]}")

# Now paste the ID from Telegram here
test_id = "b5255f6758"
print(f"\n=== SEARCHING FOR: [{test_id}] len={len(test_id)} ===")

cur.execute("SELECT id, title FROM jobs WHERE id = %s", (test_id,))
result = cur.fetchone()
print(f"Exact match: {result}")

cur.execute("SELECT id, title FROM jobs WHERE id LIKE %s", (f"%{test_id}%",))
result = cur.fetchone()
print(f"Partial match: {result}")

cur.execute("SELECT id, title FROM jobs WHERE TRIM(id) = TRIM(%s)", (test_id,))
result = cur.fetchone()
print(f"Trimmed match: {result}")

conn.close()
