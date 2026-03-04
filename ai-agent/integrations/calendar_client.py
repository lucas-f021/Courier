import re
from datetime import datetime, timezone
from googleapiclient.discovery import build
import logging

from integrations.auth import get_credentials

log = logging.getLogger(__name__)


def get_calendar_service():
    return build('calendar', 'v3', credentials=get_credentials())

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


def update_event(service, event_id, summary=None, start_time=None, end_time=None, description=None, attendees=None):
    """Update an existing calendar event. Only provided fields are changed."""
    try:
        event = service.events().get(calendarId='primary', eventId=event_id).execute()
        if summary:
            event['summary'] = summary
        if start_time:
            event['start'] = {'dateTime': start_time, 'timeZone': 'America/New_York'}
        if end_time:
            event['end'] = {'dateTime': end_time, 'timeZone': 'America/New_York'}
        if description is not None:
            event['description'] = description
        if attendees is not None:
            event['attendees'] = [{'email': e} for e in attendees]
        updated = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
        log.info(f"calendar_event_updated | id={event_id} | summary={updated.get('summary')}")
        return {
            'id': updated['id'],
            'summary': updated.get('summary'),
            'start': updated['start'].get('dateTime'),
            'link': updated.get('htmlLink'),
        }
    except Exception as e:
        log.error(f"calendar_update_error | id={event_id} | error={str(e)}")
        return None


def _ensure_tz(dt_str):
    """Append Eastern timezone offset to a naive datetime string if no tz is present."""
    if re.search(r'(Z|[+\-]\d{2}:?\d{2})$', dt_str):
        return dt_str
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime('%Y-%m-%dT%H:%M:%S-05:00')
    except ValueError:
        return dt_str + '-05:00'


def check_availability(service, time_min, time_max):
    """Check free/busy status for a time range using the FreeBusy API.
    time_min/time_max: ISO 8601 datetime strings.
    Returns a dict with 'busy' (list of busy periods) and 'free' (bool).
    """
    try:
        body = {
            'timeMin': _ensure_tz(time_min),
            'timeMax': _ensure_tz(time_max),
            'timeZone': 'America/New_York',
            'items': [{'id': 'primary'}]
        }
        result = service.freebusy().query(body=body).execute()
        busy_periods = result['calendars']['primary']['busy']
        log.info(f"availability_checked | busy_count={len(busy_periods)} | range={time_min} to {time_max}")
        return {
            'busy': [{'start': p['start'], 'end': p['end']} for p in busy_periods],
            'free': len(busy_periods) == 0
        }
    except Exception as e:
        log.error(f"availability_error | error={str(e)}")
        return None


def delete_event(service, event_id):
    """Delete a calendar event by its ID."""
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        log.info(f"calendar_event_deleted | id={event_id}")
        return True
    except Exception as e:
        log.error(f"calendar_delete_error | id={event_id} | error={str(e)}")
        return False

