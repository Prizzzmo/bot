# Запуск веб-приложения
import os
import sys
import logging
from threading import Thread
import time

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from webapp.admin_server import run_admin_server
from webapp.server import run_server

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

    # Создаем и запускаем поток для админ-панели
    admin_thread = Thread(target=run_admin_server, args=('0.0.0.0', admin_port), daemon=True)
    admin_thread.start()
    logger.info(f"Админ-панель запущена на порту {admin_port}")

    logger.info("Все сервисы запущены успешно")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Завершение работы приложения")
        sys.exit(0)

if __name__ == "__main__":
    main()