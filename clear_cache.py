
#!/usr/bin/env python3
import os
import json
import shutil
import datetime

def clear_api_cache():
    """Очищает кэш API"""
    try:
        # Проверяем наличие файла кэша API
        api_cache_file = 'api_cache.json'
        
        if os.path.exists(api_cache_file):
            # Создаем бэкап перед удалением
            backup_dir = 'backups'
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                
            # Текущее время для имени файла
            timestamp = int(datetime.datetime.now().timestamp())
            backup_path = os.path.join(backup_dir, f"api_cache_backup_{timestamp}.json")
            
            # Копируем файл кэша в бэкап
            shutil.copy2(api_cache_file, backup_path)
            print(f"Создана резервная копия файла кэша API: {backup_path}")
            
            # Удаляем файл кэша
            os.remove(api_cache_file)
            print(f"Файл кэша API {api_cache_file} успешно удален")
            
            # Создаем пустой файл кэша
            with open(api_cache_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            print(f"Создан новый пустой файл кэша API")
            
            return True
        else:
            # Если файл не существует, создаем его
            with open(api_cache_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
            print(f"Файл кэша API не существовал, создан новый пустой файл")
            return False
    except Exception as e:
        print(f"Ошибка при очистке кэша API: {e}")
        return False

def clear_temp_files():
    """Очищает временные файлы"""
    try:
        temp_dirs = ['__pycache__', 'src/__pycache__', 'tests/__pycache__']
        
        for dir_path in temp_dirs:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                shutil.rmtree(dir_path)
                print(f"Удалена директория с временными файлами: {dir_path}")
        
        # Очистка .pyc файлов в корневой директории
        for file_name in os.listdir('.'):
            if file_name.endswith('.pyc'):
                os.remove(file_name)
                print(f"Удален временный файл: {file_name}")
        
        return True
    except Exception as e:
        print(f"Ошибка при очистке временных файлов: {e}")
        return False

def clear_log_backups(days_threshold=7):
    """Очищает старые файлы логов"""
    try:
        log_dir = "logs"
        if not os.path.exists(log_dir):
            print(f"Директория логов {log_dir} не существует")
            return False
        
        # Получаем текущую дату
        current_date = datetime.datetime.now()
        
        # Счетчик удаленных файлов
        deleted_count = 0
        
        # Проверяем каждый файл в директории логов
        for file_name in os.listdir(log_dir):
            if file_name.startswith("bot_log_") and file_name.endswith(".log"):
                try:
                    # Извлекаем дату из имени файла (формат: bot_log_YYYYMMDD.log)
                    date_str = file_name[8:16]  # Извлекаем YYYYMMDD
                    file_date = datetime.datetime.strptime(date_str, "%Y%m%d")
                    
                    # Если файл старше указанного порога, удаляем его
                    if (current_date - file_date).days > days_threshold:
                        file_path = os.path.join(log_dir, file_name)
                        os.remove(file_path)
                        deleted_count += 1
                        print(f"Удален старый лог-файл: {file_path}")
                except Exception as e:
                    print(f"Ошибка при обработке файла лога {file_name}: {e}")
        
        print(f"Очистка логов завершена. Удалено файлов: {deleted_count}")
        return True
    except Exception as e:
        print(f"Ошибка при очистке старых логов: {e}")
        return False

if __name__ == "__main__":
    print("=== Очистка кэша и временных файлов ===")
    
    # Очистка кэша API
    api_cache_cleared = clear_api_cache()
    print(f"Кэш API {'очищен' if api_cache_cleared else 'не найден или не очищен'}")
    
    # Очистка временных файлов
    temp_files_cleared = clear_temp_files()
    print(f"Временные файлы {'очищены' if temp_files_cleared else 'не найдены или не очищены'}")
    
    # Очистка старых лог-файлов (старше 7 дней)
    logs_cleared = clear_log_backups(7)
    print(f"Логи старше 7 дней {'очищены' if logs_cleared else 'не найдены или не очищены'}")
    
    print("=== Очистка завершена ===")
