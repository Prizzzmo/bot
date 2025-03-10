#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для создания резервных копий данных бота
"""

import os
import json
import shutil
import time
import datetime
import zipfile
import logging
import sys

def setup_logger():
    """Настраивает логгер"""
    logger = logging.getLogger('backup')
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

    return logger

def create_backup(logger):
    """Создает резервную копию данных бота"""
    try:
        # Текущее время для имени файла
        timestamp = int(time.time())
        backup_dir = "backups"

        # Создаем директорию для резервных копий, если она не существует
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            logger.info(f"Создана директория для резервных копий: {backup_dir}")

        # Список файлов для резервного копирования
        files_to_backup = [
            'user_states.json',
            'historical_events.json',
            'admins.json',
            'bot_settings.json',
            'api_cache.json',
            'texts_cache.json',
            'data_version.json'
        ]

        # Копируем каждый файл в директорию резервных копий
        backup_files = []
        for file_name in files_to_backup:
            if os.path.exists(file_name):
                backup_file_name = f"{file_name.split('.')[0]}_backup_{timestamp}.json"
                backup_path = os.path.join(backup_dir, backup_file_name)
                try:
                    shutil.copy2(file_name, backup_path)
                    backup_files.append((file_name, backup_path))
                    logger.info(f"Создана резервная копия файла {file_name}")
                except Exception as e:
                    logger.error(f"Ошибка при копировании файла {file_name}: {e}")

        # Также создаем общую резервную копию
        data_backup_path = os.path.join(backup_dir, f"data_backup_v{len(backup_files)}_{timestamp}")
        try:
            with zipfile.ZipFile(data_backup_path + '.zip', 'w') as zipf:
                for file_name in files_to_backup:
                    if os.path.exists(file_name):
                        zipf.write(file_name)
                # Добавляем лог в архив
                if os.path.exists("logs/bot.log"):
                    zipf.write("logs/bot.log")
                elif os.path.exists("bot.log"):
                    zipf.write("bot.log")
            logger.info(f"Создана общая резервная копия данных: {data_backup_path}.zip")
            backup_files.append(("Все данные", data_backup_path + '.zip'))
        except Exception as e:
            logger.error(f"Ошибка при создании общей резервной копии: {e}")

        # Формируем сообщение о результате
        result_text = "Резервное копирование завершено\n\n"

        if backup_files:
            result_text += "Созданы следующие резервные копии:\n\n"
            for original, backup in backup_files:
                result_text += f"• {original} → {os.path.basename(backup)}\n"
        else:
            result_text += "Не удалось создать ни одной резервной копии."

        # Очистка старых бэкапов (оставляем только 5 последних)
        clean_old_backups(backup_dir, logger)

        logger.info(result_text)
        return backup_files
    except Exception as e:
        logger.error(f"Ошибка при создании резервной копии: {e}")
        return []

def clean_old_backups(backup_dir, logger):
    """Удаляет старые резервные копии, оставляя только 5 последних"""
    try:
        # Получаем список файлов в директории для резервных копий
        if not os.path.exists(backup_dir):
            return

        # Получаем все zip-файлы в директории
        backup_files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.endswith('.zip')]

        # Сортируем по времени создания (самые старые в начале)
        backup_files.sort(key=lambda x: os.path.getctime(x))

        # Удаляем старые файлы, оставляя только 5 последних
        files_to_delete = backup_files[:-5] if len(backup_files) > 5 else []

        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                logger.info(f"Удален старый файл резервной копии: {file_path}")
            except Exception as e:
                logger.error(f"Ошибка при удалении старой резервной копии {file_path}: {e}")

        logger.info(f"Очистка старых резервных копий завершена. Удалено файлов: {len(files_to_delete)}")
    except Exception as e:
        logger.error(f"Ошибка при очистке старых резервных копий: {e}")

def main():
    """Основная функция"""
    logger = setup_logger()
    logger.info("Начало создания резервной копии данных")

    backup_files = create_backup(logger)

    if backup_files:
        logger.info(f"Резервное копирование успешно завершено. Создано файлов: {len(backup_files)}")
    else:
        logger.warning("Резервное копирование завершено без создания файлов")

    logger.info("Процесс резервного копирования завершен")

if __name__ == "__main__":
    main()