from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import logging
import os

log = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/meetings.space.readonly',
]

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOKEN = os.path.join(_ROOT, 'token.json')
_CREDS = os.path.join(_ROOT, 'credentials.json')


def get_calendar_service():
    creds = None
    if os.path.exists(_TOKEN):
        creds = Credentials.from_authorized_user_file(_TOKEN, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(_CREDS, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(_TOKEN, 'w') as f:
            f.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

def create_event(service, summary, start_time, end_time, description=None, attendees=None):
    """Create a calendar event.
    start_time/end_time: ISO 8601 datetime strings (e.g. '2026-03-01T21:00:00')
    attendees: list of email addresses (optional)
    """
    event_body = {
        'summary': summary,
        'start': {'dateTime': start_time, 'timeZone': 'America/New_York'},
        'end': {'dateTime': end_time, 'timeZone': 'America/New_York'},
    }
    if description:
        event_body['description'] = description
    if attendees:
        event_body['attendees'] = [{'email': e} for e in attendees]
    try:
        event = service.events().insert(calendarId='primary', body=event_body).execute()
        log.info(f"calendar_event_created | summary={summary} | start={start_time}")
        return {
            'id': event['id'],
            'summary': event.get('summary'),
            'start': event['start'].get('dateTime'),
            'link': event.get('htmlLink'),
        }
    except Exception as e:
        log.error(f"calendar_create_error | error={str(e)}")
        return None


def get_upcoming_events(service, max_results=10):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    try:
        result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = []
        for event in result.get('items', []):
            events.append({
                'id': event['id'],
                'summary': event.get('summary', 'No title'),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'attendees': [a['email'] for a in event.get('attendees', [])]
            })
        log.info(f"calendar_fetched | count={len(events)}")
        return events
    except Exception as e:
        log.error(f"calendar_error | error={str(e)}")
        return []


def delete_event(service, event_id):
    """Delete a calendar event by its ID."""
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        log.info(f"calendar_event_deleted | id={event_id}")
        return True
    except Exception as e:
        log.error(f"calendar_delete_error | id={event_id} | error={str(e)}")
        return False

