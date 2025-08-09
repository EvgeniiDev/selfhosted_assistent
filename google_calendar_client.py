from typing import Dict, Any, Optional
import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from logger import calendar_logger


SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarClient:
    def __init__(self, credentials_path: str = "credentials.json"):
        

        credentials_path_from_env = os.getenv('GOOGLE_CREDENTIALS_PATH')

        if credentials_path_from_env:
            self.credentials_path = credentials_path
        else:
            self.credentials_path = credentials_path

        if not os.path.exists(self.credentials_path):
            raise Exception(f"Ошибка: Файл учетных данных Google не найден: {credentials_path}")

        self.service = self._authenticate()

    def _authenticate(self):
        """Аутентификация с Google Calendar API"""
        # Пробуем загрузить токен из переменных окружения
        token_json = os.getenv('GOOGLE_OAUTH_TOKEN')
        if token_json:
            try:
                token_data = json.loads(token_json)
                creds = Credentials.from_authorized_user_info(token_data, SCOPES)
                
                # Проверяем и обновляем токен если нужно
                if creds and creds.expired and creds.refresh_token:
                    print("🔄 Обновляем истекший токен...")
                    creds.refresh(Request())
                    # Обновляем токен в памяти (не сохраняем в файл)
                    print("✅ Токен обновлен в памяти")
                
                if creds and creds.valid:
                    print("✅ Используется токен из переменных окружения")
                    return build('calendar', 'v3', credentials=creds)
            except (json.JSONDecodeError, Exception) as e:
                print(f"⚠️ Ошибка при загрузке токена из переменных окружения: {e}")
        
        # Если токен не найден или не валиден - запускаем автоматическую авторизацию
        print("⚠️ Токен не найден в переменных окружения")
        return self._authenticate_auto()
    
    def _authenticate_auto(self):
        """Автоматическая OAuth аутентификация"""
        print("🚀 Запускаем автоматическую авторизацию...")
        print("💡 После авторизации скопируйте токен в main.env для будущего использования")
        
        if not os.path.exists(self.credentials_path):
            raise Exception(f"❌ Файл credentials.json не найден: {self.credentials_path}")
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, SCOPES)
            
            print("🌐 Откроется браузер для авторизации...")
            print("📋 Войдите под аккаунтом разработчика (владельца приложения)")
            
            creds = flow.run_local_server(port=0)
            
            # Выводим информацию для добавления в переменные окружения
            self._print_token_info(creds)
            
            print("✅ Авторизация завершена успешно!")
            print("⚠️ ВАЖНО: Скопируйте токен выше в main.env для постоянного использования")
            return build('calendar', 'v3', credentials=creds)
            
        except Exception as e:
            raise Exception(f"❌ Ошибка автоматической авторизации: {str(e)}")
    
    def _print_token_info(self, creds):
        """Выводит информацию о токене для добавления в переменные окружения"""
        try:
            token_data = json.loads(creds.to_json())
            token_json = json.dumps(token_data, separators=(',', ':'))
            
            print("\n" + "="*60)
            print("📋 СКОПИРУЙТЕ ЭТОТ ТОКЕН В main.env:")
            print("="*60)
            print(f"GOOGLE_OAUTH_TOKEN={token_json}")
            print("="*60)
            print("Или установите переменную окружения в PowerShell:")
            print(f'$env:GOOGLE_OAUTH_TOKEN="{token_json}"')
            print("="*60 + "\n")
        except Exception as e:
            print(f"⚠️ Не удалось вывести информацию о токене: {e}")

    def create_event(self, event_data: Dict[str, Any], calendar_id: str = 'primary') -> Optional[Dict[str, Any]]:
        """Создает событие в календаре"""
        try:
            # Логируем запрос к Google Calendar
            calendar_logger.log_calendar_request(event_data)
            
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_data
            ).execute()

            result = {
                'success': True,
                'event_id': event.get('id'),
                'event_link': event.get('htmlLink'),
                'message': f"Событие '{event_data.get('summary')}' создано успешно"
            }
            
            # Логируем успешный ответ от Google Calendar
            calendar_logger.log_calendar_response(True, result)
            
            return result
            
        except Exception as e:
            result = {
                'success': False,
                'error': str(e),
                'message': f"Ошибка при создании события: {str(e)}"
            }
            
            # Логируем ошибку от Google Calendar
            calendar_logger.log_calendar_response(False, result)
            calendar_logger.log_error(e, "google_calendar_client.create_event")
            
            return result
