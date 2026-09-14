import base64

from googleapiclient.discovery import build


def get_gmail_service(creds):
    """Builds the Gmail service using provided credentials."""
    return build('gmail', 'v1', credentials=creds)

def search_recent_bank_alerts(service, sender_email: str = "alerts@axis.bank.in", newer_than: str = "2m", limit: int = 500) -> list[dict[str, str]]:
    """
    Finds alert emails from the specified bank.
    Using 'newer_than:2m' pulls all history from the last 2 months.
    """
    # Simply filters by the sender and date range. Gmail handles the heavy lifting.
    query = f"from:{sender_email} newer_than:{newer_than}"
    print(f"Gmail Query: {query}")
    results = service.users().messages().list(userId='me', q=query, maxResults=limit).execute()
    return results.get('messages', [])

def get_email_body(service, msg_id: str) -> str | None:
    """
    Fetches the full email message and decodes the plain text body.
    """
    message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
    payload = message.get('payload', {})
    parts = payload.get('parts', [])
    
    body_data = None
    
    if not parts:
        body_data = payload.get('body', {}).get('data')
    else:
        for part in parts:
            if part.get('mimeType') == 'text/plain':
                body_data = part.get('body', {}).get('data')
                break
                
    if body_data:
        # Gmail API uses URL-safe base64 encoding
        return base64.urlsafe_b64decode(body_data).decode('utf-8')
    return None

def mark_as_read(service, msg_id: str):
    """Marks an email as read by removing the UNREAD label."""
    try:
        service.users().messages().modify(
            userId='me', 
            id=msg_id, 
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
    except Exception:
        # If it was already read, it might throw an error gracefully ignore
        pass
