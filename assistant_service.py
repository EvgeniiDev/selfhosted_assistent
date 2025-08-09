from typing import Dict, Any
from datetime import datetime

from request_classifier import RequestClassifier
from google_calendar_client import GoogleCalendarClient
from models import CalendarEvent, Note
from logger import calendar_logger


class AssistantService:
    def __init__(self):
        self.inference = RequestClassifier()
        self.calendar_client = GoogleCalendarClient()

    def process_user_request(self, user_message: str) -> Dict[str, Any]:
        """Обрабатывает запрос пользователя и создает событие в календаре или возвращает заметку"""
        try:
            # Получаем CalendarEvent или Note от модели
            result = self.inference.process_request(user_message)

            if not result:
                return {
                    'success': False,
                    'message': 'Не удалось понять запрос. Попробуйте переформулировать.'
                }

            # Обрабатываем результат в зависимости от типа
            match result:
                case Note():
                    # Заметка - возвращаем её сразу
                    return {
                        'success': True,
                        'action': 'note',
                        'note': result,
                        'message': self._format_note_response(result)
                    }
                
                case CalendarEvent():
                    # Календарное событие - возвращаем данные для подтверждения
                    return {
                        'success': True,
                        'action': 'confirm',
                        'event': result,
                        'message': self._format_event_confirmation(result)
                    }
                
                case _:
                    # Неожиданный тип объекта
                    return {
                        'success': False,
                        'message': 'Получен неожиданный тип объекта. Попробуйте переформулировать запрос.'
                    }

        except Exception as e:
            calendar_logger.log_error(e, "assistant_service.process_user_request")
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
            calendar_logger.log_error(e, "assistant_service.create_confirmed_event")
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

    def _format_note_response(self, note: Note) -> str:
        """Форматирует заметку для отправки пользователю"""
        # Форматируем дату создания
        try:
            created_time = datetime.fromisoformat(note.created_at)
            created_str = created_time.strftime("%d.%m.%Y в %H:%M")
        except:
            created_str = note.created_at

        # Собираем сообщение
        message = f"""📝 **Ваша заметка**

**{note.title}**

{note.content}

📅 Создано: {created_str}"""

        # Добавляем теги, если они есть
        if note.tags and len(note.tags) > 0:
            tags_str = " ".join([f"#{tag}" for tag in note.tags])
            message += f"\n🏷️ Теги: {tags_str}"

        return message
