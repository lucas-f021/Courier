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


def get_meet_service():
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
    return build('meet', 'v2', credentials=creds)


def get_recent_transcripts(service, max_results=3):
    """
    Fetch recent conference records and their transcript text.
    Returns a list of dicts with 'meeting_id' and 'transcript' keys.
    """
    try:
        records_resp = service.conferenceRecords().list(
            pageSize=max_results
        ).execute()
        records = records_resp.get('conferenceRecords', [])
        results = []
        for record in records:
            record_name = record.get('name')
            transcripts_resp = service.conferenceRecords().transcripts().list(
                parent=record_name
            ).execute()
            transcripts = transcripts_resp.get('transcripts', [])
            for transcript in transcripts:
                transcript_name = transcript.get('name')
                entries_resp = service.conferenceRecords().transcripts().entries().list(
                    parent=transcript_name
                ).execute()
                entries = entries_resp.get('entries', [])
                lines = []
                for entry in entries:
                    speaker = entry.get('participant', {}).get('signedinUser', {}).get('displayName', 'Unknown')
                    text = entry.get('text', '')
                    if text:
                        lines.append(f"{speaker}: {text}")
                if lines:
                    results.append({
                        'meeting_id': record_name,
                        'transcript': '\n'.join(lines)
                    })
        log.info(f"meet_transcripts_fetched | count={len(results)}")
        return results
    except Exception as e:
        log.error(f"meet_error | error={str(e)}")
        return []
