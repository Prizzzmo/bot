
import os
import json
import shutil
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_cache_files():
    """Очищает все файлы кэша в проекте"""
    
    # Список файлов кэша для удаления
    cache_files = [
        'api_cache.json',
    ]
    
    # Директории кэша для очистки
    cache_dirs = [
        'history_db_generator/temp',
        'history_db_generator/temp_mistral',
    ]
    
    # Удаляем отдельные файлы кэша
    files_removed = 0
    for file_path in cache_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Удален файл кэша: {file_path}")
                files_removed += 1
            except Exception as e:
                logger.error(f"Ошибка при удалении файла {file_path}: {e}")
    
    # Очищаем директории кэша
    dirs_cleared = 0
    for dir_path in cache_dirs:
        if os.path.exists(dir_path):
            try:
                # Удаляем все файлы в директории, но сохраняем саму директорию
                for file_name in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                logger.info(f"Очищена директория кэша: {dir_path}")
                dirs_cleared += 1
            except Exception as e:
                logger.error(f"Ошибка при очистке директории {dir_path}: {e}")
    
    # Очищаем кэши API через существующий класс
    try:
        from src.api_cache import APICache
        from src.logger import Logger
        
        logger_instance = Logger()
        api_cache = APICache(logger_instance)
        cleared_items = api_cache.clear_cache()
        logger.info(f"Очищено {cleared_items} записей из APICache")
    except Exception as e:
        logger.error(f"Ошибка при очистке APICache: {e}")
    
    logger.info(f"Итого: удалено {files_removed} файлов кэша, очищено {dirs_cleared} директорий кэша")

if __name__ == "__main__":
    clear_cache_files()
