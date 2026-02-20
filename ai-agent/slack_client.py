import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging

log = logging.getLogger(__name__)

def get_slack_client() -> WebClient:
    return WebClient(token = os.getenv("SLACK_BOT_TOKEN"))

def post_message(client, channel_id, text):
    try:
        client.chat_postMessage(channel = channel_id, text = text)
        log.info(f"slack_posted | channel={channel_id}")
    except SlackApiError as e:
        log.error(f"slack_error | error={e.response['error']}")