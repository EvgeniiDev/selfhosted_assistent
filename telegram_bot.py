from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from calendar_service import CalendarService
from voice_service import VoiceService
from logger import calendar_logger


class TelegramBot:
    def __init__(self, token: str, credentials_path: str = "credentials.json"):
        self.token = token
        self.calendar_service = CalendarService(credentials_path)
        self.voice_service = VoiceService(device="cpu")  # Используем CPU для инференса
        self.application = Application.builder().token(token).build()
        # Хранилище для ожидающих подтверждения событий
        self.pending_events = {}
        
        # Настройка разрешенных пользователей
        allowed_users_str = os.getenv('TELEGRAM_ALLOWED_USERS', '').strip()
        if allowed_users_str:
            # Парсим список пользователей (может быть username или user_id)
            self.allowed_users = set()
            for user in allowed_users_str.split(','):
                user = user.strip()
                if user:
                    # Если это число, добавляем как user_id, иначе как username
                    if user.isdigit():
                        self.allowed_users.add(int(user))
                    else:
                        # Убираем @ если есть
                        username = user.lstrip('@').lower()
                        self.allowed_users.add(username)
        else:
            self.allowed_users = None  # None означает разрешено всем
            
        self._setup_handlers()

    def _safe_url_encode(self, url: str) -> str:
        """Безопасное кодирование URL для Telegram"""
        if not url:
            return ""
        
        # Для Telegram лучше использовать HTML формат ссылок
        # или просто возвращать URL как есть для HTML parse_mode
        return url

    def _is_user_allowed(self, update: Update) -> bool:
        """Проверка, разрешен ли пользователь для использования бота"""
        if self.allowed_users is None:
            return True  # Если список не настроен, разрешаем всем
            
        user = update.effective_user
        if not user:
            return False
            
        # Проверяем по user_id
        if user.id in self.allowed_users:
            return True
            
        # Проверяем по username
        if user.username and user.username.lower() in self.allowed_users:
            return True
            
        return False

    async def _send_access_denied_message(self, update: Update):
        """Отправка сообщения о запрете доступа"""
        await update.message.reply_text(
            "❌ У вас нет доступа к этому боту.\n"
            "Обратитесь к администратору для получения разрешения."
        )

    def _setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        self.application.add_handler(
            CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))  # Обработчик голосовых сообщений
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        # Проверка разрешенных пользователей
        if not self._is_user_allowed(update):
            await self._send_access_denied_message(update)
            return
            
        welcome_message = (
            "Привет! Я ассистент для создания событий в Google Calendar.\n\n"
            "Вы можете:\n"
            "📝 Написать текстовое сообщение\n"
            "🎤 Записать голосовое сообщение\n\n"
            "Примеры запросов:\n"
            "• 'Встреча с командой завтра в 14:00 на час'\n"
            "• 'Обед каждый день в 13:00 на 30 минут'\n"
            "• 'Планерка в понедельник в 10:00'\n\n"
            "Я покажу вам детали события для подтверждения перед созданием.\n"
            "Используйте /help для получения дополнительной информации."
        )
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        # Проверка разрешенных пользователей
        if not self._is_user_allowed(update):
            await self._send_access_denied_message(update)
            return
            
        help_message = (
            "Как использовать бота:\n\n"
            "1️⃣ Отправьте мне описание события для календаря:\n"
            "   📝 Текстовое сообщение или 🎤 Голосовое сообщение\n"
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
            "• 'Обед сегодня в 13:00-14:00'\n\n"
            "🎤 Голосовые сообщения автоматически распознаются и обрабатываются как текст."
        )
        await update.message.reply_text(help_message)

    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик голосовых сообщений"""
        # Проверка разрешенных пользователей
        if not self._is_user_allowed(update):
            await self._send_access_denied_message(update)
            return
            
        user_id = str(update.effective_user.id) if update.effective_user else None
        username = update.effective_user.username if update.effective_user else None

        # Показываем, что бот обрабатывает голосовое сообщение
        processing_message = await update.message.reply_text("🎤 Обрабатываю голосовое сообщение...")

        try:
            # Проверяем, загружена ли модель
            if not self.voice_service.is_model_loaded():
                await processing_message.edit_text("❌ Модель распознавания речи не загружена")
                return

            # Получаем голосовое сообщение
            voice = update.message.voice
            voice_file = await context.bot.get_file(voice.file_id)

            # Обновляем статус
            await processing_message.edit_text("🎤 Распознаю речь...")

            # Транскрибируем голосовое сообщение
            transcription = await self.voice_service.transcribe_voice_message(voice_file)

            if not transcription:
                await processing_message.edit_text("❌ Не удалось распознать речь. Попробуйте записать сообщение заново.")
                return

            # Логируем запрос пользователя
            calendar_logger.log_user_request(user_id, username, f"[VOICE] {transcription}")

            # Показываем распознанный текст пользователю
            await processing_message.edit_text(f"🎤 Распознанный текст: *{transcription}*\n\nОбрабатываю запрос...", parse_mode='Markdown')

            # Обрабатываем транскрибированный текст как обычное текстовое сообщение
            await self._process_text_request(update, transcription, processing_message)

        except Exception as e:
            calendar_logger.log_error(e, "telegram_bot.handle_voice_message")
            error_message = f"❌ Произошла ошибка при обработке голосового сообщения: {str(e)}"
            await processing_message.edit_text(error_message)

    async def _process_text_request(self, update: Update, user_message: str, processing_message=None):
        """Общий метод для обработки текстовых запросов"""
        user_id = str(update.effective_user.id) if update.effective_user else None

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
                
                if processing_message:
                    await processing_message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
                
            elif result.get('success'):
                response = f"✅ {result['message']}"
                if result.get('event_link'):
                    response += f"\n\n🔗 <a href=\"{result['event_link']}\">Ссылка на событие</a>"
                
                # Используем HTML parse_mode для корректной обработки ссылок
                if processing_message:
                    await processing_message.edit_text(response, parse_mode='HTML', disable_web_page_preview=True)
                else:
                    await update.message.reply_text(response, parse_mode='HTML', disable_web_page_preview=True)
            else:
                response = f"❌ {result['message']}"
                if processing_message:
                    await processing_message.edit_text(response)
                else:
                    await update.message.reply_text(response)

        except Exception as e:
            calendar_logger.log_error(e, "telegram_bot._process_text_request")
            error_message = f"❌ Произошла ошибка: {str(e)}"
            if processing_message:
                await processing_message.edit_text(error_message)
            else:
                await update.message.reply_text(error_message)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        # Проверка разрешенных пользователей
        if not self._is_user_allowed(update):
            await self._send_access_denied_message(update)
            return
            
        user_message = update.message.text
        user_id = str(update.effective_user.id) if update.effective_user else None
        username = update.effective_user.username if update.effective_user else None

        # Логируем запрос пользователя
        calendar_logger.log_user_request(user_id, username, user_message)

        # Показываем, что бот обрабатывает запрос
        processing_message = await update.message.reply_text("Обрабатываю ваш запрос...")

        # Используем общий метод для обработки
        await self._process_text_request(update, user_message, processing_message)

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
                    response += f"\n\n🔗 <a href=\"{result['event_link']}\">Ссылка на событие</a>"
            else:
                response = f"❌ {result['message']}"

            # Используем HTML parse_mode для корректной обработки ссылок
            await query.edit_message_text(response, parse_mode='HTML', disable_web_page_preview=True)
            
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
        
        # Информация о разрешенных пользователях
        if self.allowed_users is None:
            print("👥 Доступ разрешен всем пользователям")
        else:
            users_count = len(self.allowed_users)
            print(f"🔒 Доступ ограничен для {users_count} пользователь(ей)")
        
        # Проверяем статус модели распознавания речи
        if self.voice_service.is_model_loaded():
            print("✅ Модель распознавания речи загружена успешно")
        else:
            print("⚠️  Модель распознавания речи не загружена. Голосовые сообщения не будут обрабатываться.")
        
        self.application.run_polling()

