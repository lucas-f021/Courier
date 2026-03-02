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


def get_drive_service():
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
    return build('drive', 'v3', credentials=creds)


def get_docs_service():
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
    return build('docs', 'v1', credentials=creds)


def read_doc_content(service, doc_id):
    try:
        doc = service.documents().get(documentId=doc_id).execute()
        text_parts = []
        for item in doc.get('body', {}).get('content', []):
            if 'paragraph' in item:
                for element in item['paragraph'].get('elements', []):
                    if 'textRun' in element:
                        text_parts.append(element['textRun']['content'])
        text = ''.join(text_parts)
        log.info(f"doc_read | doc_id={doc_id} | chars={len(text)}")
        return text
    except Exception as e:
        log.error(f"docs_error | doc_id={doc_id} | error={str(e)}")
        return ""


def search_drive_files(service, query, max_results=5):
    try:
        safe_q = query.replace("'", "\\'")
        result = service.files().list(
            q=f"name contains '{safe_q}' and trashed = false",
            pageSize=max_results,
            fields="files(id, name, webViewLink, mimeType)"
        ).execute()
        files = []
        for f in result.get('files', []):
            files.append({
                'name': f.get('name'),
                'link': f.get('webViewLink', 'No link available'),
                'type': f.get('mimeType', '')
            })
        log.info(f"drive_search | query={query} | count={len(files)}")
        return files
    except Exception as e:
        log.error(f"drive_error | error={str(e)}")
        return []
