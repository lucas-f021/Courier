from dotenv import load_dotenv
load_dotenv()

import os
import time
import sqlite3
import logging
import threading
from gmail import get_gmail_service, get_recent_emails
from slack_client import get_slack_client
from slack_listener import start_listener
from ai_agent import run_agent, run_slack_agent
from calendar_client import get_calendar_service
from drive_client import get_drive_service, get_docs_service
from meet_client import get_meet_service

_fmt = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s | %(message)s')
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
_file_handler = logging.FileHandler('agent.log')
_file_handler.setFormatter(_fmt)
logging.getLogger().addHandler(_file_handler)

log = logging.getLogger(__name__)

DB_PATH = "processed_emails.db"

def _init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("CREATE TABLE IF NOT EXISTS processed (email_id TEXT PRIMARY KEY)")
    con.commit()
    con.close()

def is_processed(email_id: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT 1 FROM processed WHERE email_id = ?", (email_id,)).fetchone()
    con.close()
    return row is not None

def mark_processed(email_id: str):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT OR IGNORE INTO processed VALUES (?)", (email_id,))
    con.commit()
    con.close()


def main():
    POLL_INTERVAL_SECONDS = 300

    log.info("agent_startup")
    _init_db()

    gmail = get_gmail_service()
    slack = get_slack_client()
    calendar = get_calendar_service()
    drive = get_drive_service()
    docs = get_docs_service()
    meet = get_meet_service()
    channel = os.getenv("SLACK_CHANNEL_ID")

    def agent_callback(text, channel, thread_ts, is_dm):
        run_slack_agent(text, channel, thread_ts, is_dm, slack)

    listener_thread = threading.Thread(target=start_listener, args=(slack, agent_callback), daemon=True)
    listener_thread.start()

    try:
        while True:
            try:
                emails = get_recent_emails(gmail, max_results=10)
                new_emails = [e for e in emails if not is_processed(e['id'])]
                log.info(f"poll | total={len(emails)} | new={len(new_emails)}")

                for email in new_emails:
                    try:
                        run_agent(email, gmail, slack, channel, calendar, drive, docs, meet)
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