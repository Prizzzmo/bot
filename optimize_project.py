
import os
import time
import json
import logging
import psutil
import sys
import glob
import subprocess
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('optimization_log.txt')
    ]
)
logger = logging.getLogger("optimizer")

def check_system_resources():
    """Проверяет системные ресурсы и возвращает информацию о них"""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    cpu_count = psutil.cpu_count(logical=False) or psutil.cpu_count()
    
    resources = {
        "cpu_count": cpu_count,
        "total_memory_mb": memory.total / (1024 * 1024),
        "available_memory_mb": memory.available / (1024 * 1024),
        "memory_percent": memory.percent,
        "total_disk_mb": disk.total / (1024 * 1024),
        "free_disk_mb": disk.free / (1024 * 1024),
        "disk_percent": disk.percent
    }
    
    logger.info(f"Системные ресурсы: CPU: {cpu_count}, RAM: {resources['available_memory_mb']:.1f} MB свободно ({memory.percent}% занято), Диск: {resources['free_disk_mb']:.1f} MB свободно ({disk.percent}% занято)")
    
    return resources

def get_file_size_mb(file_path):
    """Получает размер файла в МБ с обработкой ошибок"""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except Exception:
        return 0

def identify_large_files(min_size_mb=10):
    """Находит большие файлы в проекте"""
    # Пропускаем скрытые директории и виртуальные окружения в списковом включении
    valid_paths = [(root, files) for root, _, files in os.walk('.') 
                  if '/.' not in root and '\\.git' not in root]
    
    # Используем списковое включение для создания списка больших файлов
    large_files = [
        {"path": os.path.join(root, file), "size_mb": get_file_size_mb(os.path.join(root, file))}
        for root, files in valid_paths
        for file in files
        if get_file_size_mb(os.path.join(root, file)) >= min_size_mb
    ]
    
    # Сортируем по размеру (от больших к маленьким)
    large_files.sort(key=lambda x: x["size_mb"], reverse=True)
    
    # Выводим информацию о найденных файлах
    log_large_files_info(large_files, min_size_mb)
    
    return large_files

def log_large_files_info(large_files, min_size_mb):
    """Логирует информацию о найденных больших файлах"""
    if large_files:
        logger.info(f"Найдено {len(large_files)} больших файлов (>= {min_size_mb} MB)")
        # Используем списковое включение для логирования
        [logger.info(f"  {file['path']}: {file['size_mb']:.2f} MB") for file in large_files[:5]]
    else:
        logger.info(f"Больших файлов (>= {min_size_mb} MB) не найдено")

def identify_optimization_opportunities():
    """Определяет возможности для оптимизации"""
    opportunities = []
    
    # Проверяем кэш-файлы
    cache_files = glob.glob('*.json') + glob.glob('*cache*.*')
    cache_size = 0
    large_caches = []
    
    for cache_file in cache_files:
        if os.path.exists(cache_file) and os.path.isfile(cache_file):
            try:
                file_size_mb = os.path.getsize(cache_file) / (1024 * 1024)
                cache_size += file_size_mb
                
                if file_size_mb > 5:  # Кэш-файлы больше 5 МБ
                    large_caches.append({
                        "path": cache_file,
                        "size_mb": file_size_mb
                    })
            except Exception:
                continue
    
    if large_caches:
        opportunities.append({
            "type": "large_cache_files",
            "description": f"Найдены большие кэш-файлы (всего {len(large_caches)}, общий размер: {cache_size:.2f} MB)",
            "files": large_caches,
            "priority": "high" if cache_size > 50 else "medium"
        })
    
    # Проверяем файлы логов
    log_files = glob.glob('*.log') + glob.glob('logs/*.log')
    log_size = 0
    
    for log_file in log_files:
        if os.path.exists(log_file) and os.path.isfile(log_file):
            try:
                file_size_mb = os.path.getsize(log_file) / (1024 * 1024)
                log_size += file_size_mb
            except Exception:
                continue
    
    if log_size > 20:  # Если логи занимают более 20 МБ
        opportunities.append({
            "type": "large_log_files",
            "description": f"Большой объем лог-файлов (всего {len(log_files)}, общий размер: {log_size:.2f} MB)",
            "priority": "medium"
        })
    
    # Проверяем дубликаты данных в бэкапах
    backup_dirs = [
        'backups',
        os.path.join('history_db_generator', 'backups')
    ]
    
    backup_size = 0
    for backup_dir in backup_dirs:
        if os.path.exists(backup_dir) and os.path.isdir(backup_dir):
            for root, _, files in os.walk(backup_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        backup_size += os.path.getsize(file_path) / (1024 * 1024)
                    except Exception:
                        continue
    
    if backup_size > 100:  # Если бэкапы занимают более 100 МБ
        opportunities.append({
            "type": "large_backup_files",
            "description": f"Большой объем файлов резервных копий (общий размер: {backup_size:.2f} MB)",
            "priority": "high" if backup_size > 500 else "medium"
        })
    
    # Проверяем временные файлы
    temp_patterns = ['*.tmp', '*.temp', 'temp_*', 'tmp_*']
    temp_files = []
    
    for pattern in temp_patterns:
        temp_files.extend(glob.glob(pattern))
    
    if temp_files:
        temp_size = sum(os.path.getsize(f) / (1024 * 1024) for f in temp_files if os.path.isfile(f))
        opportunities.append({
            "type": "temp_files",
            "description": f"Найдены временные файлы (всего {len(temp_files)}, общий размер: {temp_size:.2f} MB)",
            "priority": "low"
        })
    
    # Проверяем, есть ли большие JSON файлы, которые можно оптимизировать
    json_files = glob.glob('*.json')
    large_jsons = []
    
    for json_file in json_files:
        if os.path.exists(json_file) and os.path.isfile(json_file):
            try:
                file_size_mb = os.path.getsize(json_file) / (1024 * 1024)
                if file_size_mb > 1:  # Если JSON файл больше 1 МБ
                    # Проверяем, можно ли его оптимизировать
                    with open(json_file, 'r', encoding='utf-8') as f:
                        # Читаем первые 1000 байт для проверки форматирования
                        content_sample = f.read(1000)
                        if '  ' in content_sample or '    ' in content_sample:
                            large_jsons.append({
                                "path": json_file,
                                "size_mb": file_size_mb
                            })
            except Exception:
                continue
    
    if large_jsons:
        opportunities.append({
            "type": "unoptimized_json",
            "description": f"Найдены неоптимизированные JSON файлы (всего {len(large_jsons)})",
            "files": large_jsons,
            "priority": "medium"
        })
    
    return opportunities

def optimize_project(opportunities):
    """Выполняет оптимизации на основе обнаруженных возможностей"""
    optimizations_applied = []
    
    for opportunity in opportunities:
        if opportunity["type"] == "large_cache_files" and opportunity["priority"] in ["high", "medium"]:
            # Очищаем большие кэш-файлы
            for cache_file in opportunity.get("files", []):
                file_path = cache_file["path"]
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    try:
                        # Для JSON файлов - загружаем и сохраняем в компактном формате
                        if file_path.endswith('.json'):
                            with open(file_path, 'r', encoding='utf-8') as f:
                                try:
                                    data = json.load(f)
                                    # Если это кэш, оставляем только небольшую часть новых записей
                                    if len(data) > 100 and any(cache_name in file_path.lower() for cache_name in ['cache', 'api']):
                                        # Для словарей - оставляем 20% самых новых элементов
                                        if isinstance(data, dict):
                                            try:
                                                # Сортируем по времени последнего доступа, если такое поле есть
                                                sorted_items = []
                                                for key, value in data.items():
                                                    if isinstance(value, dict) and "last_accessed" in value:
                                                        sorted_items.append((key, value, value.get("last_accessed", 0)))
                                                
                                                if sorted_items:
                                                    # Сортируем от новых к старым
                                                    sorted_items.sort(key=lambda x: x[2], reverse=True)
                                                    # Оставляем только 20% элементов
                                                    keep_count = max(20, len(sorted_items) // 5)
                                                    new_data = {}
                                                    for key, value, _ in sorted_items[:keep_count]:
                                                        new_data[key] = value
                                                    data = new_data
                                            except Exception:
                                                # Если сортировка не удалась, просто обрезаем словарь
                                                data = dict(list(data.items())[:100])
                                        # Для списков - оставляем последние элементы
                                        elif isinstance(data, list):
                                            data = data[-100:]
                                    
                                    # Сохраняем в компактном формате
                                    with open(file_path, 'w', encoding='utf-8') as f:
                                        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
                                    
                                    old_size = cache_file["size_mb"]
                                    new_size = os.path.getsize(file_path) / (1024 * 1024)
                                    saved = old_size - new_size
                                    
                                    optimizations_applied.append({
                                        "type": "cache_optimized",
                                        "file": file_path,
                                        "old_size_mb": old_size,
                                        "new_size_mb": new_size,
                                        "saved_mb": saved
                                    })
                                    
                                    logger.info(f"Оптимизирован кэш-файл {file_path}: {old_size:.2f} MB -> {new_size:.2f} MB (сохранено {saved:.2f} MB)")
                                except Exception as e:
                                    logger.error(f"Ошибка при оптимизации JSON файла {file_path}: {e}")
                        else:
                            # Для не-JSON файлов просто очищаем, если они выглядят как кэш или временные данные
                            if any(temp_name in file_path.lower() for temp_name in ['temp', 'tmp', 'cache', '~']):
                                old_size = os.path.getsize(file_path) / (1024 * 1024)
                                os.remove(file_path)
                                
                                optimizations_applied.append({
                                    "type": "cache_removed",
                                    "file": file_path,
                                    "old_size_mb": old_size,
                                    "saved_mb": old_size
                                })
                                
                                logger.info(f"Удален кэш-файл {file_path}: сохранено {old_size:.2f} MB")
                    except Exception as e:
                        logger.error(f"Ошибка при очистке кэш-файла {file_path}: {e}")
        
        elif opportunity["type"] == "large_log_files" and opportunity["priority"] in ["high", "medium"]:
            # Очищаем старые логи
            log_dir = 'logs'
            if os.path.exists(log_dir) and os.path.isdir(log_dir):
                try:
                    log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith('.log')]
                    # Сортируем по времени изменения (от старых к новым)
                    log_files.sort(key=lambda x: os.path.getmtime(x))
                    
                    # Оставляем только 5 последних лог-файлов
                    if len(log_files) > 5:
                        for old_log in log_files[:-5]:
                            if os.path.exists(old_log):
                                old_size = os.path.getsize(old_log) / (1024 * 1024)
                                os.remove(old_log)
                                
                                optimizations_applied.append({
                                    "type": "log_removed",
                                    "file": old_log,
                                    "old_size_mb": old_size,
                                    "saved_mb": old_size
                                })
                                
                                logger.info(f"Удален старый лог-файл {old_log}: сохранено {old_size:.2f} MB")
                except Exception as e:
                    logger.error(f"Ошибка при очистке лог-файлов: {e}")
        
        elif opportunity["type"] == "large_backup_files" and opportunity["priority"] in ["high", "medium"]:
            # Запускаем сценарий очистки бэкапов
            try:
                # Проверяем существование скрипта для очистки
                if os.path.exists('cleanup_old_backups.py'):
                    logger.info("Запуск скрипта очистки старых бэкапов...")
                    
                    # Запускаем скрипт очистки как подпроцесс
                    result = subprocess.run([sys.executable, 'cleanup_old_backups.py'], 
                                          capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        logger.info("Скрипт очистки бэкапов успешно завершен")
                        optimizations_applied.append({
                            "type": "backups_cleaned",
                            "details": "Запущен скрипт cleanup_old_backups.py"
                        })
                    else:
                        logger.error(f"Ошибка при запуске скрипта очистки: {result.stderr}")
                else:
                    logger.warning("Скрипт очистки бэкапов не найден!")
            except Exception as e:
                logger.error(f"Ошибка при очистке бэкапов: {e}")
        
        elif opportunity["type"] == "unoptimized_json":
            # Оптимизируем форматирование JSON файлов
            for json_file in opportunity.get("files", []):
                file_path = json_file["path"]
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    try:
                        old_size = os.path.getsize(file_path) / (1024 * 1024)
                        
                        # Загружаем и пересохраняем JSON в компактном формате
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
                        
                        new_size = os.path.getsize(file_path) / (1024 * 1024)
                        saved = old_size - new_size
                        
                        optimizations_applied.append({
                            "type": "json_optimized",
                            "file": file_path,
                            "old_size_mb": old_size,
                            "new_size_mb": new_size,
                            "saved_mb": saved
                        })
                        
                        logger.info(f"Оптимизирован JSON файл {file_path}: {old_size:.2f} MB -> {new_size:.2f} MB (сохранено {saved:.2f} MB)")
                    except Exception as e:
                        logger.error(f"Ошибка при оптимизации JSON файла {file_path}: {e}")
        
        elif opportunity["type"] == "temp_files":
            # Удаляем временные файлы
            for temp_pattern in ['*.tmp', '*.temp', 'temp_*', 'tmp_*']:
                for file_path in glob.glob(temp_pattern):
                    if os.path.exists(file_path) and os.path.isfile(file_path):
                        try:
                            old_size = os.path.getsize(file_path) / (1024 * 1024)
                            os.remove(file_path)
                            
                            optimizations_applied.append({
                                "type": "temp_removed",
                                "file": file_path,
                                "old_size_mb": old_size,
                                "saved_mb": old_size
                            })
                            
                            logger.info(f"Удален временный файл {file_path}: сохранено {old_size:.2f} MB")
                        except Exception as e:
                            logger.error(f"Ошибка при удалении временного файла {file_path}: {e}")
    
    return optimizations_applied

def recommend_code_optimizations():
    """Рекомендует оптимизации для кода на основе анализа файлов"""
    recommendations = []
    
    # Проверяем файлы Python для потенциальных оптимизаций
    py_files = []
    for root, _, files in os.walk('.'):
        # Пропускаем скрытые директории и виртуальные окружения
        if '/.' in root or '\\.git' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    
    # Анализируем каждый файл
    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Проверяем импорты
                if 'import *' in content:
                    recommendations.append({
                        "file": py_file,
                        "type": "import_optimization",
                        "description": "Используйте конкретные импорты вместо 'import *' для уменьшения использования памяти"
                    })
                
                # Проверяем на глобальные переменные
                global_vars = len([line for line in content.split('\n') if line.strip() and not line.strip().startswith((' ', 'def', 'class', 'import', 'from', '#'))])
                if global_vars > 10:
                    recommendations.append({
                        "file": py_file,
                        "type": "global_vars",
                        "description": f"Файл содержит много глобальных переменных ({global_vars}), рассмотрите упаковку их в классы или функции"
                    })
                
                # Проверяем неоптимальные паттерны в циклах
                if 'for ' in content and '.append(' in content:
                    # Проверяем использование append в циклах вместо списковых включений
                    recommendations.append({
                        "file": py_file,
                        "type": "loop_optimization",
                        "description": "Рассмотрите использование списковых включений вместо циклов с append для построения списков"
                    })
                
                # Проверяем на большие функции
                lines = content.split('\n')
                in_function = False
                function_lines = 0
                large_functions = 0
                
                for line in lines:
                    if line.strip().startswith('def '):
                        if in_function and function_lines > 50:  # Если функция более 50 строк
                            large_functions += 1
                        in_function = True
                        function_lines = 0
                    elif in_function:
                        function_lines += 1
                
                if large_functions > 0:
                    recommendations.append({
                        "file": py_file,
                        "type": "large_functions",
                        "description": f"Файл содержит {large_functions} больших функций (>50 строк), рассмотрите их разделение на более мелкие"
                    })
                
                # Проверяем отсутствие кэширования в частых операциях
                if 'cache' not in content.lower() and ('api' in py_file.lower() or 'request' in content.lower()):
                    recommendations.append({
                        "file": py_file,
                        "type": "missing_cache",
                        "description": "Рассмотрите добавление кэширования для API запросов и частых операций"
                    })
        except Exception as e:
            logger.warning(f"Ошибка при анализе файла {py_file}: {e}")
    
    return recommendations

def main():
    """Основная функция оптимизации проекта"""
    start_time = time.time()
    
    logger.info("Запуск оптимизации проекта...")
    
    # Проверяем системные ресурсы
    resources = check_system_resources()
    
    # Находим большие файлы
    large_files = identify_large_files()
    
    # Определяем возможности для оптимизации
    opportunities = identify_optimization_opportunities()
    
    # Выполняем оптимизации
    optimizations = optimize_project(opportunities)
    
    # Рекомендуем оптимизации кода
    code_recommendations = recommend_code_optimizations()
    
    # Формируем итоговый отчет
    report = {
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "execution_time_sec": time.time() - start_time,
        "system_resources": resources,
        "large_files": large_files,
        "optimization_opportunities": opportunities,
        "optimizations_applied": optimizations,
        "code_recommendations": code_recommendations
    }
    
    # Сохраняем отчет
    with open('optimization_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # Выводим сводку
    total_saved = sum(opt.get("saved_mb", 0) for opt in optimizations)
    logger.info(f"Оптимизация завершена за {report['execution_time_sec']:.2f} секунд")
    logger.info(f"Всего освобождено места: {total_saved:.2f} MB")
    logger.info(f"Применено оптимизаций: {len(optimizations)}")
    logger.info(f"Рекомендаций по коду: {len(code_recommendations)}")
    logger.info(f"Подробный отчет сохранен в 'optimization_report.json'")

if __name__ == "__main__":
    main()
