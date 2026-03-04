import re
from googleapiclient.discovery import build
import logging

from integrations.auth import get_credentials

log = logging.getLogger(__name__)


def get_drive_service():
    return build('drive', 'v3', credentials=get_credentials())


def get_docs_service():
    return build('docs', 'v1', credentials=get_credentials())


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
        safe_q = re.sub(r"['\"\\\n\r]", '', query)[:200]
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
