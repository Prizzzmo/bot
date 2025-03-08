
#!/bin/bash

# Установочный скрипт для исторического образовательного Telegram бота
# Этот скрипт устанавливает все необходимые зависимости для проекта

echo "Начинаем установку Исторического образовательного Telegram бота..."
echo "------------------------------------------------------"

# Обновление системы
echo "Обновление пакетов системы..."
sudo apt update
sudo apt upgrade -y

# Установка Python и базовых зависимостей
echo "Установка Python и базовых зависимостей..."
sudo apt install -y python3 python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools git

# Установка библиотек для работы с графикой и геоданными
echo "Установка библиотек для работы с графикой и геоданными..."
sudo apt install -y libgeos-dev libproj-dev proj-data proj-bin libcairo2-dev libgirepository1.0-dev pkg-config python3-cairo-dev

# Проверка наличия файла requirements.txt
if [ -f "requirements.txt" ]; then
    echo "Установка Python зависимостей из requirements.txt..."
    pip3 install -r requirements.txt
else
    echo "ОШИБКА: Файл requirements.txt не найден!"
    echo "Пожалуйста, убедитесь, что вы находитесь в корневой директории проекта."
    exit 1
fi

# Проверка и создание .env файла, если он не существует
if [ ! -f ".env" ]; then
    echo "Создание файла .env..."
    echo "# Токен вашего Telegram бота (получите у @BotFather в Telegram)" > .env
    echo "TELEGRAM_TOKEN=замените_на_ваш_токен" >> .env
    echo "" >> .env
    echo "# API ключ Google Gemini (получите на https://ai.google.dev/)" >> .env
    echo "GEMINI_API_KEY=замените_на_ваш_ключ" >> .env
    
    echo "Файл .env создан. Пожалуйста, отредактируйте его и добавьте ваши токены."
else
    echo "Файл .env уже существует."
fi

# Создание директорий, если они не существуют
echo "Проверка необходимых директорий..."
mkdir -p logs
mkdir -p generated_maps
mkdir -p backups

# Установка прав на выполнение для main.py
chmod +x main.py

echo "------------------------------------------------------"
echo "Установка завершена!"
echo ""
echo "Для запуска бота выполните: python3 main.py"
echo "Для настройки автозапуска используйте инструкции в docs/linux_installation.md"
