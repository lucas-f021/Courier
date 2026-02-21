from dotenv import load_dotenv
load_dotenv()

import os
import time
import logging
import threading
from gmail import get_gmail_service, get_recent_emails
from slack_client import get_slack_client
from slack_listener import start_listener
from ai_agent import run_agent, run_slack_agent
from calendar_client import get_calendar_service
from drive_client import get_drive_service, get_docs_service


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
log = logging.getLogger(__name__)

def main():
    log.info("agent_startup")
    gmail = get_gmail_service()
    slack = get_slack_client()
    calendar = get_calendar_service()
    drive = get_drive_service()
    docs = get_docs_service()
    channel = os.getenv("SLACK_CHANNEL_ID")

    def agent_callback(text, channel, thread_ts, is_dm):
        run_slack_agent(text, channel, thread_ts, is_dm, slack)

    listener_thread = threading.Thread(target=start_listener, args=(slack, agent_callback), daemon=True)
    listener_thread.start()

    emails = get_recent_emails(gmail, max_results=3)
    log.info(f"emails_found | count={len(emails)}")
    for email in emails:
        run_agent(email, gmail, slack, channel, calendar, drive, docs)
        time.sleep(1)

    listener_thread.join()


if __name__ == "__main__":
    main()