import json
from typing import Optional, Union
from datetime import datetime
from logger import calendar_logger
from models import CalendarEvent, Note
from llm_inference import ModelRouter


SYSTEM_PROMPT = """
You are a smart assistant that processes user requests in Russian and determines whether they want to create a calendar event or save a note.

First, determine the request type, then extract the relevant information. Return ONLY a JSON response without additional text.

## Request Type Detection
- **Calendar Event**: mentions time, date, meetings, appointments, reminders with specific times
- **Note**: general information to remember, ideas, thoughts, lists, anything without specific time constraints

## Response Format
Return exactly this JSON structure based on request type:

### For Calendar Events:
{
  "type": "calendar_event",
  "data": {
    "title": "string",
    "description": "string or null",
    "start_time": "YYYY-MM-DDTHH:MM:SS",
    "end_time": "YYYY-MM-DDTHH:MM:SS or null",
    "duration_minutes": "number or null",
    "recurrence": "string or null"
  }
}

### For Notes:
{
  "type": "note",
  "data": {
    "title": "string",
    "content": "string",
    "created_at": "YYYY-MM-DDTHH:MM:SS",
    "tags": ["string", "string"] or null
  }
}

## Calendar Event Rules
1. Assume all times are in the user's local time zone
2. If **end time** is specified → fill `end_time`, set `duration_minutes` = null
3. If **duration** is specified → fill `duration_minutes`, set `end_time` = null
4. If **neither** is specified → set `duration_minutes` = 60, `end_time` = null

## Note Rules
1. **Correct grammar, punctuation, and spelling** in the content
2. **Capitalize** sentences properly
3. Generate a short, descriptive title (3-7 words)
4. Extract relevant tags if applicable (optional, max 3 tags)
5. Use current timestamp for `created_at`

## Recurrence Field (Calendar Events Only)
Possible values:
- `null` - one-time event (default)
- `"Daily"` - every day
- `"Weekly on [day of week]"` - weekly on specified day
- `"Monthly on the first [day of week]"` - monthly on first specified day
- `"Annually on [month day]"` - yearly on specified date
- `"Every weekday (Monday to Friday)"` - every workday

## Date Handling
- For dates without a year, assume the current year or next occurrence if the date has already passed

## Examples
### Calendar:
- Input: "Встреча каждый понедельник в 14:00"
  Output: {"type": "calendar_event", "data": {"title": "Встреча", "description": null, "start_time": "2025-01-13T14:00:00", "end_time": null, "duration_minutes": 60, "recurrence": "Weekly on Monday"}}

### Note:
- Input: "нужно купить молоко хлеб и масло"
  Output: {"type": "note", "data": {"title": "Список покупок", "content": "Нужно купить молоко, хлеб и масло.", "created_at": "2025-01-08T15:30:00", "tags": ["покупки"]}}
"""

class RequestClassifier:
    def __init__(self):
        """Инициализация с простым роутером"""
        self.router = ModelRouter()
        
        calendar_logger.info('RequestClassifier initialized with notes support')
        
        # Выводим статус системы
        status = self.router.get_status()
        calendar_logger.info(f"Local model available: {status['local_available']}")
        calendar_logger.info(f"OpenRouter available: {status['openrouter_available']}")
        calendar_logger.info(f"Configured models: {status['models_count']}")

    def process_request(self, user_message: str) -> Optional[Union[CalendarEvent, Note]]:
        """Обрабатывает запрос пользователя и возвращает объект CalendarEvent или Note"""
        # Добавляем текущее время в промт пользователя
        current_time = datetime.now()
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S (%A)")
        
        enhanced_message = f"""
        ## Input Data
        - Current date: {current_time_str}
        - User query: {user_message}
        """
        
        try:
            # Все задачи приватные (локальная модель)
            content = self.router.generate(enhanced_message, SYSTEM_PROMPT, is_private=True)
            
            if not content:
                calendar_logger.log_error(
                    Exception("No response from router"),
                    "inference.process_request - router"
                )
                return None
            
            # Извлекаем JSON из ответа
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                # Логируем структурированный ответ
                calendar_logger.log_llm_response(content, parsed_data)
                
                # Определяем тип и создаем соответствующий объект
                if parsed_data.get('type') == 'calendar_event':
                    return CalendarEvent(**parsed_data['data'])
                elif parsed_data.get('type') == 'note':
                    return Note(**parsed_data['data'])
                else:
                    calendar_logger.log_error(
                        Exception(f"Unknown type in response: {parsed_data.get('type')}"),
                        "inference.process_request - type detection"
                    )
                    return None
            else:
                calendar_logger.log_error(
                    Exception(f"No JSON found in response: {content}"),
                    "inference.process_request - JSON extraction"
                )
                return None
                
        except json.JSONDecodeError as e:
            if 'content' in locals():
                calendar_logger.log_llm_response(content, None)
            calendar_logger.log_error(e, "inference.process_request - JSON parsing")
        except Exception as e:
            calendar_logger.log_error(e, "inference.process_request - General exception")

        return None
