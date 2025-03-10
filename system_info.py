
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для получения информации о системе.
Используется для диагностики и мониторинга.
"""

import os
import psutil
import time
import datetime
import json
import platform
import logging

# Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger("SystemInfo")

def get_system_info():
    """Получает общую информацию о системе"""
    try:
        info = {
            "system": platform.system(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent,
            },
            "cpu": {
                "usage_percent": psutil.cpu_percent(interval=1),
                "cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
            },
            "boot_time": psutil.boot_time(),
            "timestamp": time.time()
        }
        return info
    except Exception as e:
        logger.error(f"Ошибка при получении информации о системе: {e}")
        return None

def get_process_info():
    """Получает информацию о процессах Python"""
    try:
        current_pid = os.getpid()
        python_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_info', 'cpu_percent', 'create_time', 'cmdline']):
            if 'python' in proc.info['name'].lower() or 'python' in ' '.join(proc.info.get('cmdline', [])).lower():
                try:
                    # Добавляем информацию о текущем процессе
                    is_current = proc.info['pid'] == current_pid
                    
                    # Получаем память в МБ и процент использования
                    memory_mb = proc.info['memory_info'].rss / (1024 * 1024) if proc.info.get('memory_info') else 0
                    
                    # Вычисляем время работы
                    uptime_seconds = time.time() - proc.info['create_time'] if proc.info.get('create_time') else 0
                    uptime = str(datetime.timedelta(seconds=int(uptime_seconds)))
                    
                    # Получаем командную строку
                    cmdline = ' '.join(proc.info.get('cmdline', []))
                    
                    python_processes.append({
                        "pid": proc.info['pid'],
                        "username": proc.info.get('username', 'unknown'),
                        "name": proc.info['name'],
                        "memory_mb": round(memory_mb, 2),
                        "cpu_percent": proc.info.get('cpu_percent', 0),
                        "uptime": uptime,
                        "uptime_seconds": uptime_seconds,
                        "cmdline": cmdline,
                        "is_current": is_current
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        # Сортируем по использованию памяти
        python_processes.sort(key=lambda x: x['memory_mb'], reverse=True)
        
        return python_processes
    except Exception as e:
        logger.error(f"Ошибка при получении информации о процессах: {e}")
        return []

def get_bot_specific_info():
    """Получает информацию, специфичную для бота"""
    try:
        bot_info = {
            "files": {},
            "stats": {}
        }
        
        # Получаем информацию о размере файлов
        important_files = [
            'api_cache.json', 
            'user_states.json', 
            'historical_events.json', 
            'admins.json', 
            'bot_settings.json'
        ]
        
        for file_name in important_files:
            if os.path.exists(file_name):
                file_size = os.path.getsize(file_name) / 1024  # KB
                bot_info["files"][file_name] = {
                    "size_kb": round(file_size, 2),
                    "last_modified": os.path.getmtime(file_name)
                }
        
        # Получаем статистику логов
        log_dir = "logs"
        log_stats = {
            "total_size_mb": 0,
            "count": 0,
            "latest_file": None,
            "latest_time": 0
        }
        
        if os.path.exists(log_dir) and os.path.isdir(log_dir):
            for file_name in os.listdir(log_dir):
                if file_name.startswith("bot_log_") or file_name == "bot.log":
                    file_path = os.path.join(log_dir, file_name)
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    log_stats["total_size_mb"] += file_size
                    log_stats["count"] += 1
                    
                    modified_time = os.path.getmtime(file_path)
                    if modified_time > log_stats["latest_time"]:
                        log_stats["latest_time"] = modified_time
                        log_stats["latest_file"] = file_name
            
            log_stats["total_size_mb"] = round(log_stats["total_size_mb"], 2)
        
        bot_info["stats"]["logs"] = log_stats
        
        # Получаем статистику бэкапов
        backup_dir = "backups"
        backup_stats = {
            "total_size_mb": 0,
            "count": 0,
            "latest_file": None,
            "latest_time": 0
        }
        
        if os.path.exists(backup_dir) and os.path.isdir(backup_dir):
            for file_name in os.listdir(backup_dir):
                file_path = os.path.join(backup_dir, file_name)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    backup_stats["total_size_mb"] += file_size
                    backup_stats["count"] += 1
                    
                    modified_time = os.path.getmtime(file_path)
                    if modified_time > backup_stats["latest_time"]:
                        backup_stats["latest_time"] = modified_time
                        backup_stats["latest_file"] = file_name
            
            backup_stats["total_size_mb"] = round(backup_stats["total_size_mb"], 2)
        
        bot_info["stats"]["backups"] = backup_stats
        
        return bot_info
    except Exception as e:
        logger.error(f"Ошибка при получении информации о боте: {e}")
        return {}

def save_info_to_file():
    """Сохраняет информацию о системе в файл"""
    try:
        system_info = get_system_info()
        process_info = get_process_info()
        bot_info = get_bot_specific_info()
        
        all_info = {
            "timestamp": time.time(),
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system": system_info,
            "processes": process_info,
            "bot": bot_info
        }
        
        # Создаем директорию для системной информации, если не существует
        if not os.path.exists('system_info'):
            os.makedirs('system_info')
        
        # Сохраняем в файл с текущей датой
        file_name = f"system_info_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path = os.path.join('system_info', file_name)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(all_info, f, indent=2)
        
        logger.info(f"Информация о системе сохранена в файл {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Ошибка при сохранении информации о системе: {e}")
        return None

def format_info_for_display():
    """Форматирует информацию о системе для отображения в консоли"""
    try:
        system_info = get_system_info()
        process_info = get_process_info()
        bot_info = get_bot_specific_info()
        
        # Форматируем системную информацию
        system_text = f"=== Системная информация ===\n"
        system_text += f"Операционная система: {system_info['system']} ({system_info['platform']})\n"
        system_text += f"Python: {system_info['python_version']}\n"
        system_text += f"\nПроцессор: {system_info['processor']}\n"
        system_text += f"Ядер: {system_info['cpu']['cores']} (логических: {system_info['cpu']['logical_cores']})\n"
        system_text += f"Загрузка CPU: {system_info['cpu']['usage_percent']}%\n"
        
        system_text += f"\nПамять:\n"
        system_text += f"  Всего: {system_info['memory']['total'] / (1024*1024*1024):.2f} ГБ\n"
        system_text += f"  Доступно: {system_info['memory']['available'] / (1024*1024*1024):.2f} ГБ\n"
        system_text += f"  Использовано: {system_info['memory']['percent']}%\n"
        
        system_text += f"\nДиск:\n"
        system_text += f"  Всего: {system_info['disk']['total'] / (1024*1024*1024):.2f} ГБ\n"
        system_text += f"  Свободно: {system_info['disk']['free'] / (1024*1024*1024):.2f} ГБ\n"
        system_text += f"  Использовано: {system_info['disk']['percent']}%\n"
        
        # Форматируем информацию о процессах
        process_text = f"\n=== Процессы Python ===\n"
        for i, proc in enumerate(process_info[:5], 1):
            process_text += f"{i}. PID: {proc['pid']}"
            if proc['is_current']:
                process_text += " (Текущий процесс)"
            process_text += f"\n   Память: {proc['memory_mb']:.2f} МБ\n"
            process_text += f"   CPU: {proc['cpu_percent']}%\n"
            process_text += f"   Время работы: {proc['uptime']}\n"
            if len(proc['cmdline']) > 50:
                process_text += f"   Команда: {proc['cmdline'][:50]}...\n"
            else:
                process_text += f"   Команда: {proc['cmdline']}\n"
        
        # Форматируем информацию о боте
        bot_text = f"\n=== Информация о боте ===\n"
        
        # Информация о файлах
        bot_text += f"\nФайлы:\n"
        for file_name, file_info in bot_info['files'].items():
            modified_time = datetime.datetime.fromtimestamp(file_info['last_modified']).strftime("%Y-%m-%d %H:%M:%S")
            bot_text += f"  {file_name}: {file_info['size_kb']:.2f} КБ (изменен: {modified_time})\n"
        
        # Информация о логах
        logs = bot_info['stats'].get('logs', {})
        if logs:
            bot_text += f"\nЛоги:\n"
            bot_text += f"  Всего: {logs['count']} файлов, {logs['total_size_mb']:.2f} МБ\n"
            if logs['latest_file']:
                latest_time = datetime.datetime.fromtimestamp(logs['latest_time']).strftime("%Y-%m-%d %H:%M:%S")
                bot_text += f"  Последний: {logs['latest_file']} (изменен: {latest_time})\n"
        
        # Информация о бэкапах
        backups = bot_info['stats'].get('backups', {})
        if backups:
            bot_text += f"\nБэкапы:\n"
            bot_text += f"  Всего: {backups['count']} файлов, {backups['total_size_mb']:.2f} МБ\n"
            if backups['latest_file']:
                latest_time = datetime.datetime.fromtimestamp(backups['latest_time']).strftime("%Y-%m-%d %H:%M:%S")
                bot_text += f"  Последний: {backups['latest_file']} (создан: {latest_time})\n"
        
        return system_text + process_text + bot_text
    except Exception as e:
        logger.error(f"Ошибка при форматировании информации о системе: {e}")
        return f"Ошибка при получении информации о системе: {e}"

def main():
    """Основная функция скрипта"""
    logger.info("Запуск получения информации о системе")
    
    # Получаем и выводим информацию
    info_text = format_info_for_display()
    print(info_text)
    
    # Сохраняем в файл
    save_path = save_info_to_file()
    if save_path:
        print(f"\nИнформация сохранена в файл: {save_path}")
    
    logger.info("Получение информации о системе завершено")

if __name__ == "__main__":
    main()
