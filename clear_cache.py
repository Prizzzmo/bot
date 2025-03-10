
"""
Скрипт для очистки всех видов кэша в системе
"""
import os
import json
import shutil

def clear_api_cache():
    """Очищает API кэш"""
    cache_files = ['api_cache.json', 'cache.json']
    
    for file in cache_files:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"✅ Файл {file} успешно удален")
            except Exception as e:
                print(f"❌ Ошибка при удалении файла {file}: {e}")
    
    # Очищаем директорию кэша, если она существует
    cache_dirs = ['cache', '.cache']
    
    for directory in cache_dirs:
        if os.path.exists(directory) and os.path.isdir(directory):
            try:
                shutil.rmtree(directory)
                print(f"✅ Директория {directory} успешно удалена")
            except Exception as e:
                print(f"❌ Ошибка при удалении директории {directory}: {e}")

def clear_memory_cache():
    """Создаем/перезаписываем файл с пустым кэшем в памяти"""
    empty_cache = {}
    
    try:
        with open('api_cache.json', 'w', encoding='utf-8') as f:
            json.dump(empty_cache, f)
        print("✅ Кэш в памяти очищен (создан новый пустой файл)")
    except Exception as e:
        print(f"❌ Ошибка при очистке кэша в памяти: {e}")

def create_backup():
    """Создает резервную копию данных перед очисткой"""
    backup_dir = 'backups'
    
    # Создаем директорию для резервных копий, если она не существует
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    import time
    timestamp = int(time.time())
    
    # Файлы, которые нужно скопировать
    files_to_backup = [
        'api_cache.json', 
        'user_states.json', 
        'historical_events.json',
        'admins.json',
        'bot_settings.json'
    ]
    
    for file in files_to_backup:
        if os.path.exists(file):
            try:
                backup_path = f"{backup_dir}/{file.replace('.json', '')}_backup_{timestamp}.json"
                shutil.copy2(file, backup_path)
                print(f"✅ Создана резервная копия {file} -> {backup_path}")
            except Exception as e:
                print(f"❌ Ошибка при создании резервной копии {file}: {e}")

if __name__ == "__main__":
    print("🔄 Создание резервной копии данных...")
    create_backup()
    
    print("\n🔄 Очистка API кэша...")
    clear_api_cache()
    
    print("\n🔄 Очистка кэша в памяти...")
    clear_memory_cache()
    
    print("\n✅ Операция завершена! Все кэши очищены.")
