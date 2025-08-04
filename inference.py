import json
from typing import Dict, Any, Optional
from llama_cpp import Llama


SYSTEM_PROMPT = """Ты — ассистент для создания событий в календаре. Анализируй запросы пользователя и извлекай информацию о событии.

Верни результат ТОЛЬКО в формате JSON со следующими полями:
- title (обязательно): название события
- description (опционально): описание события  
- start_time (обязательно): время начала в формате ISO 8601 (YYYY-MM-DDTHH:MM:SS)
- end_time (опционально): время окончания в формате ISO 8601
- duration_minutes (опционально): длительность в минутах вместо end_time
- recurrence (опционально): объект с правилами повторения {"rule": "RRULE:FREQ=DAILY;COUNT=10"}

Если время не указано, используй разумные значения по умолчанию.
Если дата не указана, используй сегодняшний день.

Пример ответа:
{"title": "Встреча с командой", "start_time": "2025-08-04T14:00:00", "duration_minutes": 60}"""


class CalendarInference:
    def __init__(self, model_path: str, n_ctx: int = 8192):
        self.model = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_parts=1,
            verbose=True,
        )

    def process_request(self, user_message: str) -> Optional[Dict[str, Any]]:
        """Обрабатывает запрос пользователя и возвращает JSON с данными события"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]

        response = self.model.create_chat_completion(
            messages,
            temperature=0.3,
            top_k=30,
            top_p=0.9,
            max_tokens=512,
            stop=["User:", "\n\n"]
        )

        content = response["choices"][0]["message"]["content"].strip()

        try:
            # Извлекаем JSON из ответа
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

        return None
