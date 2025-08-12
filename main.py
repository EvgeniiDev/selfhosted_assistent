#!/usr/bin/env python3
"""
Главный файл для запуска Google Calendar Assistant

test with prompt : напомни завтра позвонить в банк в 17 часов

qwen/qwen3-30b-a3b-2507@3q_L - 13.4
qwen3-30b-a3b-instruct-2507@q3_k_s - 14.7
qwen3-30b-a3b-instruct-2507@q2_k - 19 токенов в сек / 16.6
qwen3-30b-a3b-instruct-2507@q2_k_l - 18.5
qwen3-30b-a3b-instruct-2507-q2ks-mixed-autoround - 17.7
qwen3-30b-a3b-instruct-2507@iq2_m - 10.5 
qwen3-30b-a3b-instruct-2507@iq2_xxs - 10.5
qwen3-30b-a3b-instruct-2507@iq1_s -- 11
qwen3-30b-a3b-instruct-2507@iq1_m - 12.4
saiga_gemma3_12b_gguf@q4_k_m - 4
google/gemma-3n-e4b@q4_k_m - 10
gemma-3n-e4b-it-text@q6_k - 8.4
gemma-3n-e4b-it-text@q8_0 - 6.5
qwen/qwen3-1.7b@Q6_K- 44 т\с 20 но с русским почти никак, тупит на времени
cotype-nano - 18.8 не очень понимает промт
qwen/qwen3-4b@Q4_k_M - 11 плохо с промтами
refalmachine/ruadaptqwen3-4b-instruct-gguf/q4_k_s.gguf - 11 но долго из-за thinking
euromoe-2.6b-a0.6b-instruct-preview -- 44 т с но возвращает бред 
t-lite-it-1.0 - 5 т с
baidu/ernie-4.5-21b-a3b - 13 тс но продолбало минуты
devstral-small-2507_gguf - 2.5 товена но ок
Best-smal-LLM-GGUF/Gemma3-4B-Medical-COT-SFT-2kstep-4kcol.Q6_K (gemma3) - 10  t\s



🎯 Общая точность: 86.7% (26/30)
⚡ Среднее время классификации: 0.643с
📊 Медиана времени: 0.639с
🕐 Общее время бенчмарка: 19.28с
📝 Всего тестов: 30
🔥 Скорость: 1.6 классификаций/сек

"""

from telegram_bot import TelegramBot
import os

def main():
    # Получаем настройки из переменных окружения
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not telegram_token:
        print("Ошибка: Установите переменную окружения TELEGRAM_BOT_TOKEN")
        return

    bot = TelegramBot(telegram_token)
    bot.run()

if __name__ == "__main__":
    main()
