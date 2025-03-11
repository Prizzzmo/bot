# Запуск веб-приложения
import os
import sys
import logging
from threading import Thread
import time

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from webapp.server import run_server
import logging
import json
from webapp.admin_server import AdminServer

# Подключаем основные компоненты проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.logger import Logger
from src.analytics import AnalyticsService
from src.admin_panel import AdminPanel
from src.config import Config

def load_config():
    """Загрузка конфигурации проекта"""
    config = Config()
    return config

# Настраиваем логирование
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/webapp.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('WebApp')


def main():
    """Запускает веб-приложение и админ-панель"""
    logger.info("Запуск веб-приложения и админ-панели")

    # Порт для веб-приложения
    webapp_port = int(os.environ.get('WEBAPP_PORT', 5000))
    # Порт для админ-панели
    admin_port = int(os.environ.get('ADMIN_PORT', 8000))

    # Создаем и запускаем поток для веб-сервера
    webapp_thread = Thread(target=run_server, args=('0.0.0.0', webapp_port), daemon=True)
    webapp_thread.start()
    logger.info(f"Веб-приложение запущено на порту {webapp_port}")

    # Создаем экземпляр логгера
    #logger = Logger() #Already defined above
    logger.info("Запуск веб-сервера администратора")

    # Загружаем конфигурацию
    config = load_config()

    # Создаем сервис аналитики
    analytics_service = AnalyticsService(logger)

    # Создаем админ-панель из основного кода
    admin_panel = AdminPanel(logger, config)

    # Создаем и запускаем сервер админки
    admin_server = AdminServer(admin_panel=admin_panel, analytics_service=analytics_service)
    admin_server.start(host='0.0.0.0', port=admin_port) #using admin_port variable

    # Запускаем Flask Admin Server
    #admin_server.start(host='0.0.0.0', port=8000)

    # Предупреждение о запуске веб-панели администратора
    print(f"Админ-сервер запущен на http://0.0.0.0:{admin_port}")
    print("Для доступа к админ-панели перейдите по адресу: http://0.0.0.0:{admin_port}/admin-panel".format(admin_port=admin_port))
    print("Для остановки сервера нажмите Ctrl+C")

    # Держим основной поток активным
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Сервер остановлен.")
        admin_server.stop() #added to stop admin server gracefully
        sys.exit(0)


    logger.info(f"Админ-панель запущена на порту {admin_port}")

    logger.info("Все сервисы запущены успешно")

if __name__ == "__main__":
    main()