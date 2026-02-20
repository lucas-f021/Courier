from dotenv import load_dotenv
load_dotenv()

import os
import time
import logging
from gmail import get_gmail_service, get_recent_emails
from slack_client import get_slack_client
from ai_agent import run_agent


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
log = logging.getLogger(__name__)

def main():
    gmail = get_gmail_service()
    slack = get_slack_client()
    channel = os.getenv("SLACK_CHANNEL_ID")
    emails = get_recent_emails(gmail, max_results=3)
    log.info(f"agent_started | email_count={len(emails)}")
    for email in emails:
        log.info(f"email_processing | from={email['from']} | subject={email['subject']}")
        run_agent(email, gmail, slack, channel)
        time.sleep(1)



if __name__ == "__main__":
    main()