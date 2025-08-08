import json
import time
import requests
from typing import Optional
from datetime import datetime
from logger import calendar_logger
from models import CalendarEvent


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
        """
        Инициализация клиента для LM Studio API
        
        Args:
            api_url: URL API LM Studio (опциональный, по умолчанию http://127.0.0.1:1234)
        """
        # Захардкоженный адрес LM Studio API
        self.api_url = "http://127.0.0.1:1234"
        
        self.chat_url = f"{self.api_url}/v1/chat/completions"
        
        calendar_logger.info(f'Initializing LM Studio API client with URL: {self.api_url}')
        
        # Проверяем доступность API
        try:
            response = requests.get(f"{self.api_url}/v1/models", timeout=5)
            if response.status_code == 200:
                models = response.json()
                calendar_logger.info(f"LM Studio API is available. Available models: {models}")
            else:
                calendar_logger.warning(f"LM Studio API responded with status {response.status_code}")
        except Exception as e:
            calendar_logger.log_error(e, "CalendarInference.__init__ - API availability check")

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
        
        # Логируем промт, отправляемый в LLM
        calendar_logger.log_llm_prompt(enhanced_message, SYSTEM_PROMPT)

        # Засекаем время начала обработки
        start_time = time.time()

        # Подготавливаем запрос для OpenAI-совместимого API (базовый режим)
        request_data = {
            "model": "local-model",  # LM Studio игнорирует это поле, но оно требуется
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": enhanced_message}
            ],
            "stream": False
        }
        
        try:
            # Отправляем запрос к LM Studio API
            response = requests.post(
                self.chat_url,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=60
            )
            
            processing_time = time.time() - start_time
            calendar_logger.info(f"LM Studio API processing time: {processing_time:.2f} seconds")
            
            if response.status_code != 200:
                calendar_logger.log_error(
                    Exception(f"API request failed with status {response.status_code}: {response.text}"),
                    "inference.process_request - API request"
                )
                return None
                
            response_json = response.json()
            
            # Извлекаем содержимое ответа
            if "choices" not in response_json or len(response_json["choices"]) == 0:
                calendar_logger.log_error(
                    Exception(f"Invalid API response format: {response_json}"),
                    "inference.process_request - API response format"
                )
                return None
                
            content = response_json["choices"][0]["message"]["content"].strip()
            
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                # Логируем ответ от LLM
                calendar_logger.log_llm_response(content, parsed_data)
                
                # Добавляем время обработки в название встречи для отладки
                if "title" in parsed_data:
                    parsed_data["title"] = f"{parsed_data['title']} [⏱{processing_time:.2f}s]"
                
                # Создаем объект CalendarEvent из parsed_data
                return CalendarEvent(**parsed_data)
            else:
                calendar_logger.log_error(
                    Exception(f"No JSON found in response: {content}"),
                    "inference.process_request - JSON extraction"
                )
                return None
                
        except requests.exceptions.RequestException as e:
            calendar_logger.log_error(e, "inference.process_request - API request exception")
        except json.JSONDecodeError as e:
            calendar_logger.log_llm_response(content if 'content' in locals() else "No content", None)
            calendar_logger.log_error(e, "inference.process_request - JSON parsing")
        except Exception as e:
            calendar_logger.log_error(e, "inference.process_request - General exception")

        return None
