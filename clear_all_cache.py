
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
import os
import sys
import json
import shutil
import argparse
from datetime import datetime

def log_message(message):
    """Вывод сообщения в лог"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def clear_api_cache():
    """Очистка кэша API запросов"""
    cache_files = ["api_cache.json"]
    
    for cache_file in cache_files:
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
                log_message(f"Удален файл кэша API: {cache_file}")
            except Exception as e:
                log_message(f"Ошибка при удалении файла кэша API {cache_file}: {e}")
    
    return True

def clear_events_cache():
    """Очистка кэша исторических событий"""
    cache_files = ["historical_events.json"]
    
    for cache_file in cache_files:
        if os.path.exists(cache_file):
            try:
                # Создаем резервную копию перед удалением
                backup_file = f"{cache_file}.bak"
                shutil.copy(cache_file, backup_file)
                os.remove(cache_file)
                log_message(f"Удален файл кэша событий: {cache_file} (создана резервная копия {backup_file})")
            except Exception as e:
                log_message(f"Ошибка при удалении файла кэша событий {cache_file}: {e}")
    
    return True

def clear_user_cache():
    """Очистка кэша пользовательских данных"""
    cache_files = ["user_states.json"]
    
    for cache_file in cache_files:
        if os.path.exists(cache_file):
            try:
                # Создаем резервную копию перед удалением
                backup_file = f"{cache_file}.bak"
                shutil.copy(cache_file, backup_file)
                
                # Опционально: можно очистить только определенные данные, а не весь файл
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Очищаем временные данные, сохраняя основную информацию
                for user_id in data:
                    if 'temp_data' in data[user_id]:
                        data[user_id]['temp_data'] = {}
                    if 'last_activity' in data[user_id]:
                        data[user_id]['last_activity'] = datetime.now().isoformat()
                
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
                
                log_message(f"Очищены пользовательские данные в файле: {cache_file} (создана резервная копия {backup_file})")
            except Exception as e:
                log_message(f"Ошибка при очистке пользовательских данных в файле {cache_file}: {e}")
    
    return True

def clear_image_cache():
    """Очистка кэша изображений"""
    cache_dirs = ["generated_maps"]
    
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir) and os.path.isdir(cache_dir):
            try:
                # Опционально: можно удалить только старые файлы, а не всю директорию
                for filename in os.listdir(cache_dir):
                    file_path = os.path.join(cache_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                
                log_message(f"Очищена директория с изображениями: {cache_dir}")
            except Exception as e:
                log_message(f"Ошибка при очистке директории с изображениями {cache_dir}: {e}")
    
    return True

def clear_all_cache():
    """Очистка всех типов кэша"""
    results = {}
    results['api'] = clear_api_cache()
    results['events'] = clear_events_cache()
    results['user'] = clear_user_cache()
    results['images'] = clear_image_cache()
    
    log_message("Все кэши успешно очищены!")
    return results

def selective_cache_clear(types=None):
    """Выборочная очистка кэша по типам"""
    if types is None or len(types) == 0:
        log_message("Не указаны типы кэша для очистки")
        return False
    
    results = {}
    
    if 'api' in types:
        results['api'] = clear_api_cache()
    
    if 'events' in types:
        results['events'] = clear_events_cache()
    
    if 'user' in types:
        results['user'] = clear_user_cache()
    
    if 'images' in types:
        results['images'] = clear_image_cache()
    
    log_message(f"Выборочная очистка кэша завершена для типов: {', '.join(types)}")
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Скрипт для очистки кэша')
    parser.add_argument('--all', action='store_true', help='Очистить все типы кэша')
    parser.add_argument('--api', action='store_true', help='Очистить кэш API')
    parser.add_argument('--events', action='store_true', help='Очистить кэш событий')
    parser.add_argument('--user', action='store_true', help='Очистить пользовательский кэш')
    parser.add_argument('--images', action='store_true', help='Очистить кэш изображений')
    
    args = parser.parse_args()
    
    if args.all:
        clear_all_cache()
    else:
        types = []
        if args.api:
            types.append('api')
        if args.events:
            types.append('events')
        if args.user:
            types.append('user')
        if args.images:
            types.append('images')
        
        if types:
            selective_cache_clear(types)
        else:
            log_message("Не указаны типы кэша для очистки. Используйте --all для очистки всех кэшей или укажите конкретные типы.")
            parser.print_help()
