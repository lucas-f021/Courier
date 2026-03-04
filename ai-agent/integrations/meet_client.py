from googleapiclient.discovery import build
import logging

from integrations.auth import get_credentials

log = logging.getLogger(__name__)


def get_meet_service():
    return build('meet', 'v2', credentials=get_credentials())


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
