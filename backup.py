
#!/usr/bin/env python3
import os
import json
import shutil
import zipfile
import datetime
import time

def create_backup():
    """Создает резервную копию данных бота"""
    try:
        # Создаем директорию для резервных копий, если она не существует
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Текущее время для имени файла
        timestamp = int(time.time())
        
        # Список файлов для резервного копирования
        files_to_backup = [
            'user_states.json',
            'historical_events.json',
            'admins.json',
            'bot_settings.json',
            'api_cache.json'
        ]
        
        # Список успешно скопированных файлов
        backup_files = []
        
        # Копируем каждый файл в директорию резервных копий
        for file_name in files_to_backup:
            if os.path.exists(file_name):
                backup_file_name = f"{file_name.split('.')[0]}_backup_{timestamp}.json"
                backup_path = os.path.join(backup_dir, backup_file_name)
                
                try:
                    shutil.copy2(file_name, backup_path)
                    backup_files.append((file_name, backup_path))
                    print(f"Создана резервная копия файла {file_name}")
                except Exception as e:
                    print(f"Ошибка при копировании файла {file_name}: {e}")
        
        # Создаем общую резервную копию в ZIP-архиве
        if backup_files:
            data_backup_path = os.path.join(backup_dir, f"data_backup_v{len(backup_files)}_{timestamp}")
            
            try:
                with zipfile.ZipFile(data_backup_path + '.zip', 'w') as zipf:
                    # Добавляем каждый файл в архив
                    for file_name in files_to_backup:
                        if os.path.exists(file_name):
                            zipf.write(file_name)
                    
                    # Добавляем лог-файл в архив
                    log_files = get_log_files()
                    if log_files:
                        zipf.write(log_files[0])
                
                backup_files.append(("Все данные", data_backup_path + '.zip'))
                print(f"Создана общая резервная копия данных: {data_backup_path}.zip")
            except Exception as e:
                print(f"Ошибка при создании общей резервной копии: {e}")
        
        return backup_files
    except Exception as e:
        print(f"Ошибка при создании резервной копии: {e}")
        return []

def get_log_files():
    """Получает список всех файлов логов"""
    log_files = []
    
    # Проверяем директорию логов
    log_dir = "logs"
    if os.path.exists(log_dir) and os.path.isdir(log_dir):
        for file_name in os.listdir(log_dir):
            if file_name.startswith("bot_log_") or file_name == "bot.log":
                log_files.append(os.path.join(log_dir, file_name))
    
    # Проверяем корневую директорию
    for file_name in os.listdir("."):
        if file_name.startswith("bot_log_") or file_name == "bot.log":
            log_files.append(file_name)
    
    # Сортируем по времени изменения (новые сначала)
    log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    return log_files

def list_backups():
    """Выводит список имеющихся резервных копий"""
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        print("Директория резервных копий не существует")
        return
    
    # Получаем список файлов в директории резервных копий
    backup_files = os.listdir(backup_dir)
    
    # Группируем файлы по типу
    grouped_backups = {}
    for file_name in backup_files:
        if "_backup_" in file_name:
            parts = file_name.split("_backup_")
            backup_type = parts[0]
            
            if backup_type not in grouped_backups:
                grouped_backups[backup_type] = []
            
            grouped_backups[backup_type].append(file_name)
    
    # Выводим информацию о резервных копиях
    print("\n=== Список резервных копий ===")
    
    if not grouped_backups:
        print("Резервные копии не найдены")
    else:
        for backup_type, files in grouped_backups.items():
            print(f"\n{backup_type.capitalize()}:")
            
            # Сортируем файлы по времени создания (новые сначала)
            files.sort(reverse=True)
            
            for i, file_name in enumerate(files[:5], 1):  # Показываем только 5 последних копий
                file_path = os.path.join(backup_dir, file_name)
                file_size = os.path.getsize(file_path) / 1024  # Размер в КБ
                mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                
                print(f"  {i}. {file_name}")
                print(f"     Размер: {file_size:.2f} КБ")
                print(f"     Создан: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if len(files) > 5:
                print(f"  ... и еще {len(files) - 5} резервных копий")

def restore_backup(backup_file):
    """Восстанавливает данные из резервной копии"""
    backup_dir = "backups"
    backup_path = os.path.join(backup_dir, backup_file)
    
    if not os.path.exists(backup_path):
        print(f"Файл резервной копии {backup_file} не найден")
        return False
    
    try:
        # Определяем тип резервной копии
        if backup_file.endswith('.zip'):
            # Распаковываем ZIP-архив
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Создаем временную директорию для распаковки
                temp_dir = os.path.join(backup_dir, "temp_restore")
                os.makedirs(temp_dir, exist_ok=True)
                
                # Распаковываем файлы
                zipf.extractall(temp_dir)
                
                # Копируем распакованные файлы в корневую директорию
                for file_name in os.listdir(temp_dir):
                    if file_name.endswith('.json'):
                        source_path = os.path.join(temp_dir, file_name)
                        dest_path = os.path.join(".", file_name)
                        
                        # Создаем бэкап текущего файла перед заменой
                        if os.path.exists(dest_path):
                            current_backup = dest_path + ".bak"
                            shutil.copy2(dest_path, current_backup)
                            print(f"Создана резервная копия текущего файла {file_name}: {current_backup}")
                        
                        # Копируем файл из архива
                        shutil.copy2(source_path, dest_path)
                        print(f"Восстановлен файл {file_name}")
                
                # Удаляем временную директорию
                shutil.rmtree(temp_dir)
        else:
            # Восстанавливаем отдельный файл
            if "_backup_" in backup_file:
                original_file = backup_file.split("_backup_")[0] + ".json"
                dest_path = os.path.join(".", original_file)
                
                # Создаем бэкап текущего файла перед заменой
                if os.path.exists(dest_path):
                    current_backup = dest_path + ".bak"
                    shutil.copy2(dest_path, current_backup)
                    print(f"Создана резервная копия текущего файла {original_file}: {current_backup}")
                
                # Копируем файл из бэкапа
                shutil.copy2(backup_path, dest_path)
                print(f"Восстановлен файл {original_file}")
            else:
                print(f"Неизвестный формат файла резервной копии: {backup_file}")
                return False
        
        print("Восстановление из резервной копии успешно завершено")
        return True
    except Exception as e:
        print(f"Ошибка при восстановлении из резервной копии: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    # Если передан аргумент --list, выводим список резервных копий
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_backups()
    # Если передан аргумент --restore, восстанавливаем указанную резервную копию
    elif len(sys.argv) > 2 and sys.argv[1] == "--restore":
        backup_file = sys.argv[2]
        restore_backup(backup_file)
    # В остальных случаях создаем новую резервную копию
    else:
        print("=== Создание резервной копии данных ===")
        backup_files = create_backup()
        
        if backup_files:
            print("\nСозданы следующие резервные копии:")
            for original, backup in backup_files:
                print(f"• {original} → {os.path.basename(backup)}")
        else:
            print("\nНе удалось создать ни одной резервной копии.")
        
        print("\n=== Резервное копирование завершено ===")
