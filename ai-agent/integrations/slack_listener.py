from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest 
from slack_sdk.socket_mode.response import SocketModeResponse
import logging
import os

log = logging.getLogger(__name__)

def start_listener(slack_web_client, agent_callback):

    socket_client = SocketModeClient(
        app_token=os.getenv("SLACK_APP_TOKEN"),
        web_client=slack_web_client
    )

    def handle_event(client: SocketModeClient, req: SocketModeRequest):
        client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))

        if req.type != "events_api":
            return

        event = req.payload.get("event", {})
        event_type = event.get("type")

        if event.get("bot_id"):
            return

        if event_type == "app_mention":
            agent_callback(
                text=event.get("text", ""),
                channel=event["channel"],
                thread_ts=event.get("thread_ts") or event["ts"],
                is_dm=False
            )

        elif event_type == "message" and event.get("channel_type") == "im":
            agent_callback(
                text=event.get("text", ""),
                channel=event["channel"],
                thread_ts=event["ts"],
                is_dm=True
            )

    socket_client.socket_mode_request_listeners.append(handle_event)
    socket_client.connect()
    log.info("slack_listener_started | mode=socket")

    import threading
    threading.Event().wait()