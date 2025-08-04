from typing import Dict, Any, Optional
from datetime import datetime
from dateutil.parser import parse as parse_date

from inference import CalendarInference
from google_calendar_client import GoogleCalendarClient
from models import CalendarEvent


class CalendarService:
    def __init__(self, model_path: str, credentials_path: str = "credentials.json"):
        self.inference = CalendarInference(model_path)
        self.calendar_client = GoogleCalendarClient(credentials_path)

    def process_user_request(self, user_message: str) -> Dict[str, Any]:
        """Обрабатывает запрос пользователя и создает событие в календаре"""
        try:
            # Получаем JSON от модели
            event_data = self.inference.process_request(user_message)

            if not event_data:
                return {
                    'success': False,
                    'message': 'Не удалось понять запрос. Попробуйте переформулировать.'
                }

            # Валидируем и преобразуем данные
            calendar_event = self._create_calendar_event(event_data)

            if not calendar_event:
                return {
                    'success': False,
                    'message': 'Ошибка в данных события. Проверьте время и дату.'
                }

            # Создаем событие в Google Calendar
            google_event_data = calendar_event.to_google_event()
            result = self.calendar_client.create_event(google_event_data)

            return result or {
                'success': False,
                'message': 'Неожиданная ошибка при создании события'
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Произошла ошибка: {str(e)}'
            }

    def _create_calendar_event(self, event_data: Dict[str, Any]) -> Optional[CalendarEvent]:
        """Создает объект CalendarEvent из данных модели"""
        try:
            # Обязательные поля
            title = event_data.get('title')
            start_time_str = event_data.get('start_time')

            if not title or not start_time_str:
                return None

            start_time = parse_date(start_time_str)

            # Опциональные поля
            description = event_data.get('description')
            end_time = None
            duration_minutes = event_data.get('duration_minutes')

            if event_data.get('end_time'):
                end_time = parse_date(event_data['end_time'])

            recurrence = event_data.get('recurrence')

            return CalendarEvent(
                title=title,
                description=description,
                start_time=start_time,
                end_time=end_time,
                duration_minutes=duration_minutes,
                recurrence=recurrence
            )

        except Exception:
            return None
