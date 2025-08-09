"""
Провайдер для OpenRouter API
"""

import os
import requests
from typing import Optional
from logger import calendar_logger


class OpenRouterProvider:
    """провайдер для OpenRouter"""
    
    def __init__(self, api_url: str = "https://openrouter.ai/api/v1/chat/completions"):
        self.api_url = api_url
        self.api_key = os.getenv('OPEN_ROUTER_API_KEY')
        
    def is_available(self) -> bool:
        """Проверка доступности OpenRouter"""
        return bool(self.api_key)
    
    def generate(self, messages: list, model_id: str) -> Optional[str]:
        """Генерация ответа от OpenRouter модели"""
        if not self.api_key:
            calendar_logger.warning("OpenRouter API key not found")
            return None
            
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model_id,
                    "messages": messages
                },
                timeout=120
            )
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"].strip()
                    calendar_logger.info(f"OpenRouter response received: {model_id}")
                    return content
            
            calendar_logger.warning(f"OpenRouter failed: {response.status_code} - {response.text}")
            return None
            
        except Exception as e:
            calendar_logger.log_error(e, f"OpenRouterProvider.generate - {model_id}")
            return None
