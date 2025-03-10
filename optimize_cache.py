
import os
import json
import time
import sys
import logging
import argparse
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("cache_optimizer")

def get_cache_file_size(file_path):
    """Получение размера файла кэша в МБ"""
    try:
        if os.path.exists(file_path):
            return os.path.getsize(file_path) / (1024 * 1024)
        return 0
    except Exception as e:
        logger.error(f"Ошибка при определении размера файла {file_path}: {e}")
        return 0

def clean_expired_entries(file_path, max_age_hours=24):
    """Очистка устаревших записей из файла кэша"""
    try:
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            logger.info(f"Файл кэша {file_path} пуст или не существует")
            return 0

        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                cache_data = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Ошибка чтения JSON из файла {file_path}")
                return 0

        if isinstance(cache_data, dict):
            # Формат API кэша
            current_time = time.time()
            expired_keys = []
            
            for key, item in list(cache_data.items()):
                # Проверяем по TTL, если есть
                if "ttl" in item and item["ttl"] and current_time > item["created_at"] + item["ttl"]:
                    expired_keys.append(key)
                    continue
                
                # Проверяем по времени последнего доступа
                if "last_accessed" in item:
                    last_accessed = item["last_accessed"]
                    if current_time - last_accessed > max_age_hours * 3600:
                        expired_keys.append(key)
            
            # Удаляем устаревшие записи
            for key in expired_keys:
                del cache_data[key]
            
            # Сохраняем обновленный кэш
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            return len(expired_keys)
        
        elif isinstance(cache_data, list):
            # Формат метрик или другой список
            cutoff_time = time.time() - (max_age_hours * 3600)
            original_count = len(cache_data)
            
            # Фильтруем по времени
            cache_data = [item for item in cache_data if not ("timestamp" in item and item["timestamp"] < cutoff_time)]
            
            # Сохраняем обновленный кэш
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            return original_count - len(cache_data)
        
        return 0
    
    except Exception as e:
        logger.error(f"Ошибка при очистке устаревших записей из {file_path}: {e}")
        return 0

def optimize_cache_file(file_path, min_file_size_mb=10):
    """Оптимизирует файл кэша если он превышает указанный размер"""
    try:
        file_size_mb = get_cache_file_size(file_path)
        
        if file_size_mb >= min_file_size_mb:
            logger.info(f"Оптимизация файла кэша {file_path} (размер: {file_size_mb:.2f} MB)")
            
            # Сначала чистим устаревшие записи
            removed_count = clean_expired_entries(file_path)
            
            # Если файл всё ещё большой, удаляем 25% самых старых записей
            if get_cache_file_size(file_path) >= min_file_size_mb:
                with open(file_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                if isinstance(cache_data, dict):
                    # Сортируем ключи по времени последнего доступа
                    if all("last_accessed" in item for item in cache_data.values()):
                        sorted_keys = sorted(
                            cache_data.keys(),
                            key=lambda k: cache_data[k].get("last_accessed", 0)
                        )
                        
                        # Удаляем 25% самых старых записей
                        keys_to_remove = sorted_keys[:max(1, len(sorted_keys) // 4)]
                        
                        for key in keys_to_remove:
                            del cache_data[key]
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(cache_data, f, ensure_ascii=False, indent=2)
                        
                        removed_count += len(keys_to_remove)
                
                elif isinstance(cache_data, list):
                    # Для списка оставляем только 75% самых новых записей
                    if cache_data and "timestamp" in cache_data[0]:
                        cache_data.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
                        
                        # Оставляем только 75% новых записей
                        items_to_keep = max(1, int(len(cache_data) * 0.75))
                        original_count = len(cache_data)
                        cache_data = cache_data[:items_to_keep]
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(cache_data, f, ensure_ascii=False, indent=2)
                        
                        removed_count += (original_count - items_to_keep)
            
            logger.info(f"Оптимизация завершена. Удалено {removed_count} записей.")
            logger.info(f"Новый размер файла: {get_cache_file_size(file_path):.2f} MB")
            
            return removed_count
        else:
            logger.info(f"Файл {file_path} не требует оптимизации (размер: {file_size_mb:.2f} MB)")
            return 0
    
    except Exception as e:
        logger.error(f"Ошибка при оптимизации файла {file_path}: {e}")
        return 0

def main():
    parser = argparse.ArgumentParser(description="Оптимизатор кэша для улучшения производительности")
    parser.add_argument("--min-size", type=float, default=5.0, help="Минимальный размер файла для оптимизации (МБ)")
    parser.add_argument("--max-age", type=int, default=24, help="Максимальный возраст записей в часах")
    parser.add_argument("--silent", action="store_true", help="Тихий режим без вывода")
    args = parser.parse_args()
    
    if args.silent:
        logger.setLevel(logging.ERROR)
    
    # Файлы кэша для оптимизации
    cache_files = [
        "api_cache.json",
        "local_cache.json",
        "performance_metrics.json"
    ]
    
    total_removed = 0
    for file_path in cache_files:
        if os.path.exists(file_path):
            removed = optimize_cache_file(file_path, min_file_size_mb=args.min_size)
            total_removed += removed
    
    logger.info(f"Оптимизация кэша завершена. Всего удалено {total_removed} записей.")

if __name__ == "__main__":
    main()
