from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from calendar_service import CalendarService
from models import CalendarEvent
from logger import calendar_logger


class TelegramBot:
    def __init__(self, token: str, model_path: str, credentials_path: str = "credentials.json"):
        self.token = token
        self.calendar_service = CalendarService(model_path, credentials_path)
        self.application = Application.builder().token(token).build()
        # Хранилище для ожидающих подтверждения событий
        self.pending_events = {}
        self._setup_handlers()

    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        self.application.add_handler(
            CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        welcome_message = (
            "Привет! Я ассистент для создания событий в Google Calendar.\n\n"
            "Просто напишите мне что-то вроде:\n"
            "• 'Встреча с командой завтра в 14:00 на час'\n"
            "• 'Обед каждый день в 13:00 на 30 минут'\n"
            "• 'Планерка в понедельник в 10:00'\n\n"
            "Я покажу вам детали события для подтверждения перед созданием.\n"
            "Используйте /help для получения дополнительной информации."
        )
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_message = (
            "Как использовать бота:\n\n"
            "1️⃣ Отправьте мне описание события для календаря\n"
            "2️⃣ Проверьте детали события в предварительном просмотре\n"
            "3️⃣ Нажмите \"✅ Подтвердить\" для создания или \"❌ Отменить\"\n"
            "4️⃣ Если что-то не так, нажмите \"✏️ Редактировать\"\n\n"
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
        user_id = str(update.effective_user.id) if update.effective_user else None
        username = update.effective_user.username if update.effective_user else None

        # Логируем запрос пользователя
        calendar_logger.log_user_request(user_id, username, user_message)

        # Показываем, что бот обрабатывает запрос
        await update.message.reply_text("Обрабатываю ваш запрос...")

        try:
            # Обрабатываем запрос через календарный сервис
            result = self.calendar_service.process_user_request(user_message)

            if result.get('success') and result.get('action') == 'confirm':
                # Событие готово к подтверждению
                event = result['event']
                message = result['message']
                
                # Сохраняем событие для подтверждения
                event_id = f"{user_id}_{update.message.message_id}"
                self.pending_events[event_id] = event
                
                # Создаем клавиатуру с кнопками
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{event_id}"),
                        InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{event_id}")
                    ],
                    [
                        InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{event_id}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
                
            elif result.get('success'):
                response = f"✅ {result['message']}"
                if result.get('event_link'):
                    response += f"\n\n🔗 [Ссылка на событие]({result['event_link']})"
                await update.message.reply_text(response, parse_mode='Markdown')
            else:
                response = f"❌ {result['message']}"
                await update.message.reply_text(response)

        except Exception as e:
            calendar_logger.log_error(e, "telegram_bot.handle_message")
            error_message = f"❌ Произошла ошибка: {str(e)}"
            await update.message.reply_text(error_message)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на inline кнопки"""
        query = update.callback_query
        await query.answer()

        data = query.data
        
        if data.startswith("confirm_"):
            event_id = data.replace("confirm_", "")
            await self._confirm_event(query, event_id)
        elif data.startswith("cancel_"):
            event_id = data.replace("cancel_", "")
            await self._cancel_event(query, event_id)
        elif data.startswith("edit_"):
            event_id = data.replace("edit_", "")
            await self._edit_event(query, event_id)

    async def _confirm_event(self, query, event_id: str):
        """Подтверждение создания события"""
        if event_id not in self.pending_events:
            await query.edit_message_text("❌ Событие не найдено или уже обработано.")
            return

        event = self.pending_events[event_id]
        
        try:
            # Создаем событие в календаре
            result = self.calendar_service.create_confirmed_event(event)
            
            if result.get('success'):
                response = f"✅ {result['message']}"
                if result.get('event_link'):
                    response += f"\n\n🔗 [Ссылка на событие]({result['event_link']})"
            else:
                response = f"❌ {result['message']}"
            
            await query.edit_message_text(response, parse_mode='Markdown')
            
            # Удаляем событие из ожидающих
            del self.pending_events[event_id]
            
        except Exception as e:
            calendar_logger.log_error(e, "telegram_bot._confirm_event")
            await query.edit_message_text(f"❌ Произошла ошибка при создании события: {str(e)}")

    async def _cancel_event(self, query, event_id: str):
        """Отмена создания события"""
        if event_id in self.pending_events:
            del self.pending_events[event_id]
        
        await query.edit_message_text("❌ Создание события отменено.")

    async def _edit_event(self, query, event_id: str):
        """Редактирование события"""
        if event_id not in self.pending_events:
            await query.edit_message_text("❌ Событие не найдено или уже обработано.")
            return

        event = self.pending_events[event_id]
        
        # Формируем сообщение с данными для редактирования
        edit_message = f"""✏️ **Редактирование события**

Скопируйте, исправьте и отправьте данные в следующем формате:

```
Название: {event.title}
Время: {event.start_time.strftime("%d.%m.%Y %H:%M")}"""

        if event.duration_minutes:
            edit_message += f"\nДлительность: {event.duration_minutes} минут"
        elif event.end_time:
            edit_message += f"\nОкончание: {event.end_time.strftime("%H:%M")}"

        if event.description:
            edit_message += f"\nОписание: {event.description}"

        edit_message += "\n```\n\nИли напишите новый запрос заново."

        await query.edit_message_text(edit_message, parse_mode='Markdown')
        
        # Удаляем текущее событие из ожидающих
        del self.pending_events[event_id]

    def run(self):
        """Запуск бота"""
        print("Запуск Telegram бота...")
        self.application.run_polling()
