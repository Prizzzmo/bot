# Запуск объединенного веб-приложения
import os
import sys
import logging
from threading import Thread
import time

# Добавляем путь к корневой директории проекта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

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

logger = logging.getLogger('UnifiedWebApp')

def main():
    """Запускает объединенное веб-приложение"""
    logger.info("Запуск объединенного веб-приложения")

    # Импортируем и запускаем объединенный сервер
    from webapp.unified_server import run_unified_server

    # Получаем порт из переменной окружения или используем 8080 по умолчанию
    port = int(os.environ.get('PORT', 8080))

    # Запускаем сервер
    run_unified_server('0.0.0.0', port)

    # Предупреждение о запуске веб-приложения
    print(f"Объединенный веб-сервер запущен на http://0.0.0.0:{port}")
    print(f"Карта истории доступна по адресу: http://0.0.0.0:{port}/")
    print(f"Админ-панель доступна по адресу: http://0.0.0.0:{port}/admin-panel")
    print("Для остановки сервера нажмите Ctrl+C")

if __name__ == "__main__":
    main()