"""
Провайдер для локальной модели (LM Studio)
"""

import requests
from typing import Optional
from logger import calendar_logger


class LocalProvider:
    """Простой провайдер для локальной модели"""
    
    def __init__(self, api_url: str = "http://127.0.0.1:1234"):
        self.api_url = api_url
        self.chat_url = f"{api_url}/v1/chat/completions"
        
    def is_available(self) -> bool:
        """Проверка доступности локальной модели"""
        try:
            response = requests.get(f"{self.api_url}/v1/models", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def generate(self, messages: list, model_id: str = "local-model") -> Optional[str]:
        """Генерация ответа от локальной модели"""
        try:
            response = requests.post(
                self.chat_url,
                json={
                    "model": model_id,
                    "messages": messages,
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"].strip()
                    calendar_logger.info("Local model response received")
                    return content
            
            calendar_logger.warning(f"Local model failed: {response.status_code}")
            return None
            
        except Exception as e:
            calendar_logger.log_error(e, "LocalProvider.generate")
            return None
