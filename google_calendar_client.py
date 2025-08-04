from typing import Dict, Any, Optional
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarClient:
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json"):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._authenticate()

    def _authenticate(self):
        """Аутентификация с Google Calendar API"""
        creds = None

        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(
                self.token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        return build('calendar', 'v3', credentials=creds)

    def create_event(self, event_data: Dict[str, Any], calendar_id: str = 'primary') -> Optional[Dict[str, Any]]:
        """Создает событие в календаре"""
        try:
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_data
            ).execute()

            return {
                'success': True,
                'event_id': event.get('id'),
                'event_link': event.get('htmlLink'),
                'message': f"Событие '{event_data.get('summary')}' создано успешно"
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f"Ошибка при создании события: {str(e)}"
            }
