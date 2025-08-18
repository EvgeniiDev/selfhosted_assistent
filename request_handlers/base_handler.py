"""
Базовый класс для обработчиков запросов.
"""

import json
from abc import ABC, abstractmethod
from typing import Optional, Any
from logger import calendar_logger
from llm_inference import ModelRouter


class BaseRequestHandler(ABC):
    """Базовый класс для всех обработчиков запросов"""
    
    def __init__(self, router: ModelRouter):
        """
        Инициализация обработчика
        
        Args:
            router: Роутер для работы с LLM моделями
        """
        self.router = router
    
    @abstractmethod
    def get_prompt(self) -> str:
        """Возвращает промт для данного обработчика"""
        pass
    
    @abstractmethod
    def get_handler_name(self) -> str:
        """Возвращает имя обработчика для логирования"""
        pass
    
    @abstractmethod
    def parse_response(self, response_content: str, **kwargs) -> Optional[Any]:
        """
        Парсит ответ модели и возвращает соответствующий объект
        
        Args:
            response_content: Ответ от LLM модели
            **kwargs: Дополнительные параметры для парсинга
            
        Returns:
            Объект соответствующего типа или None при ошибке
        """
        pass
    
    def process(self, enhanced_message: str, is_private: bool, **kwargs) -> Optional[Any]:
        """
        Обрабатывает сообщение с помощью LLM и парсит результат
        
        Args:
            enhanced_message: Улучшенное сообщение с контекстом
            **kwargs: Дополнительные параметры для обработки
            
        Returns:
            Обработанный объект или None при ошибке
        """
        try:
            # Генерируем ответ от модели
            content = self.router.generate(
                enhanced_message, 
                self.get_prompt(), 
                is_private=is_private
            )
            
            if not content:
                calendar_logger.warning(f"{self.get_handler_name()}: Empty response from model")
                return None
            
            # Парсим ответ
            result = self.parse_response(content, **kwargs)
            
            if result is None:
                calendar_logger.warning(f"{self.get_handler_name()}: Failed to parse response")
            
            return result
            
        except Exception as e:
            calendar_logger.log_error(e, f"{self.get_handler_name()}.process")
            return None
    
    def extract_json_from_response(self, content: str) -> Optional[dict]:
        """
        Извлекает и парсит JSON из ответа модели
        
        Args:
            content: Ответ от модели
            
        Returns:
            Словарь с данными или None при ошибке
        """
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
                    f"{self.get_handler_name()}.extract_json_from_response"
                )
                return None
                
        except json.JSONDecodeError as e:
            calendar_logger.log_llm_response(content, None)
            calendar_logger.log_error(e, f"{self.get_handler_name()}.extract_json_from_response - JSON parsing")
            return None
