
#!/usr/bin/env python3
"""
Скрипт для очистки всех кэшей проекта.
"""

import os
import json
import shutil
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def clear_api_cache():
    """Очищает API кэш"""
    cache_files = [
        'api_cache.json',
        'local_cache.json',
        'texts_cache.json'
    ]
    
    count = 0
    for file_path in cache_files:
        if os.path.exists(file_path):
            try:
                # Создаем пустой кэш вместо полного удаления файла
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('{}')
                logger.info(f"Очищен файл кэша: {file_path}")
                count += 1
            except Exception as e:
                logger.error(f"Ошибка при очистке файла {file_path}: {e}")
    
    return count

def clear_temp_dirs():
    """Очищает директории временных файлов"""
    temp_dirs = [
        'history_db_generator/temp',
        'history_db_generator/temp_mistral',
        '.pytest_cache',
        '.mypy_cache'
    ]
    
    count = 0
    for dir_path in temp_dirs:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            try:
                for file_name in os.listdir(dir_path):
                    file_path = os.path.join(dir_path, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                logger.info(f"Очищена директория: {dir_path}")
                count += 1
            except Exception as e:
                logger.error(f"Ошибка при очистке директории {dir_path}: {e}")
    
    return count

def clear_pycache():
    """Очищает директории __pycache__"""
    count = 0
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                pycache_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(pycache_path)
                    logger.info(f"Удалена директория: {pycache_path}")
                    count += 1
                except Exception as e:
                    logger.error(f"Ошибка при удалении {pycache_path}: {e}")
    
    return count

def main():
    logger.info("Начинаем очистку всех кэшей проекта...")
    
    api_cache_count = clear_api_cache()
    temp_dirs_count = clear_temp_dirs()
    pycache_count = clear_pycache()
    
    logger.info(f"Очищено {api_cache_count} файлов кэша API")
    logger.info(f"Очищено {temp_dirs_count} директорий временных файлов")
    logger.info(f"Удалено {pycache_count} директорий __pycache__")
    logger.info("Очистка кэша завершена!")

if __name__ == "__main__":
    main()
