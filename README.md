# Google Calendar Assistant

Ассистент для создания задач и встреч в Google Calendar через Telegram бота с использованием локальной языковой модели.

## Функциональность

- Обработка естественного языка для создания событий в календаре
- **Предварительный просмотр и подтверждение событий перед созданием**
- Поддержка указания времени начала, окончания или длительности
- Создание повторяющихся событий
- Интеграция с Telegram для удобного взаимодействия
- Использование локальной модели IlyaGusev/saiga_gemma3_12b_gguf
- **Полное логирование всех операций в файл**

## Модули

1. **inference.py** - Модуль инференса с системным промптом для обработки запросов пользователя
2. **google_calendar_client.py** - Клиент для работы с Google Calendar API
3. **calendar_service.py** - Сервис, соединяющий инференс и календарь клиент
4. **telegram_bot.py** - Telegram бот для взаимодействия с пользователем
5. **models.py** - Модели данных для событий календаря
6. **utils.py** - Утилиты для работы с датами и временем
7. **logger.py** - Модуль логирования всех операций системы

## Установка и настройка

### 1. Установка зависимостей

#### Windows

Для сборки llama-cpp-python из исходников на Windows требуется установка w64devkit:

1. Скачайте w64devkit с [GitHub релизов](https://github.com/skeeto/w64devkit/releases)
2. Распакуйте в `C:\w64devkit\`
3. Настройте переменные окружения CMAKE:

```powershell
$env:CMAKE_GENERATOR = "MinGW Makefiles"
$env:CMAKE_ARGS = "-DGGML_OPENBLAS=on -DCMAKE_C_COMPILER=C:/w64devkit/bin/gcc.exe -DCMAKE_CXX_COMPILER=C:/w64devkit/bin/g++.exe -DCMAKE_MAKE_PROGRAM=C:/w64devkit/bin/mingw32-make.exe"
$env:PATH = "C:\w64devkit\bin;" + $env:PATH
```

4. Установите зависимости:

```powershell
pip install -r requirements.txt
```

**Поддержка Vulkan (опционально):**
```powershell
$env:CMAKE_ARGS = "-DGGML_VULKAN=on -DCMAKE_C_COMPILER=C:/w64devkit/bin/gcc.exe -DCMAKE_CXX_COMPILER=C:/w64devkit/bin/g++.exe -DCMAKE_MAKE_PROGRAM=C:/w64devkit/bin/mingw32-make.exe"
pip install llama-cpp-python
```

#### Linux/macOS

```bash
pip install -r requirements.txt
```

### 2. Настройка Google Calendar API

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите Google Calendar API
4. Создайте учетные данные (OAuth 2.0 Client ID)
5. Скачайте файл `credentials.json` и поместите в корень проекта

### 3. Настройка Telegram бота

1. Найдите @BotFather в Telegram
2. Создайте нового бота командой `/newbot`
3. Получите токен бота

### 4. Скачивание модели

Скачайте модель IlyaGusev/saiga_gemma3_12b_gguf с квантованием Q4_K_M и поместите в папку `./models/`

### 5. Настройка переменных окружения

Скопируйте `.env.example` в `.env` и заполните необходимые значения:

```bash
cp .env.example .env
```

## Запуск

```bash
python main.py
```

Или

```bash
python telegram_bot.py
```

## Примеры использования

### Создание событий
- "Встреча с командой завтра в 14:00 на час"
- "Обед каждый день в 13:00 на 30 минут" 
- "Планерка в понедельник в 10:00"
- "Стоматолог 15 августа в 16:30 описание: профилактический осмотр"

### Процесс создания
1. Отправьте описание события боту
2. Получите структурированное сообщение с деталями события
3. Выберите действие:
   - ✅ **Подтвердить** - создать событие в календаре
   - ❌ **Отменить** - отменить создание
   - ✏️ **Редактировать** - получить текст для редактирования

## Структура проекта

```
selfhosted_assistent/
├── main.py                    # Точка входа
├── inference.py               # Модуль инференса
├── google_calendar_client.py  # Google Calendar клиент
├── calendar_service.py        # Сервис календаря
├── telegram_bot.py           # Telegram бот
├── models.py                 # Модели данных
├── utils.py                  # Утилиты
├── logger.py                 # Модуль логирования
├── requirements.txt          # Зависимости Python
├── .env.example             # Пример настроек
├── README.md               # Документация
└── credentials.json        # Учетные данные Google (не в репозитории)
```