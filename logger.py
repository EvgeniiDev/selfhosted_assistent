import logging
import os
import json
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path


class CalendarLogger:
    def __init__(self, log_file: str = "calendar_assistant.log"):
        """Инициализация логгера для календарного ассистента"""
        self.log_file = Path(log_file)
        
        # Создаем директорию для логов если она не существует
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Настройка логгера
        self.logger = logging.getLogger('calendar_assistant')
        self.logger.setLevel(logging.INFO)
        # Отключаем распространение сообщений к корневому логгеру,
        # чтобы избежать дублирования в консоли при наличии root-хендлеров
        self.logger.propagate = False
        
        # Удаляем старые хендлеры если они есть
        for handler in list(self.logger.handlers):
            self.logger.removeHandler(handler)
        
        # Настройка форматтера
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Файловый хендлер
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        
        # Консольный хендлер
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_user_request(self, user_id: Optional[str], username: Optional[str], message: str):
        """Логирование запроса от пользователя из Telegram"""
        log_data = {
            "type": "user_request",
            "user_id": user_id,
            "username": username,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"USER_REQUEST | {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_llm_prompt(self, prompt: str, system_prompt: str):
        """Логирование промта, отправленного в LLM"""
        log_data = {
            "type": "llm_prompt",
            "system_prompt": system_prompt,
            "user_prompt": prompt,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"LLM_PROMPT | {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_llm_response(self, response: str, parsed_data: Optional[Dict[str, Any]] = None):
        """Логирование ответа от LLM"""
        log_data = {
            "type": "llm_response",
            "raw_response": response,
            "parsed_data": parsed_data,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"LLM_RESPONSE | {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_calendar_request(self, event_data: Dict[str, Any]):
        """Логирование запроса к Google Calendar"""
        log_data = {
            "type": "calendar_request",
            "event_data": event_data,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"CALENDAR_REQUEST | {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_calendar_response(self, success: bool, response_data: Dict[str, Any]):
        """Логирование ответа от Google Calendar"""
        log_data = {
            "type": "calendar_response",
            "success": success,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"CALENDAR_RESPONSE | {json.dumps(log_data, ensure_ascii=False)}")
    
    def log_error(self, error: Exception, context: str = ""):
        """Логирование ошибок"""
        log_data = {
            "type": "error",
            "error_message": str(error),
            "error_type": type(error).__name__,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.error(f"ERROR | {json.dumps(log_data, ensure_ascii=False)}")
    
    def info(self, message: str):
        """Общее логирование информационных сообщений"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Логирование предупреждений"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Логирование ошибок (простой формат)"""
        self.logger.error(message)


# Глобальный экземпляр логгера
calendar_logger = CalendarLogger()
