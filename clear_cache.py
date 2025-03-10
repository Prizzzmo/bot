
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для очистки различных кэшей бота.
Может быть вызван вручную или из админ-панели.
"""

import os
import json
import logging
import time

# Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger("CacheCleaner")

def clear_api_cache():
    """Очищает кэш API"""
    try:
        cache_file = 'api_cache.json'
        if os.path.exists(cache_file):
            # Создаем бэкап перед удалением
            backup_file = f'api_cache_backup_{int(time.time())}.json'
            try:
                import shutil
                shutil.copy2(cache_file, os.path.join('backups', backup_file))
                logger.info(f"Создан бэкап кэша API: {backup_file}")
            except Exception as e:
                logger.warning(f"Не удалось создать бэкап кэша API: {e}")
                
            # Удаляем файл кэша
            os.remove(cache_file)
            logger.info(f"Файл кэша API удален: {cache_file}")
            return True
        else:
            logger.info(f"Файл кэша API не найден: {cache_file}")
            return False
    except Exception as e:
        logger.error(f"Ошибка при очистке кэша API: {e}")
        return False

def clear_memory_caches():
    """Создает файл-индикатор для перезагрузки кэшей в памяти"""
    try:
        with open('clear_memory_cache', 'w') as f:
            f.write(str(int(time.time())))
        logger.info("Создан файл-индикатор для очистки кэшей в памяти")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании файла-индикатора для очистки кэшей: {e}")
        return False

def clear_temp_files():
    """Очищает временные файлы"""
    temp_extensions = ['.tmp', '.bak', '.temp']
    deleted_count = 0
    
    try:
        for file in os.listdir('.'):
            for ext in temp_extensions:
                if file.endswith(ext):
                    try:
                        os.remove(file)
                        deleted_count += 1
                        logger.info(f"Удален временный файл: {file}")
                    except Exception as e:
                        logger.error(f"Ошибка при удалении файла {file}: {e}")
    
        logger.info(f"Удалено {deleted_count} временных файлов")
        return deleted_count
    except Exception as e:
        logger.error(f"Ошибка при очистке временных файлов: {e}")
        return 0

def main():
    """Основная функция скрипта"""
    logger.info("Запуск очистки кэша")
    
    # Проверяем наличие директории backups
    if not os.path.exists('backups'):
        try:
            os.makedirs('backups')
            logger.info("Создана директория для бэкапов: backups")
        except Exception as e:
            logger.error(f"Не удалось создать директорию backups: {e}")
    
    # Очищаем различные кэши
    api_cache_cleared = clear_api_cache()
    memory_cache_cleared = clear_memory_caches()
    temp_files_cleared = clear_temp_files()
    
    # Выводим результаты
    logger.info("Результаты очистки кэша:")
    logger.info(f"- Кэш API: {'очищен' if api_cache_cleared else 'не найден или ошибка'}")
    logger.info(f"- Кэши в памяти: {'создан запрос на очистку' if memory_cache_cleared else 'ошибка'}")
    logger.info(f"- Временные файлы: удалено {temp_files_cleared} файлов")
    
    logger.info("Очистка кэша завершена")

if __name__ == "__main__":
    main()
