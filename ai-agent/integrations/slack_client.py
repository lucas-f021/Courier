import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import logging

log = logging.getLogger(__name__)

def get_slack_client() -> WebClient:
    return WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

def post_message(client, channel_id, text):
    try:
        client.chat_postMessage(channel=channel_id, text=text)
        log.info(f"slack_posted | channel={channel_id}")
    except SlackApiError as e:
        log.error(f"slack_error | op=post_message | error={e.response['error']}")

def get_channel_messages(client, channel_id, limit=10):
    try:
        result = client.conversations_history(channel=channel_id, limit=limit)
        log.info(f"slack_messages_fetched | channel={channel_id} | count={len(result['messages'])}")
        return result['messages']
    except SlackApiError as e:
        log.error(f"slack_error | op=get_messages | error={e.response['error']}")
        return []

def reply_in_thread(client, channel_id, thread_ts, text):
    """Reply inside an existing thread. thread_ts ties the reply to the parent message."""
    try:
        client.chat_postMessage(channel=channel_id, thread_ts=thread_ts, text=text)
        log.info(f"slack_thread_reply | channel={channel_id} | thread={thread_ts}")
    except SlackApiError as e:
        log.error(f"slack_error | op=reply_in_thread | error={e.response['error']}")

def get_thread_history(client, channel_id, thread_ts, limit=10):
    """Fetch messages in a thread to provide conversation context."""
    try:
        result = client.conversations_replies(
            channel=channel_id, ts=thread_ts, limit=limit
        )
        messages = result.get("messages", [])
        log.info(f"thread_history_fetched | channel={channel_id} | thread={thread_ts} | count={len(messages)}")
        return messages
    except SlackApiError as e:
        log.error(f"slack_error | op=get_thread_history | error={e.response['error']}")
        return []

def open_dm(client, user_id):
    """Open a DM channel with a user and return the channel ID."""
    try:
        result = client.conversations_open(users=user_id)
        return result['channel']['id']
    except SlackApiError as e:
        log.error(f"slack_error | op=open_dm | error={e.response['error']}")
        return None