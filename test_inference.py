#!/usr/bin/env python3
"""
Тестовый скрипт для проверки модуля инференса
"""

from inference import CalendarInference
import sys
from pathlib import Path

# Добавляем текущую директорию в путь Python
sys.path.insert(0, str(Path(__file__).parent))


def test_inference(model_path: str):
    """Тестирует модуль инференса"""
    print("Инициализация модели...")

    try:
        inference = CalendarInference(model_path)
        print("Модель загружена успешно!")

        # Тестовые запросы
        test_queries = [
            "Встреча с командой завтра в 14:00 на час",
            "Обед каждый день в 13:00 на 30 минут",
            "Стоматолог 15 августа в 16:30",
            "Планерка в понедельник в 10:00"
        ]

        for query in test_queries:
            print(f"\n--- Тест запроса: '{query}' ---")
            result = inference.process_request(query)

            if result:
                print("Результат:")
                for key, value in result.items():
                    print(f"  {key}: {value}")
            else:
                print("Не удалось обработать запрос")

    except Exception as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    import os

    model_path = os.getenv(
        'MODEL_PATH', './models/saiga_gemma3_12b_q4_k_m.gguf')

    if not os.path.exists(model_path):
        print(f"Модель не найдена: {model_path}")
        print("Укажите путь к модели в переменной окружения MODEL_PATH")
        sys.exit(1)

    test_inference(model_path)
