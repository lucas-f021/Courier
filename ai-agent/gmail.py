import ctypes
import os
import sys
import base64 as _b64std
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import logging

log = logging.getLogger(__name__)

if sys.platform == 'win32':
    _lib_path = os.path.join(os.path.dirname(__file__), 'base64.dll')
else:
    _lib_path = os.path.join(os.path.dirname(__file__), 'base64.so')

_b64lib = ctypes.CDLL(_lib_path)

_b64lib.b64_decode.argtypes = [
    ctypes.c_char_p,
    ctypes.c_char_p,
    ctypes.POINTER(ctypes.c_size_t)
]

_b64lib.b64_decode.restype = None

# translates our c code into python terms
def decode_base64_urlsafe(encoded: str) -> str:
    encoded_bytes = encoded.encode('ascii')
    out_buf = ctypes.create_string_buffer(len(encoded_bytes))
    out_len = ctypes.c_size_t(0)
    _b64lib.b64_decode(encoded_bytes, out_buf, ctypes.byref(out_len))
    return out_buf.raw[:out_len.value].decode('utf-8', errors='replace')

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

#connects user to gmail
def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as f:
            f.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def get_recent_emails(service, max_results = 5):
    msg_ids = service.users().messages().list(userId = 'me', maxResults = max_results, labelIds = ['INBOX']).execute()
    messages = msg_ids.get('messages', [])
    emails = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_data['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        frm = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        body = ''
        if 'parts' in msg_data['payload']:
            for part in msg_data['payload']['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part.get('body', {}):
                    body = decode_base64_urlsafe(part['body']['data'])
                    break
        emails.append({'id': msg['id'], 'subject': subject, 'from': frm, 'body': body})
    return emails

def send_reply(service, to, subject, body, draft_mode=True):
    message = MIMEText(body)
    message['to'] = to
    message['subject'] = f"Re: {subject}"
    raw = _b64std.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    if draft_mode:
        service.users().drafts().create(userId = 'me', body = {'message': {'raw': raw}}).execute()
        log.info(f"draft_saved | to={to} | subject={subject}")
    else:
        print(f"Send email to {to}? (y/n)")
        ans = input()
        if ans.lower() == 'y':
            service.users().messages().send(userId='me', body={'raw': raw}).execute()



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




 