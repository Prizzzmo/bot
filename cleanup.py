
#!/usr/bin/env python3
"""
Скрипт для очистки проекта от временных файлов и кэшей.
Используется для поддержания порядка в репозитории.
"""

import os
import shutil
import glob
import argparse

def clean_pycache():
    """Удаляет все __pycache__ директории и .pyc файлы."""
    count = 0
    
    # Удаление __pycache__ директорий
    for pycache_dir in glob.glob('**/__pycache__', recursive=True):
        try:
            shutil.rmtree(pycache_dir)
            count += 1
            print(f"Удалена директория: {pycache_dir}")
        except Exception as e:
            print(f"Ошибка при удалении {pycache_dir}: {e}")
    
    # Удаление .pyc файлов
    for pyc_file in glob.glob('**/*.pyc', recursive=True):
        try:
            os.remove(pyc_file)
            count += 1
            print(f"Удален файл: {pyc_file}")
        except Exception as e:
            print(f"Ошибка при удалении {pyc_file}: {e}")
    
    return count

def clean_temp_files():
    """Удаляет временные файлы."""
    temp_patterns = [
        '**/*.tmp',
        '**/*.bak',
        '**/*.swp',
        '**/.DS_Store',
        '**/Thumbs.db'
    ]
    
    count = 0
    for pattern in temp_patterns:
        for file_path in glob.glob(pattern, recursive=True):
            try:
                os.remove(file_path)
                count += 1
                print(f"Удален временный файл: {file_path}")
            except Exception as e:
                print(f"Ошибка при удалении {file_path}: {e}")
    
    return count

def clean_logs(keep_latest=True):
    """
    Удаляет старые файлы логов.
    
    Args:
        keep_latest (bool): Сохранять ли последний файл лога.
    """
    log_files = glob.glob('logs/*.log')
    
    if keep_latest and log_files:
        # Сортируем по времени изменения (новые в конце)
        log_files.sort(key=os.path.getmtime)
        # Удаляем последний (самый новый) из списка на удаление
        latest_log = log_files.pop()
        print(f"Сохранен последний лог-файл: {latest_log}")
    
    count = 0
    for log_file in log_files:
        try:
            os.remove(log_file)
            count += 1
            print(f"Удален лог-файл: {log_file}")
        except Exception as e:
            print(f"Ошибка при удалении {log_file}: {e}")
    
    return count

def clean_cache():
    """Очищает директории кэша."""
    cache_dirs = [
        'history_db_generator/temp',
        '.pytest_cache',
        '.mypy_cache'
    ]
    
    count = 0
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir) and os.path.isdir(cache_dir):
            try:
                # Удаляем содержимое директории, но сохраняем саму директорию
                for item in os.listdir(cache_dir):
                    item_path = os.path.join(cache_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                count += 1
                print(f"Очищена директория кэша: {cache_dir}")
            except Exception as e:
                print(f"Ошибка при очистке {cache_dir}: {e}")
    
    return count

def main():
    parser = argparse.ArgumentParser(description='Очистка проекта от временных файлов и кэшей.')
    parser.add_argument('--all', action='store_true', help='Выполнить полную очистку')
    parser.add_argument('--pycache', action='store_true', help='Удалить __pycache__ директории и .pyc файлы')
    parser.add_argument('--temp', action='store_true', help='Удалить временные файлы')
    parser.add_argument('--logs', action='store_true', help='Удалить файлы логов')
    parser.add_argument('--cache', action='store_true', help='Очистить директории кэша')
    parser.add_argument('--keep-latest-log', action='store_true', default=True, 
                       help='Сохранять последний файл лога (по умолчанию: True)')
    
    args = parser.parse_args()
    
    # Если не указаны конкретные параметры, выполняем базовую очистку
    if not any([args.all, args.pycache, args.temp, args.logs, args.cache]):
        args.pycache = True
        args.temp = True
    
    # Если указан --all, включаем все опции
    if args.all:
        args.pycache = True
        args.temp = True
        args.logs = True
        args.cache = True
    
    total_count = 0
    
    if args.pycache:
        count = clean_pycache()
        total_count += count
        print(f"Удалено {count} __pycache__ директорий и .pyc файлов")
    
    if args.temp:
        count = clean_temp_files()
        total_count += count
        print(f"Удалено {count} временных файлов")
    
    if args.logs:
        count = clean_logs(keep_latest=args.keep_latest_log)
        total_count += count
        print(f"Удалено {count} файлов логов")
    
    if args.cache:
        count = clean_cache()
        total_count += count
        print(f"Очищено {count} директорий кэша")
    
    print(f"\nВсего удалено/очищено: {total_count} элементов")
    print("Очистка завершена успешно.")

if __name__ == "__main__":
    main()
