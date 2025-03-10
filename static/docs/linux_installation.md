
# Руководство по установке проекта на Linux

Этот документ содержит инструкции по установке всех необходимых компонентов для запуска исторического образовательного Telegram бота на системах Linux.

## Предварительные требования

Для работы с проектом вам потребуется:
- Python 3.11 или выше
- Доступ в интернет для загрузки зависимостей
- Telegram Bot Token (получается у @BotFather в Telegram)
- Google Gemini API ключ

## Установка

### 1. Обновление системы

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Установка Python и зависимостей

```bash
sudo apt install -y python3 python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools python3-venv git
```

### 3. Установка дополнительных библиотек для работы с графикой и геоданными

```bash
sudo apt install -y libgeos-dev libproj-dev proj-data proj-bin libcairo2-dev libgirepository1.0-dev pkg-config python3-cairo-dev
```

### 4. Клонирование репозитория

```bash
git clone https://github.com/ваш-пользователь/ваш-репозиторий.git
cd ваш-репозиторий
```

### 5. Установка Python зависимостей

```bash
pip3 install -r requirements.txt
```

## Настройка окружения

### 1. Создание файла с переменными окружения

Создайте файл `.env` в корневой директории проекта со следующим содержимым:

```
# Токен вашего Telegram бота (получите у @BotFather в Telegram)
TELEGRAM_TOKEN=ваш_токен_здесь

# API ключ Google Gemini (получите на https://ai.google.dev/)
GEMINI_API_KEY=ваш_ключ_здесь
```

### 2. Настройка прав администратора (опционально)

Отредактируйте файл `admins.json`, добавив ваш Telegram ID в список админов:

```json
{
    "admin_ids": [ваш_telegram_id],
    "super_admin_ids": [ваш_telegram_id]
}
```

## Запуск бота

### Обычный запуск

```bash
python3 main.py
```

### Запуск в фоновом режиме

```bash
nohup python3 main.py > bot.log 2>&1 &
```

### Автоматический запуск при старте системы (systemd)

1. Создайте файл сервиса:

```bash
sudo nano /etc/systemd/system/history-bot.service
```

2. Добавьте следующее содержимое (замените пути на ваши):

```
[Unit]
Description=History Educational Telegram Bot
After=network.target

[Service]
User=ваш_пользователь
WorkingDirectory=/путь/к/вашему/проекту
ExecStart=/usr/bin/python3 /путь/к/вашему/проекту/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Включите и запустите сервис:

```bash
sudo systemctl enable history-bot.service
sudo systemctl start history-bot.service
```

4. Проверьте статус:

```bash
sudo systemctl status history-bot.service
```

## Решение проблем

### Логи

Логи бота можно найти в директории `logs/`. Для просмотра последних логов используйте:

```bash
tail -f logs/bot.log
```

### Перезапуск

Если бот перестал работать, попробуйте перезапустить его:

```bash
sudo systemctl restart history-bot.service
```

## Обновление бота

1. Перейдите в директорию проекта:

```bash
cd /путь/к/вашему/проекту
```

2. Получите последние изменения:

```bash
git pull
```

3. Обновите зависимости:

```bash
pip3 install -r requirements.txt
```

4. Перезапустите бота:

```bash
sudo systemctl restart history-bot.service
```
