import json
from typing import Optional, Union
from datetime import datetime
from logger import calendar_logger
from models import CalendarEvent, Note
from llm_inference import ModelRouter


CLASSIFICATION_PROMPT = """
Сlassify text into one of these categories:

- **calendar_event**: mentions specific time, date, meetings, appointments, reminders with time constraints
- **note**: general information to remember, ideas, thoughts, lists, anything without specific time
- **unknown**: unclear or ambiguous requests

Respond with ONLY one word: calendar_event, note, or unknown
"""

CALENDAR_EVENT_PROMPT = """
You are a calendar event extractor. The user wants to create a calendar event. Extract event details and return ONLY a JSON response.

Return exactly this JSON structure:
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

## Rules:
1. Assume all times are in the user's local time zone
2. If **end time** is specified → fill `end_time`, set `duration_minutes` = null
3. If **duration** is specified → fill `duration_minutes`, set `end_time` = null
4. If **neither** is specified → set `duration_minutes` = 60, `end_time` = null

## Recurrence values:
- `null` - one-time event
- `"Daily"` - every day
- `"Weekly on [day of week]"` - weekly
- `"Monthly on the first [day of week]"` - monthly
- `"Annually on [month day]"` - yearly
- `"Every weekday (Monday to Friday)"` - workdays

For dates without year, assume current year or next occurrence if date has passed.
"""

NOTE_PROMPT = """
Ты — форматтер заметок. Пользователь хочет сохранить заметку. Сформируй ответ строго в виде JSON и ничего больше.

Верни ровно такую JSON-структуру:
{
  "type": "note",
  "data": {
    "title": "string",
    "content": "string",
    "created_at": "YYYY-MM-DDTHH:MM:SS",
    "tags": ["string", "string"] or null
  }
}

Правила для "content":
1) Не изменяй смысл, факты, порядок и объём информации. Ничего не добавляй и не удаляй.
2) Исправляй только:
   - заглавные буквы в начале предложений и имен собственных,
   - знаки препинания,
   - опечатки и орфографические ошибки в русских словах.
3) Не перефразируй, не сокращай и не расширяй формулировки.
4) Сохраняй исходные абзацы, переносы строк, списки, числа, даты, ссылки, эмодзи и форматирование (кроме исправлений из п.2).
5) Фрагменты на других языках не переводить; менять только пунктуацию вокруг них при необходимости.
6) Нормализуй пробелы: один пробел между словами, без пробелов перед знаками препинания, ставь пробел после знаков, где это требуется.

Правила для "title":
- Короткий и описательный (3–7 слов).
- Не содержит новых фактов, только отражает суть заметки.

Правила для "tags":
- Извлекай релевантные теги при наличии (не более 3); иначе null.
- Теги — короткие существительные в нижнем регистре, без символов "#", без повторов.

Правила для "created_at":
- Используй текущие локальные дату и время в формате YYYY-MM-DDTHH:MM:SS.

Требования к ответу:
- Верни ТОЛЬКО JSON, без текста, пояснений, кода или бэктиков.
- Строгий JSON: двойные кавычки, без лишних запятых; экранируй спецсимволы.
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
        """Обрабатывает запрос пользователя в два этапа: классификация -> обработка"""
        current_time = datetime.now()
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S (%A)")
        
        try:
            # Этап 1: Быстрая классификация типа запроса
            classification = self._classify_request(user_message)
            
            if classification == "unknown":
                calendar_logger.warning(f"Unknown request type for: {user_message} request_classifier.classify - unknown type")
                classification = "note"
            
            # Этап 2: Специализированная обработка в зависимости от типа
            enhanced_message = f"""
            ## Input Data
            - Current date: {current_time_str}
            - User query: {user_message}
            """
            
            match classification:
                case "calendar_event":
                    return self._process_calendar_event(enhanced_message)
                case "note":
                    return self._process_note(enhanced_message, current_time)
                case _:
                    calendar_logger.log_error(
                        Exception(f"Unexpected classification: {classification}"),
                        "request_classifier.process_request - classification"
                    )
                    return None
                    
        except Exception as e:
            calendar_logger.log_error(e, "request_classifier.process_request - General exception")
            return None

    def _classify_request(self, user_message: str) -> str:
        """Первый этап: быстрая классификация типа запроса"""
        try:
            # Используем короткий промт для классификации
            classification_response = self.router.generate(
                user_message, 
                CLASSIFICATION_PROMPT, 
                is_private=True
            )
            
            if not classification_response:
                return "unknown"
            
            # Извлекаем классификацию из ответа
            classification = classification_response.strip().lower()
            
            # Проверяем, что получили валидную классификацию
            valid_types = {"calendar_event", "note", "unknown"}
            if classification in valid_types:
                calendar_logger.info(f"Request classified as: {classification}")
                return classification
            else:
                calendar_logger.warning(f"Invalid classification received: {classification}")
                return "unknown"
                
        except Exception as e:
            calendar_logger.log_error(e, "request_classifier._classify_request")
            return "unknown"

    def _process_calendar_event(self, enhanced_message: str) -> Optional[CalendarEvent]:
        """Второй этап: обработка календарного события"""
        try:
            content = self.router.generate(enhanced_message, CALENDAR_EVENT_PROMPT, is_private=True)
            
            if not content:
                return None
            
            parsed_data = self._extract_json_from_response(content)
            if parsed_data and parsed_data.get('type') == 'calendar_event':
                return CalendarEvent(**parsed_data['data'])
            
            return None
            
        except Exception as e:
            calendar_logger.log_error(e, "request_classifier._process_calendar_event")
            return None

    def _process_note(self, enhanced_message: str, current_time: datetime) -> Optional[Note]:
        """Второй этап: обработка заметки"""
        try:
            content = self.router.generate(enhanced_message, NOTE_PROMPT, is_private=True)
            
            if not content:
                return None
            
            parsed_data = self._extract_json_from_response(content)
            if parsed_data and parsed_data.get('type') == 'note':
                return Note(**parsed_data['data'])
            
            return None
            
        except Exception as e:
            calendar_logger.log_error(e, "request_classifier._process_note")
            return None

    def _extract_json_from_response(self, content: str) -> Optional[dict]:
        """Извлекает и парсит JSON из ответа модели"""
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                # Логируем структурированный ответ
                calendar_logger.log_llm_response(content, parsed_data)
                return parsed_data
            else:
                calendar_logger.log_error(
                    Exception(f"No JSON found in response: {content}"),
                    "request_classifier._extract_json_from_response"
                )
                return None
                
        except json.JSONDecodeError as e:
            calendar_logger.log_llm_response(content, None)
            calendar_logger.log_error(e, "request_classifier._extract_json_from_response - JSON parsing")
            return None
