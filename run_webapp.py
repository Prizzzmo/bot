
#!/usr/bin/env python3
"""
Скрипт для запуска веб-сервера администратора.
"""
import os
import logging
import time
from webapp.admin_server import AdminServer

# Настройка логирования
logging.basicConfig(
    filename='logs/admin_server.log',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("AdminWebApp")

def ensure_directories_exist():
    """Создает необходимые директории, если они отсутствуют"""
    dirs = ['logs', 'backups', 'static/docs']
    for directory in dirs:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Создана директория: {directory}")

def run_admin_server():
    """Запускает сервер администратора"""
    try:
        # Создаем необходимые директории
        ensure_directories_exist()
        
        # Запускаем сервер админки
        logger.info("Запуск веб-сервера администратора...")
        port = int(os.environ.get('PORT', 8080))
        admin_server = AdminServer()
        admin_server.start(host='0.0.0.0', port=port)
        
        # Выводим информацию о запуске
        logger.info(f"Веб-сервер администратора запущен на порту {port}")
        print(f"Веб-сервер администратора запущен на порту {port}")
        print(f"Откройте в браузере: http://localhost:{port}/admin-panel")
        
        # Ожидаем остановки сервера
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Получен сигнал завершения")
            admin_server.stop()
            logger.info("Веб-сервер администратора остановлен")
    
    except Exception as e:
        logger.error(f"Ошибка при запуске веб-сервера администратора: {e}")
        print(f"Ошибка при запуске веб-сервера администратора: {e}")

if __name__ == "__main__":
    run_admin_server()
