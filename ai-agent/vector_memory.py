from dotenv import load_dotenv
load_dotenv()

import re
import sqlite3
import logging
from datetime import datetime, timezone

log = logging.getLogger(__name__)

_DB_PATH = "memory.db"


def _init_db():
    con = sqlite3.connect(_DB_PATH)
    con.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS email_memory
        USING fts5(source, source_id, summary, timestamp)
    """)
    con.commit()
    con.close()


_init_db()


def store_email_embedding(email):
    summary = f"From: {email['from']} | Subject: {email['subject']} | {email['body'][:500]}"
    ts = datetime.now(tz=timezone.utc).isoformat()
    try:
        con = sqlite3.connect(_DB_PATH)
        con.execute(
            "INSERT INTO email_memory(source, source_id, summary, timestamp) VALUES (?, ?, ?, ?)",
            ("gmail", email['id'], summary, ts)
        )
        con.commit()
        con.close()
        log.info(f"embedding_stored | id={email['id']}")
    except Exception as e:
        log.error(f"embedding_store_error | id={email['id']} | error={str(e)}")


def retrieve_similar_emails(query_text, max_results=3):
    try:
        # FTS5 treats special chars as operators — strip them before querying
        safe_query = re.sub(r'[^\w\s]', ' ', query_text).strip()
        if not safe_query:
            return []
        con = sqlite3.connect(_DB_PATH)
        rows = con.execute(
            """
            SELECT source, source_id, summary, timestamp
            FROM email_memory
            WHERE email_memory MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (safe_query, max_results)
        ).fetchall()
        con.close()
        results = [
            {"source": r[0], "source_id": r[1], "summary": r[2], "timestamp": r[3]}
            for r in rows
        ]
        log.info(f"memory_retrieved | query_len={len(query_text)} | count={len(results)}")
        return results
    except Exception as e:
        log.error(f"memory_retrieve_error | error={str(e)}")
        return []
