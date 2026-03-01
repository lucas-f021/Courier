from dotenv import load_dotenv
load_dotenv()

# --- User config ---
USE_WEB_UI = True       # Set to True to use browser chat instead of Slack
USE_LOCAL_MODEL = True  # Set to True to use Ollama instead of Anthropic API
# -------------------

import os
import time
import sqlite3
import logging
import threading
from integrations.gmail import get_gmail_service, get_recent_emails
from integrations.slack_client import get_slack_client
from integrations.slack_listener import start_listener
from agent.ai_agent import run_agent, run_slack_agent, set_backend
from integrations.calendar_client import get_calendar_service
from integrations.drive_client import get_drive_service, get_docs_service
from integrations.meet_client import get_meet_service
from agent.vector_memory import prune_memory

import sys
_ROOT = os.path.dirname(os.path.abspath(__file__))

_fmt = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
_root = logging.getLogger()
_root.setLevel(logging.INFO)
_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.setFormatter(_fmt)
_stream_handler.stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', closefd=False)
_root.addHandler(_stream_handler)
_file_handler = logging.FileHandler(os.path.join(_ROOT, 'agent.log'), encoding='utf-8')
_file_handler.setFormatter(_fmt)
_root.addHandler(_file_handler)

log = logging.getLogger(__name__)

DB_PATH = os.path.join(_ROOT, "processed_emails.db")

def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS processed (email_id TEXT PRIMARY KEY, processed_at TEXT)")
    con.commit()
    con.close()

def is_processed(email_id: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT 1 FROM processed WHERE email_id = ?", (email_id,)).fetchone()
    con.close()
    return row is not None

def mark_processed(email_id: str):
    from datetime import datetime, timezone
    ts = datetime.now(tz=timezone.utc).isoformat()
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT OR IGNORE INTO processed VALUES (?, ?)", (email_id, ts))
    con.commit()
    con.close()

def prune_processed(keep_days=30):
    from datetime import datetime, timezone, timedelta
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=keep_days)).isoformat()
    con = sqlite3.connect(DB_PATH)
    con.isolation_level = None
    con.execute("DELETE FROM processed WHERE processed_at < ? OR processed_at IS NULL", (cutoff,))
    con.commit()
    con.execute("VACUUM")
    con.commit()
    con.close()
    log.info(f"processed_pruned | keep_days={keep_days}")


def main():
    POLL_INTERVAL_SECONDS = 300

    log.info("agent_startup")
    if USE_LOCAL_MODEL:
        set_backend("ollama")
    _init_db()
    prune_memory()
    prune_processed()

    gmail = get_gmail_service()
    slack = get_slack_client()
    calendar = get_calendar_service()
    drive = get_drive_service()
    docs = get_docs_service()
    meet = get_meet_service()
    channel = os.getenv("SLACK_CHANNEL_ID")

    if USE_WEB_UI:
        from ui.web_server import start_web_server, push_to_web
        notifier = push_to_web
        web_thread = threading.Thread(target=start_web_server, daemon=True)
        web_thread.start()
        log.info("ui_mode | mode=web | url=http://127.0.0.1:5000")
    else:
        from integrations.slack_client import post_message as _post
        notifier = lambda msg: _post(slack, channel, msg)
        def agent_callback(text, channel, thread_ts, is_dm):
            run_slack_agent(text, channel, thread_ts, is_dm, slack)
        listener_thread = threading.Thread(target=start_listener, args=(slack, agent_callback), daemon=True)
        listener_thread.start()
        log.info("ui_mode | mode=slack")

    try:
        while True:
            try:
                emails = get_recent_emails(gmail, max_results=10)
                new_emails = [e for e in emails if not is_processed(e['id'])]
                log.info(f"poll | total={len(emails)} | new={len(new_emails)}")

                for email in new_emails:
                    try:
                        run_agent(email, gmail, slack, channel, calendar, drive, docs, meet, notifier=notifier)
                        mark_processed(email['id'])
                    except Exception as e:
                        log.error(f"email_error | id={email['id']} | error={str(e)}")
                    time.sleep(1)

            except Exception as e:
                log.error(f"poll_error | error={str(e)}")

            time.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        log.info("agent_shutdown | reason=keyboard_interrupt")


if __name__ == "__main__":
    main()