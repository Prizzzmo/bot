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

# Скрипт для запуска и перезапуска бота

# Проверяем наличие файла-индикатора перезапуска
check_restart() {
  if [ -f "bot.restart" ]; then
    echo "Обнаружен файл bot.restart. Перезапуск..."
    rm -f bot.restart
    return 0
  fi
  return 1
}

# Запускаем бота
run_bot() {
  echo "Запуск бота..."
  python main.py
}

# Основной цикл
while true; do
  run_bot
  
  # Проверяем, есть ли файл для перезапуска
  if check_restart; then
    echo "Перезапуск бота..."
    sleep 3  # Небольшая пауза перед перезапуском
    continue
  fi
  
  # Если бот завершился без запроса на перезапуск, выходим из цикла
  echo "Бот завершился. Выход."
  break
done
