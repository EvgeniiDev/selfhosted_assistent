#!/usr/bin/env python3
"""
Главный файл для запуска Google Calendar Assistant

test with prompt : напомни завтра позвонить в банк в 17 часов

qwen/qwen3-30b-a3b-2507@3q_L - 13.4
qwen3-30b-a3b-instruct-2507@q3_k_s - 14.7
qwen3-30b-a3b-instruct-2507@q2_k - 19 токенов в сек / 16.6
qwen3-30b-a3b-instruct-2507@q2_k_l - 18.5
qwen3-30b-a3b-instruct-2507@iq2_m - 10.5 
qwen3-30b-a3b-instruct-2507@iq2_xxs - 10.5
qwen3-30b-a3b-instruct-2507@iq1_s -- 11
qwen3-30b-a3b-instruct-2507@iq1_m - 12.4
saiga_gemma3_12b_gguf@q4_k_m - 4

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
