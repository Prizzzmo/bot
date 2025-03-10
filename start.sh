#!/bin/bash

echo "=== Запуск исторического образовательного проекта ==="
echo "Проверка зависимостей и запуск приложения"
echo "------------------------------------------------------"

# Проверка и установка зависимостей Python
check_and_install_dependencies() {
  echo "Проверка Python зависимостей..."

  if [ -f "requirements.txt" ]; then
    python3 -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
      echo "ОШИБКА: Не удалось установить зависимости из requirements.txt"
      exit 1
    fi
    echo "✅ Все Python зависимости установлены"
  else
    echo "ОШИБКА: Файл requirements.txt не найден!"
    exit 1
  fi
}

# Проверка наличия API ключей
check_api_keys() {
  echo "Проверка API ключей..."

  # Проверка наличия .env файла
  if [ ! -f ".env" ]; then
    echo "⚠️ Файл .env не найден. Создание примера файла..."
    echo "# Токен вашего Telegram бота (получите у @BotFather в Telegram)" > .env
    echo "TELEGRAM_TOKEN=замените_на_ваш_токен" >> .env
    echo "" >> .env
    echo "# API ключ Google Gemini (получите на https://ai.google.dev/)" >> .env
    echo "GEMINI_API_KEY=замените_на_ваш_ключ" >> .env

    echo "⚠️ Пожалуйста, отредактируйте файл .env и добавьте ваши токены"
  fi

  # Проверка наличия gemini_api_keys.py
  if [ ! -f "gemini_api_keys.py" ]; then
    echo "⚠️ Файл gemini_api_keys.py не найден. Создание примера файла..."
    echo "# API ключи для доступа к Google Gemini" > gemini_api_keys.py
    echo "GEMINI_API_KEYS = [" >> gemini_api_keys.py
    echo "    'API_KEY_1'," >> gemini_api_keys.py
    echo "    # Добавьте дополнительные ключи по необходимости" >> gemini_api_keys.py
    echo "]" >> gemini_api_keys.py

    echo "⚠️ Пожалуйста, отредактируйте файл gemini_api_keys.py и добавьте ваши ключи Gemini API"
  fi
}

# Проверка наличия необходимых директорий
check_directories() {
  echo "Проверка необходимых директорий..."

  # Создание директорий, если они не существуют
  mkdir -p logs
  mkdir -p generated_maps
  mkdir -p backups
  mkdir -p history_db_generator/backups
  mkdir -p history_db_generator/temp

  echo "✅ Все необходимые директории созданы"
}

# Чистка временных файлов и кэша
cleanup_cache() {
  echo "Очистка временных файлов и кэша..."

  if [ -f "cleanup.py" ]; then
    python3 cleanup.py --temp --cache
    if [ $? -eq 0 ]; then
      echo "✅ Кэш и временные файлы очищены"
    fi
  fi
}

# Функция для запуска приложения
run_application() {
  echo "------------------------------------------------------"
  echo "Запуск приложения..."

  # Проверяем наличие файла run_webapp.py для запуска веб-сервера
  if [ -f "run_webapp.py" ]; then
    echo "Запуск веб-сервера..."
    # Запускаем веб-сервер для карты в фоновом режиме
    python3 run_webapp.py &

    # Запускаем основного бота
    python3 main.py
  # Если есть файл main.py, запускаем его (телеграм бот)
  elif [ -f "main.py" ]; then
    echo "Запуск основного приложения (Telegram бот)..."
    python3 main.py
  else
    echo "ОШИБКА: Не найдены файлы запуска (run_webapp.py или main.py)"
    exit 1
  fi
}

# Главная функция
main() {
  check_and_install_dependencies
  check_api_keys
  check_directories
  cleanup_cache
  run_application
}

# Запуск главной функции
main

#!/bin/bash

# Убедимся что скрипт останавливается при ошибках
set -e

# Проверка наличия нужных файлов
if [ ! -f "admins.json" ]; then
    echo "Файл admins.json не найден. Создаю файл со стандартными настройками..."
    echo '{"admin_ids": [], "super_admin_ids": []}' > admins.json
fi

# Очистка кэша перед запуском (если указан параметр)
if [ "$1" == "--clear-cache" ]; then
    echo "Очистка кэша..."
    python clear_cache.py
fi

# Запуск основного скрипта
echo "Запуск бота..."
python main.py

# Проверяем наличие файла перезапуска
if [ -f "bot.restart" ]; then
    echo "Обнаружен запрос на перезапуск бота..."
    rm -f "bot.restart"
    echo "Перезапуск..."
    exec "$0"
fi