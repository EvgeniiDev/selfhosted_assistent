import json
from typing import Optional
from datetime import datetime
from logger import calendar_logger
from models import CalendarEvent
from llm_inference import ModelRouter


SYSTEM_PROMPT = """
You are a calendar assistant that creates calendar events from user text input in Russian.

Extract event information from the text and return ONLY a JSON response without additional text.

## Response Format
Return exactly this JSON structure:
{
  "title": "string",
  "description": "string or null",
  "start_time": "YYYY-MM-DDTHH:MM:SS",
  "end_time": "YYYY-MM-DDTHH:MM:SS or null",
  "duration_minutes": "number or null",
  "recurrence": "string or null"
}

## Time Rules
1. Assume all times are in the user's local time zone
2. If **end time** is specified → fill `end_time`, set `duration_minutes` = null
3. If **duration** is specified → fill `duration_minutes`, set `end_time` = null
4. If **neither** is specified → set `duration_minutes` = 60, `end_time` = null

## Recurrence Field (Optional)
Possible values:
- `null` - one-time event (default)
- `"Daily"` - every day
- `"Weekly on [day of week]"` - weekly on specified day
- `"Monthly on the first [day of week]"` - monthly on first specified day
- `"Annually on [month day]"` - yearly on specified date
- `"Every weekday (Monday to Friday)"` - every workday

**Important:** If day of week isn't explicitly mentioned, use the current day of week.

## Date Handling
- For dates without a year, assume the current year or next occurrence if the date has already passed

## Examples
- Input: "Встреча каждый понедельник в 14:00"
  Output: {"title": "Встреча", "description": null, "start_time": "2025-08-11T14:00:00", "end_time": null, "duration_minutes": 60, "recurrence": "Weekly on Monday"}

- Input: "Совещание завтра с 10 до 11"
  Output: {"title": "Совещание", "description": null, "start_time": "2025-08-09T10:00:00", "end_time": "2025-08-09T11:00:00", "duration_minutes": null, "recurrence": null}
"""

class CalendarInference:
    def __init__(self):
        """Инициализация с простым роутером"""
        self.router = ModelRouter()
        
        calendar_logger.info('CalendarInference initialized')
        
        # Выводим статус системы
        status = self.router.get_status()
        calendar_logger.info(f"Local model available: {status['local_available']}")
        calendar_logger.info(f"OpenRouter available: {status['openrouter_available']}")
        calendar_logger.info(f"Configured models: {status['models_count']}")

    def process_request(self, user_message: str) -> Optional[CalendarEvent]:
        """Обрабатывает запрос пользователя и возвращает объект CalendarEvent"""
        # Добавляем текущее время в промт пользователя
        current_time = datetime.now()
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S (%A)")
        
        enhanced_message = f"""
        ## Input Data
        - Current date: {current_time_str}
        - User query: {user_message}
        """
        
        try:
            # Календарные задачи всегда приватные (локальная модель)
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
                
                return CalendarEvent(**parsed_data)
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
