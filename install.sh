
#!/bin/bash

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Starting installation of History Educational Bot...${NC}"

# Функция для проверки успешности выполнения команды
check_success() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1 successful${NC}"
    else
        echo -e "${RED}✗ $1 failed${NC}"
        exit 1
    fi
}

# 0. Клонирование репозитория
echo -e "${YELLOW}Cloning repository from GitHub...${NC}"
if [ -d "bot" ]; then
    rm -rf bot
fi
git clone https://github.com/Prizzzmo/bot.git
cd bot
check_success "Repository cloning"

# 1. Обновление системы
echo -e "${YELLOW}Updating system packages...${NC}"
sudo apt update
sudo apt upgrade -y
check_success "System update"

# 2. Установка базовых зависимостей
echo -e "${YELLOW}Installing basic dependencies...${NC}"
sudo apt install -y python3 python3-pip python3-dev build-essential git
check_success "Basic dependencies installation"

# 3. Установка системных библиотек
echo -e "${YELLOW}Installing system libraries...${NC}"
sudo apt install -y libssl-dev libffi-dev python3-setuptools libgeos-dev libproj-dev proj-data proj-bin libcairo2-dev libgirepository1.0-dev pkg-config python3-cairo-dev
check_success "System libraries installation"

# 4. Создание необходимых директорий
echo -e "${YELLOW}Creating required directories...${NC}"
mkdir -p logs
mkdir -p generated_maps
mkdir -p backups
mkdir -p history_db_generator/backups
mkdir -p history_db_generator/temp
check_success "Directory creation"

# 5. Проверка и установка Python зависимостей
echo -e "${YELLOW}Installing Python dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt
    check_success "Python dependencies installation"
else
    echo -e "${RED}requirements.txt not found!${NC}"
    exit 1
fi

# 6. Создание и настройка конфигурационных файлов
echo -e "${YELLOW}Creating configuration files...${NC}"

# Создание .env файла с токенами из проекта
echo -e "${YELLOW}Creating .env file with tokens...${NC}"
cat > .env << EOL
# Токен Telegram бота
TELEGRAM_TOKEN=6783318815:AAHjX5fy_CU1NRjO1NjrWvWDQjVa-qG1UkA

# API ключи Google Gemini
GEMINI_API_KEY=AIzaSyAuAktN3PCP1EOXHvA4D-4SPvddXSOKNuU

# Настройки логирования
LOG_LEVEL=INFO
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
EOL
check_success "Configuration files creation"

# 7. Настройка прав доступа
echo -e "${YELLOW}Setting up permissions...${NC}"
chmod -R 755 .
chmod +x main.py
chmod +x run_combined.py
check_success "Permissions setup"

# 8. Создание службы systemd
echo -e "${YELLOW}Creating systemd service...${NC}"
SERVICE_FILE="/etc/systemd/system/history-bot.service"

sudo tee $SERVICE_FILE > /dev/null << EOL
[Unit]
Description=History Educational Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/python3 run_combined.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/history-bot.log
StandardError=append:/var/log/history-bot.error.log

[Install]
WantedBy=multi-user.target
EOL

check_success "Systemd service creation"

# 9. Активация и запуск службы
echo -e "${YELLOW}Enabling and starting service...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable history-bot.service
sudo systemctl start history-bot.service
check_success "Service activation"

# 10. Настройка автоматического обновления
echo -e "${YELLOW}Setting up auto-update script...${NC}"
UPDATE_SCRIPT="update.sh"

cat > $UPDATE_SCRIPT << EOL
#!/bin/bash
git pull
pip3 install -r requirements.txt
sudo systemctl restart history-bot.service
EOL

chmod +x $UPDATE_SCRIPT
check_success "Auto-update script creation"

# 11. Проверка статуса службы
echo -e "${YELLOW}Checking service status...${NC}"
sudo systemctl status history-bot.service
check_success "Service status check"

echo -e "${GREEN}Installation completed successfully!${NC}"
echo -e "${YELLOW}To view logs use: journalctl -u history-bot.service -f${NC}"
echo -e "${YELLOW}To update the bot use: ./update.sh${NC}"
