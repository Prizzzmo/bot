#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для очистки кэша и временных данных бота
"""

import os
import json
import logging
import sys

def setup_logger():
    """Настраивает логгер"""
    logger = logging.getLogger('cache_cleaner')
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

    return logger

def clear_cache(logger):
    """Очищает кэш API и другие временные данные"""
    try:
        # Список файлов для проверки и очистки
        cache_files = [
            'api_cache.json',
            'texts_cache.json',
            'temp_cache.json'
        ]

        cleared_files = []

        # Удаляем файлы кэша, если они существуют
        for file_name in cache_files:
            if os.path.exists(file_name):
                try:
                    os.remove(file_name)
                    cleared_files.append(file_name)
                    logger.info(f"Файл {file_name} успешно удален")
                except Exception as e:
                    logger.error(f"Ошибка при удалении файла {file_name}: {e}")

        # Создаем пустой файл api_cache.json
        with open('api_cache.json', 'w', encoding='utf-8') as f:
            json.dump({}, f)
            logger.info("Создан новый пустой файл api_cache.json")

        return cleared_files
    except Exception as e:
        logger.error(f"Ошибка при очистке кэша: {e}")
        return []

def main():
    """Основная функция"""
    logger = setup_logger()
    logger.info("Начало очистки кэша")

    cleared_files = clear_cache(logger)

    if cleared_files:
        logger.info(f"Очистка кэша завершена. Удалено файлов: {len(cleared_files)}")
    else:
        logger.info("Очистка кэша завершена. Файлы кэша не найдены или не удалены")

    logger.info("Очистка кэша завершена")

if __name__ == "__main__":
    main()