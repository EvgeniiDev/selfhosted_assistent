import os
import asyncio
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from calendar_service import CalendarService


class TelegramBot:
    def __init__(self, token: str, model_path: str, credentials_path: str = "credentials.json"):
        self.token = token
        self.calendar_service = CalendarService(model_path, credentials_path)
        self.application = Application.builder().token(token).build()
        self._setup_handlers()

    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        self.application.add_handler(
            CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        welcome_message = (
            "Привет! Я ассистент для создания событий в Google Calendar.\n\n"
            "Просто напишите мне что-то вроде:\n"
            "• 'Встреча с командой завтра в 14:00 на час'\n"
            "• 'Обед каждый день в 13:00 на 30 минут'\n"
            "• 'Планерка в понедельник в 10:00'\n\n"
            "Используйте /help для получения дополнительной информации."
        )
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_message = (
            "Как использовать бота:\n\n"
            "Отправьте мне описание события, которое нужно создать в календаре.\n"
            "Вы можете указать:\n"
            "• Название события (обязательно)\n"
            "• Описание\n"
            "• Время начала\n"
            "• Время окончания или длительность\n"
            "• Повторяемость (каждый день, каждую неделю и т.д.)\n\n"
            "Примеры:\n"
            "• 'Встреча с клиентом завтра в 15:00 длительностью 2 часа'\n"
            "• 'Спортзал каждый понедельник в 19:00'\n"
            "• 'Обед сегодня в 13:00-14:00'\n"
        )
        await update.message.reply_text(help_message)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        user_message = update.message.text

        # Показываем, что бот обрабатывает запрос
        await update.message.reply_text("Обрабатываю ваш запрос...")

        try:
            # Обрабатываем запрос через календарный сервис
            result = self.calendar_service.process_user_request(user_message)

            if result.get('success'):
                response = f"✅ {result['message']}"
                if result.get('event_link'):
                    response += f"\n\n🔗 [Ссылка на событие]({result['event_link']})"
            else:
                response = f"❌ {result['message']}"

            await update.message.reply_text(response, parse_mode='Markdown')

        except Exception as e:
            error_message = f"❌ Произошла ошибка: {str(e)}"
            await update.message.reply_text(error_message)

    def run(self):
        """Запуск бота"""
        print("Запуск Telegram бота...")
        self.application.run_polling()


def main():
    # Получаем настройки из переменных окружения
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    model_path = os.getenv(
        'MODEL_PATH', './models/saiga_gemma3_12b_q4_k_m.gguf')
    credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')

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
