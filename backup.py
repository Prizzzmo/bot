
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для создания резервных копий данных бота.
Может быть запущен вручную или по расписанию.
"""

import os
import time
import datetime
import shutil
import zipfile
import logging
import json

# Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger("Backup")

class BackupManager:
    """Класс для управления резервными копиями"""
    
    def __init__(self):
        self.backup_dir = "backups"
        self.timestamp = int(time.time())
        self.date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Создаем директорию для резервных копий, если она не существует
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            logger.info(f"Создана директория для резервных копий: {self.backup_dir}")
    
    def backup_file(self, file_path):
        """Создает резервную копию отдельного файла"""
        if not os.path.exists(file_path):
            logger.warning(f"Файл не найден: {file_path}")
            return None
            
        try:
            # Получаем имя файла из пути
            file_name = os.path.basename(file_path)
            
            # Формируем имя для резервной копии
            backup_name = f"{os.path.splitext(file_name)[0]}_backup_{self.timestamp}{os.path.splitext(file_name)[1]}"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Копируем файл
            shutil.copy2(file_path, backup_path)
            
            logger.info(f"Создана резервная копия файла {file_path} -> {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Ошибка при создании резервной копии файла {file_path}: {e}")
            return None
    
    def backup_files(self, file_paths, create_zip=True):
        """Создает резервные копии нескольких файлов и, опционально, архивирует их"""
        successful_backups = []
        
        # Создаем резервные копии каждого файла
        for file_path in file_paths:
            backup_path = self.backup_file(file_path)
            if backup_path:
                successful_backups.append((file_path, backup_path))
        
        # Если нужно, архивируем все файлы вместе
        if create_zip and successful_backups:
            try:
                zip_path = os.path.join(self.backup_dir, f"full_backup_{self.date_str}.zip")
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Добавляем в архив оригинальные файлы, а не резервные копии
                    for original_file, _ in successful_backups:
                        zipf.write(original_file, arcname=os.path.basename(original_file))
                
                logger.info(f"Создан архив с резервными копиями: {zip_path}")
                successful_backups.append(("all_files", zip_path))
            except Exception as e:
                logger.error(f"Ошибка при создании архива: {e}")
        
        return successful_backups
    
    def clean_old_backups(self, max_age_days=30, max_count=50):
        """Удаляет старые резервные копии"""
        try:
            if not os.path.exists(self.backup_dir):
                return 0
                
            # Получаем список всех файлов в директории резервных копий
            backup_files = []
            for file_name in os.listdir(self.backup_dir):
                file_path = os.path.join(self.backup_dir, file_name)
                if os.path.isfile(file_path):
                    backup_files.append({
                        'path': file_path,
                        'mtime': os.path.getmtime(file_path),
                        'size': os.path.getsize(file_path)
                    })
            
            # Сортируем по времени изменения (новые в начале)
            backup_files.sort(key=lambda x: x['mtime'], reverse=True)
            
            # Удаляем старые файлы по возрасту и количеству
            deleted_count = 0
            current_time = time.time()
            
            for i, file_info in enumerate(backup_files):
                # Пропускаем файлы, которые нужно сохранить по количеству
                if i < max_count:
                    # Но все равно проверяем по возрасту
                    age_days = (current_time - file_info['mtime']) / (60 * 60 * 24)
                    if age_days <= max_age_days:
                        continue
                
                try:
                    os.remove(file_info['path'])
                    deleted_count += 1
                    logger.info(f"Удалена старая резервная копия: {os.path.basename(file_info['path'])}")
                except Exception as e:
                    logger.error(f"Ошибка при удалении файла {file_info['path']}: {e}")
            
            return deleted_count
        except Exception as e:
            logger.error(f"Ошибка при очистке старых резервных копий: {e}")
            return 0

def main():
    """Основная функция скрипта"""
    logger.info("Запуск создания резервных копий")
    
    # Файлы для резервного копирования
    files_to_backup = [
        'user_states.json',
        'historical_events.json',
        'admins.json',
        'bot_settings.json',
        'api_cache.json'
    ]
    
    # Добавляем лог-файлы
    log_dir = "logs"
    if os.path.exists(log_dir) and os.path.isdir(log_dir):
        for file_name in os.listdir(log_dir):
            if file_name.startswith("bot_log_") or file_name == "bot.log":
                files_to_backup.append(os.path.join(log_dir, file_name))
    elif os.path.exists("bot.log"):
        files_to_backup.append("bot.log")
    
    # Создаем менеджер резервных копий
    backup_manager = BackupManager()
    
    # Создаем резервные копии
    successful_backups = backup_manager.backup_files(files_to_backup)
    
    # Очищаем старые резервные копии
    deleted_count = backup_manager.clean_old_backups()
    
    # Выводим результаты
    logger.info("Результаты создания резервных копий:")
    for original, backup in successful_backups:
        logger.info(f"- {original} -> {os.path.basename(backup)}")
    
    logger.info(f"Создано {len(successful_backups)} резервных копий")
    logger.info(f"Удалено {deleted_count} старых резервных копий")
    
    # Сохраняем информацию о резервных копиях
    backup_info = {
        "timestamp": time.time(),
        "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "backups": [{
            "original": original,
            "backup": os.path.basename(backup),
            "size": os.path.getsize(backup) if os.path.exists(backup) else 0
        } for original, backup in successful_backups],
        "deleted_count": deleted_count
    }
    
    # Сохраняем информацию в файл
    try:
        info_file = os.path.join(backup_manager.backup_dir, f"backup_info_{backup_manager.date_str}.json")
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(backup_info, f, indent=2)
        logger.info(f"Информация о резервных копиях сохранена в файл {info_file}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении информации о резервных копиях: {e}")
    
    logger.info("Создание резервных копий завершено")

if __name__ == "__main__":
    main()
