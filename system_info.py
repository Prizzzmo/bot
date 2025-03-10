#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для отображения информации о системе и рабочем окружении бота
"""

import os
import sys
import platform
import psutil
import json
import datetime
import time
import logging

# Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger("SystemInfo")

def get_system_info():
    """Получает системную информацию"""
    try:
        info = {
            "system": {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "python_implementation": platform.python_implementation(),
            },
            "memory": {
                "total": psutil.virtual_memory().total / (1024**3),  # GB
                "available": psutil.virtual_memory().available / (1024**3),  # GB
                "used": psutil.virtual_memory().used / (1024**3),  # GB
                "percent": psutil.virtual_memory().percent,
            },
            "disk": {
                "total": psutil.disk_usage('/').total / (1024**3),  # GB
                "used": psutil.disk_usage('/').used / (1024**3),  # GB
                "free": psutil.disk_usage('/').free / (1024**3),  # GB
                "percent": psutil.disk_usage('/').percent,
            },
            "cpu": {
                "physical_cores": psutil.cpu_count(logical=False),
                "total_cores": psutil.cpu_count(logical=True),
                "current_frequency": psutil.cpu_freq().current if psutil.cpu_freq() else "N/A",
                "usage_per_core": [percentage for percentage in psutil.cpu_percent(interval=1, percpu=True)],
                "total_usage": psutil.cpu_percent(interval=1),
            },
            "network": {
                "interfaces": list(psutil.net_if_addrs().keys()),
                "stats": {k: v._asdict() for k, v in psutil.net_if_stats().items()},
            },
            "time": {
                "current_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "timezone": time.tzname,
                "uptime": time.time() - psutil.boot_time(),
            },
            "bot": {
                "start_time": time.ctime(os.path.getctime("bot.log")) if os.path.exists("bot.log") else "N/A",
                "admin_count": len(json.load(open("admins.json"))["admin_ids"]) + len(json.load(open("admins.json"))["super_admin_ids"]) if os.path.exists("admins.json") else 0,
                "user_count": len(json.load(open("user_states.json"))) if os.path.exists("user_states.json") else 0,
                "replit_environment": "True" if "REPL_ID" in os.environ else "False",
            }
        }
        return info
    except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
        logger.error(f"Ошибка при получении информации о системе: {e}")
        return None


def display_system_info():
    """Отображает системную информацию в читаемом формате"""
    info = get_system_info()
    if info is None:
        print("Ошибка при сборе информации.")
        return

    print("\n" + "="*50)
    print(" "*15 + "СИСТЕМНАЯ ИНФОРМАЦИЯ")
    print("="*50)

    # Операционная система
    print("\n[ОПЕРАЦИОННАЯ СИСТЕМА]")
    print(f"Платформа: {info['system']['platform']} {info['system']['platform_release']} ({info['system']['platform_version']})")
    print(f"Архитектура: {info['system']['architecture']}")
    print(f"Процессор: {info['system']['processor']}")

    # Python
    print("\n[PYTHON]")
    print(f"Версия: {info['system']['python_version']}")
    print(f"Реализация: {info['system']['python_implementation']}")

    # CPU
    print("\n[ПРОЦЕССОР]")
    print(f"Физические ядра: {info['cpu']['physical_cores']}")
    print(f"Всего ядер: {info['cpu']['total_cores']}")
    print(f"Текущая частота: {info['cpu']['current_frequency']} МГц" if info['cpu']['current_frequency'] != "N/A" else "Текущая частота: Н/Д")
    print(f"Общая загрузка: {info['cpu']['total_usage']}%")
    print("Загрузка по ядрам:", end=" ")
    for i, percentage in enumerate(info['cpu']['usage_per_core']):
        print(f"Ядро {i}: {percentage}%", end="; ")
    print()

    # Память
    print("\n[ОПЕРАТИВНАЯ ПАМЯТЬ]")
    print(f"Всего: {info['memory']['total']:.2f} ГБ")
    print(f"Доступно: {info['memory']['available']:.2f} ГБ")
    print(f"Используется: {info['memory']['used']:.2f} ГБ ({info['memory']['percent']}%)")

    # Диск
    print("\n[ДИСКОВОЕ ПРОСТРАНСТВО]")
    print(f"Всего: {info['disk']['total']:.2f} ГБ")
    print(f"Используется: {info['disk']['used']:.2f} ГБ ({info['disk']['percent']}%)")
    print(f"Свободно: {info['disk']['free']:.2f} ГБ")

    # Время
    print("\n[ВРЕМЯ]")
    print(f"Текущее время: {info['time']['current_time']}")
    print(f"Аптайм системы: {datetime.timedelta(seconds=int(info['time']['uptime']))}")

    # Информация о боте
    print("\n[БОТ]")
    print(f"Время запуска: {info['bot']['start_time']}")
    print(f"Количество администраторов: {info['bot']['admin_count']}")
    print(f"Количество пользователей: {info['bot']['user_count']}")
    print(f"Replit окружение: {info['bot']['replit_environment']}")

    print("\n" + "="*50 + "\n")

def save_info_to_file():
    """Сохраняет информацию о системе в файл"""
    try:
        system_info = get_system_info()
        if system_info is None:
            return None

        all_info = {
            "timestamp": time.time(),
            "datetime": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system": system_info
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

def main():
    """Основная функция скрипта"""
    logger.info("Запуск получения информации о системе")

    # Получаем и выводим информацию
    display_system_info()

    # Сохраняем в файл
    save_path = save_info_to_file()
    if save_path:
        print(f"\nИнформация сохранена в файл: {save_path}")

    logger.info("Получение информации о системе завершено")

if __name__ == "__main__":
    main()