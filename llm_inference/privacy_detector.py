"""
Определитель приватности текста на основе регулярных выражений
"""

import re
from logger import calendar_logger


class PrivacyDetector:
    """Определитель приватности сообщений"""
    
    def __init__(self):
        # Паттерны для публичных сообщений (имеют приоритет)
        self.public_patterns = [
            r'(общий вопрос|публично|всем известно|общедоступн)',
            r'(википедия|история|наука|факт|общие знания)',
            r'(погода|новости|курс валют|расписание)',
            r'(рецепт|инструкция|как сделать|объясни всем)',
            r'(переведи|перевод|translate)',
            r'(что такое|кто такой|когда произошло)',
            r'(расскажи про|информация о)'
        ]
        
        # Паттерны для приватных сообщений
        self.private_patterns = [
            r'(личн|приват|секрет|конфиденц|не говори никому)',
            r'(мой|моя|моё|мне|я думаю|я чувствую|мои проблемы)',
            r'(пароль|логин|токен|ключ|api|секретный)',
            r'(доход|зарплата|деньги|финанс|банк|счет)',
            r'(здоровье|болезнь|врач|лечение|симптом)',
            r'(семья|родители|дети|жена|муж|родственник)',
            r'(личные данные|адрес|телефон|email|почта)',
            r'(между нами|не расскажешь|только тебе|в секрете)',
            r'(привет|спасибо|как дела|пока|до свидания)'
        ]
        
        calendar_logger.info("PrivacyDetector initialized")
    
    def is_private(self, text: str) -> bool:
        """
        Определяет, является ли сообщение приватным
        
        Args:
            text: Текст сообщения
            
        Returns:
            True если сообщение приватное, False если публичное
        """
        text_lower = text.lower()
        
        # Сначала проверяем публичные паттерны (приоритет)
        for pattern in self.public_patterns:
            if re.search(pattern, text_lower):
                calendar_logger.info(f"Public message detected: '{text[:50]}...'")
                return False
        
        # Затем проверяем приватные паттерны
        for pattern in self.private_patterns:
            if re.search(pattern, text_lower):
                calendar_logger.info(f"Private message detected: '{text[:50]}...'")
                return True
        
        # По умолчанию считаем приватным для безопасности
        calendar_logger.info(f"Default private: '{text[:50]}...'")
        return True
