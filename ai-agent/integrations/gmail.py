import ctypes
import os
import re
import sys
import base64 as _b64std
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import logging
from integrations.auth import get_credentials

log = logging.getLogger(__name__)

if sys.platform == 'win32':
    _lib_path = os.path.join(os.path.dirname(__file__), '..', 'base64.dll')
else:
    _lib_path = os.path.join(os.path.dirname(__file__), '..', 'b64decode.so')

_lib_path = os.path.realpath(_lib_path)
_expected_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
if not _lib_path.startswith(_expected_dir + os.sep):
    raise RuntimeError(f"base64 library resolved outside project directory: {_lib_path}")

_b64lib = ctypes.CDLL(_lib_path)
_b64lib.b64_decode.argtypes = [
    ctypes.c_char_p, ctypes.c_char_p,
    ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)
]
_b64lib.b64_decode.restype = ctypes.c_int


def decode_base64_urlsafe(encoded: str) -> str:
    encoded_bytes = encoded.encode('ascii')
    out_size = len(encoded_bytes)
    out_buf = ctypes.create_string_buffer(out_size)
    out_len = ctypes.c_size_t(0)
    ret = _b64lib.b64_decode(encoded_bytes, out_buf, ctypes.c_size_t(out_size), ctypes.byref(out_len))
    if ret != 0:
        log.warning("b64_decode_failed | falling back to stdlib")
        return _b64std.urlsafe_b64decode(encoded + '==').decode('utf-8', errors='replace')
    return out_buf.raw[:out_len.value].decode('utf-8', errors='replace')


def get_gmail_service():
    return build('gmail', 'v1', credentials=get_credentials())


def _sanitize_header(value, max_len=500):
    """Strip control characters and truncate email header values."""
    return re.sub(r'[\x00-\x1f\x7f]', '', value)[:max_len]


def _get_header(headers, name, default=''):
    """Extract a single header value by name (case-insensitive)."""
    return next((h['value'] for h in headers if h['name'].lower() == name), default)


def _extract_body(payload):
    """Extract plain-text body from a Gmail message payload."""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain' and 'data' in part.get('body', {}):
                return decode_base64_urlsafe(part['body']['data'])
    elif 'data' in payload.get('body', {}):
        return decode_base64_urlsafe(payload['body']['data'])
    return ''


def get_recent_emails(service, max_results=5):
    msg_ids = service.users().messages().list(userId='me', maxResults=max_results, labelIds=['INBOX']).execute()
    emails = []
    for msg in msg_ids.get('messages', []):
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_data['payload']['headers']
        subject = _sanitize_header(_get_header(headers, 'subject', 'No Subject'))
        frm = _sanitize_header(_get_header(headers, 'from', 'Unknown'))
        body = _extract_body(msg_data['payload'])
        if not body:
            log.warning(f"email_skipped | reason=body_empty | id={msg['id']}")
        else:
            log.info(f"email_fetched | from={frm} | subject={subject}")
        emails.append({'id': msg['id'], 'subject': subject, 'from': frm, 'body': body})
    return emails


def search_emails(service, query, max_results=5):
    """Search Gmail by query string (same syntax as Gmail search bar)."""
    try:
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        emails = []
        for msg in results.get('messages', []):
            msg_data = service.users().messages().get(
                userId='me', id=msg['id'], format='metadata',
                metadataHeaders=['Subject', 'From']
            ).execute()
            headers = msg_data.get('payload', {}).get('headers', [])
            subject = _sanitize_header(_get_header(headers, 'subject', 'No Subject'))
            frm = _sanitize_header(_get_header(headers, 'from', 'Unknown'))
            snippet = _sanitize_header(msg_data.get('snippet', ''), max_len=300)
            emails.append({'id': msg['id'], 'subject': subject, 'from': frm, 'snippet': snippet})
        log.info(f"email_search | query={query} | results={len(emails)}")
        return emails
    except Exception as e:
        log.error(f"email_search_error | query={query} | error={str(e)}")
        return []


def read_email(service, email_id):
    """Fetch the full body of a single email by its ID."""
    try:
        msg_data = service.users().messages().get(userId='me', id=email_id, format='full').execute()
        headers = msg_data['payload']['headers']
        subject = _sanitize_header(_get_header(headers, 'subject', 'No Subject'))
        frm = _sanitize_header(_get_header(headers, 'from', 'Unknown'))
        body = _extract_body(msg_data['payload'])
        log.info(f"email_read | id={email_id} | from={frm} | subject={subject}")
        return {'id': email_id, 'subject': subject, 'from': frm, 'body': body}
    except Exception as e:
        log.error(f"email_read_error | id={email_id} | error={str(e)}")
        return None


def send_email(service, to, subject, body):
    """Send a new email immediately (not a reply, not a draft)."""
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    raw = _b64std.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    try:
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        log.info(f"email_sent | to={to} | subject={subject}")
        return True
    except Exception as e:
        log.error(f"email_send_error | to={to} | error={str(e)}")
        return False


def send_reply(service, to, subject, body, draft_mode=True):
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = f"Re: {subject}"
    raw = _b64std.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    if draft_mode:
        service.users().drafts().create(userId='me', body={'message': {'raw': raw}}).execute()
        log.info(f"draft_saved | to={to} | subject={subject}")
    else:
        print(f"Send email to {to}? (y/n)")
        if input().lower() == 'y':
            service.users().messages().send(userId='me', body={'raw': raw}).execute()
            log.info(f"email_sent | to={to} | subject={subject}")
        else:
            log.info(f"email_cancelled | to={to}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(levelname)s | %(message)s')
    service = get_gmail_service()
    emails = get_recent_emails(service, max_results=3)
    for email in emails:
        print(f"From: {email['from']}")
        print(f"Subject: {email['subject']}")
        print(f"Body preview: {email['body'][:200]}")
        print("---")
    send_reply(service, emails[0]['from'], emails[0]['subject'], 'Test reply body', draft_mode=True)
