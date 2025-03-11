
"""
Скрипт для очистки старых резервных копий и логов
"""

import os
import shutil
import glob
import time
from datetime import datetime, timedelta
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Cleanup")

def cleanup_old_files():
    """Очищает старые файлы резервных копий и логов"""
    logger.info("Запуск очистки старых файлов")
    
    # Директории для проверки
    backup_dirs = ['backups', 'history_db_generator/backups']
    log_dirs = ['logs']
    
    # Очистка старых резервных копий (старше 7 дней)
    backup_cutoff = time.time() - (7 * 24 * 60 * 60)  # 7 дней
    
    for backup_dir in backup_dirs:
        if os.path.exists(backup_dir) and os.path.isdir(backup_dir):
            for item in os.listdir(backup_dir):
                item_path = os.path.join(backup_dir, item)
                
                # Если это файл и он старше 7 дней
                if os.path.isfile(item_path) and os.path.getmtime(item_path) < backup_cutoff:
                    try:
                        os.remove(item_path)
                        logger.info(f"Удален старый файл резервной копии: {item_path}")
                    except Exception as e:
                        logger.error(f"Ошибка при удалении файла {item_path}: {e}")
    
    # Очистка старых логов (старше 3 дней)
    log_cutoff = time.time() - (3 * 24 * 60 * 60)  # 3 дня
    
    for log_dir in log_dirs:
        if os.path.exists(log_dir) and os.path.isdir(log_dir):
            for item in os.listdir(log_dir):
                # Проверяем, что это лог-файл
                if item.endswith('.log') and not item.startswith(('cleanup', 'unified_server')):
                    item_path = os.path.join(log_dir, item)
                    
                    # Если он старше 3 дней
                    if os.path.getmtime(item_path) < log_cutoff:
                        try:
                            os.remove(item_path)
                            logger.info(f"Удален старый лог-файл: {item_path}")
                        except Exception as e:
                            logger.error(f"Ошибка при удалении лог-файла {item_path}: {e}")
    
    # Записываем дату последней очистки
    with open('last_cleanup.txt', 'w') as f:
        f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    logger.info("Очистка старых файлов завершена")

if __name__ == "__main__":
    # Проверяем существование директории логов
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # Запускаем очистку
    cleanup_old_files()
