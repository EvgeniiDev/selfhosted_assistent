from typing import Dict, Any, Optional
from datetime import datetime
from dateutil.parser import parse as parse_date

from inference import CalendarInference
from google_calendar_client import GoogleCalendarClient
from models import CalendarEvent
from logger import calendar_logger


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

            # Возвращаем данные для подтверждения вместо создания события
            return {
                'success': True,
                'action': 'confirm',
                'event': calendar_event,
                'message': self._format_event_confirmation(calendar_event)
            }

        except Exception as e:
            calendar_logger.log_error(e, "calendar_service.process_user_request")
            return {
                'success': False,
                'message': f'Произошла ошибка: {str(e)}'
            }

    def create_confirmed_event(self, calendar_event: CalendarEvent) -> Dict[str, Any]:
        """Создает подтвержденное событие в Google Calendar"""
        try:
            # Создаем событие в Google Calendar
            google_event_data = calendar_event.to_google_event()
            result = self.calendar_client.create_event(google_event_data)

            return result or {
                'success': False,
                'message': 'Неожиданная ошибка при создании события'
            }

        except Exception as e:
            calendar_logger.log_error(e, "calendar_service.create_confirmed_event")
            return {
                'success': False,
                'message': f'Произошла ошибка при создании события: {str(e)}'
            }

    def _format_event_confirmation(self, event: CalendarEvent) -> str:
        """Форматирует событие для подтверждения пользователем"""
        # Форматируем время начала
        start_time_str = event.start_time.strftime("%d.%m.%Y в %H:%M")
        
        # Форматируем время окончания
        if event.end_time:
            end_time_str = event.end_time.strftime("%H:%M")
            duration_str = f"до {end_time_str}"
        elif event.duration_minutes:
            hours = event.duration_minutes // 60
            minutes = event.duration_minutes % 60
            if hours > 0 and minutes > 0:
                duration_str = f"({hours}ч {minutes}мин)"
            elif hours > 0:
                duration_str = f"({hours}ч)"
            else:
                duration_str = f"({minutes}мин)"
        else:
            duration_str = "(1ч)"

        # Форматируем повторяемость
        recurrence_str = ""
        if event.recurrence:
            recurrence_str = "\n🔄 Повторяемость: Да"

        # Собираем сообщение
        message = f"""📅 **Подтверждение события**

📝 **Название:** {event.title}
⏰ **Время:** {start_time_str} {duration_str}"""

        if event.description:
            message += f"\n📋 **Описание:** {event.description}"
        
        message += recurrence_str
        message += "\n\n✅ Подтвердить создание события?"

        return message

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
            calendar_logger.log_error(Exception("Failed to create CalendarEvent"), "calendar_service._create_calendar_event")
            return None
