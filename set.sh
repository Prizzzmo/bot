
#!/bin/bash

# Обновление системы
echo "Обновление системы..."
sudo yum update -y
sudo yum upgrade -y

# Установка необходимых пакетов
echo "Установка необходимых пакетов..."
sudo yum install -y epel-release
sudo yum install -y python3 python3-pip python3-devel gcc git wget curl

# Установка и настройка firewall
echo "Настройка файервола..."
sudo yum install -y firewalld
sudo systemctl start firewalld
sudo systemctl enable firewalld

# Открытие портов
echo "Открытие необходимых портов..."
sudo firewall-cmd --permanent --add-port=8080/tcp  # Для веб-приложения
sudo firewall-cmd --permanent --add-port=5000/tcp  # Для Flask
sudo firewall-cmd --reload

# Установка Python зависимостей
echo "Установка Python зависимостей..."
pip3 install --upgrade pip
pip3 install python-telegram-bot==13.15
pip3 install requests==2.31.0
pip3 install python-dotenv==1.0.0
pip3 install flask==2.3.3
pip3 install google-generativeai==0.3.1
pip3 install psutil matplotlib folium selenium webdriver-manager pillow docx jinja2 basemap pandas numpy redis pymemcache astor html2text markdown pillow python-docx python-pptx

# Настройка SELinux
echo "Настройка SELinux..."
sudo setsebool -P httpd_can_network_connect 1

# Создание системного сервиса
echo "Создание системного сервиса..."
sudo tee /etc/systemd/system/history-bot.service << EOF
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
EOF

# Создание лог-директории и настройка прав
echo "Настройка логирования..."
sudo mkdir -p /var/log/history-bot/
sudo chown -R $USER:$USER /var/log/history-bot/

# Активация и запуск сервиса
echo "Активация и запуск сервиса..."
sudo systemctl daemon-reload
sudo systemctl enable history-bot.service
sudo systemctl start history-bot.service

echo "Установка завершена!"
echo "Для просмотра логов используйте: journalctl -u history-bot.service -f"
echo "Для перезапуска бота используйте: sudo systemctl restart history-bot.service"
