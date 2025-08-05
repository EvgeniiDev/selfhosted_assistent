import json
import time
from typing import Dict, Any, Optional
from datetime import datetime
from llama_cpp import Llama
from logger import calendar_logger


SYSTEM_PROMPT = """Ты — ассистент для создания событий в календаре. Анализируй запросы пользователя и извлекай информацию о событии.

Ты получаешь текущее время в начале каждого запроса. Используй его для интерпретации относительных дат и времен.

Верни результат ТОЛЬКО в формате JSON со следующими полями:
- title (обязательно): название события
- description (опционально): описание события  
- start_time (обязательно): время начала в формате ISO 8601 (YYYY-MM-DDTHH:MM:SS)
- end_time (опционально): время окончания в формате ISO 8601
- duration_minutes (опционально): длительность в минутах вместо end_time
- recurrence (опционально): тип повторения события. Возможные значения:
  * "Daily" - каждый день
  * "Weekly on [день недели]" - еженедельно в указанный день (например, "Weekly on Monday")
  * "Monthly on the first [день недели]" - ежемесячно в первый указанный день недели
  * "Annually on [месяц день]" - ежегодно в указанную дату (например, "Annually on August 7")
  * "Every weekday (Monday to Friday)" - каждый рабочий день
  Если текущий день недели не указан явно, используй текущий день недели

Если время не указано, используй разумные значения по умолчанию (например, 10:00 для рабочих встреч, 19:00 для личных событий).

Пример ответа:
{"title": "Встреча с командой", "start_time": "2025-08-04T14:00:00", "duration_minutes": 60, "recurrence": "Weekly on Monday"}"""


class CalendarInference:
    def __init__(self, model_path: str, n_ctx: int = 8192):
        self.model = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_parts=1,
            verbose=False,
        )

    def process_request(self, user_message: str) -> Optional[Dict[str, Any]]:
        """Обрабатывает запрос пользователя и возвращает JSON с данными события"""
        # Добавляем текущее время в промт пользователя
        current_time = datetime.now()
        current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S (%A)")
        
        enhanced_message = f"Текущее время: {current_time_str}\n\nЗапрос пользователя: {user_message}"
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": enhanced_message}
        ]

        # Логируем промт, отправляемый в LLM
        calendar_logger.log_llm_prompt(enhanced_message, SYSTEM_PROMPT)

        # Засекаем время начала обработки
        start_time = time.time()

        response = self.model.create_chat_completion(
            messages,
            temperature=0.3,
            top_k=30,
            top_p=0.9,
            max_tokens=512,
            stop=["User:", "\n\n"]
        )

        # Вычисляем время обработки
        processing_time = time.time() - start_time
        calendar_logger.info(f"LLM processing time: {processing_time:.2f} seconds")

        content = response["choices"][0]["message"]["content"].strip()

        try:
            # Извлекаем JSON из ответа
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                # Логируем ответ от LLM
                calendar_logger.log_llm_response(content, parsed_data)
                
                return parsed_data
        except (json.JSONDecodeError, ValueError) as e:
            # Логируем ошибку парсинга
            calendar_logger.log_llm_response(content, None)
            calendar_logger.log_error(e, "inference.process_request - JSON parsing")

        return None
