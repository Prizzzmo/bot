
#!/usr/bin/env python3
"""
Скрипт для запуска веб-сервера и админ-панели
"""

import os
import sys
import threading
import time
import logging
from webapp.server import run_server
from webapp.admin_server import run_admin_server

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/webapp.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('WebApp')

# Создаем директорию для логов, если её нет
os.makedirs('logs', exist_ok=True)

def main():
    """Основная функция запуска веб-серверов"""
    try:
        logger.info("Запуск веб-серверов...")
        
        # Запускаем веб-сервер в отдельном потоке
        webapp_thread = threading.Thread(target=run_server, kwargs={'host': '0.0.0.0', 'port': 8080})
        webapp_thread.daemon = True
        webapp_thread.start()
        logger.info("Веб-сервер запущен на порту 8080")
        
        # Запускаем админ-сервер в отдельном потоке
        admin_thread = threading.Thread(target=run_admin_server, kwargs={'host': '0.0.0.0', 'port': 8000})
        admin_thread.daemon = True
        admin_thread.start()
        logger.info("Сервер админ-панели запущен на порту 8000")
        
        # Основной поток остается активным, чтобы серверы продолжали работать
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, остановка серверов...")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Ошибка при запуске серверов: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
