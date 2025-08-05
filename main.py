#!/usr/bin/env python3
"""
Главный файл для запуска Google Calendar Assistant
"""

from telegram_bot import TelegramBot
import os


def main():
    # Получаем настройки из переменных окружения
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    model_path = os.getenv('MODEL_PATH')
    credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH')

    if not telegram_token:
        print("Ошибка: Установите переменную окружения TELEGRAM_BOT_TOKEN")
        return

    if not os.path.exists(model_path):
        print(f"Ошибка: Модель не найдена по пути {model_path}")
        return

    if not os.path.exists(credentials_path):
        print(
            f"Ошибка: Файл учетных данных Google не найден: {credentials_path}")
        return

    bot = TelegramBot(telegram_token, model_path, credentials_path)
    bot.run()

if __name__ == "__main__":
    main()
