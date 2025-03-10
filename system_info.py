#!/usr/bin/env python3
import os
import sys
import json
import psutil
import datetime

def get_system_info():
    """Получает информацию о системе и возвращает ее в виде словаря"""
    # Информация о системе
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Список Python процессов
    python_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent']):
        try:
            if 'python' in proc.info['name'].lower():
                proc_info = proc.info.copy()
                proc_info['memory_mb'] = proc.memory_info().rss / (1024 * 1024)
                python_processes.append(proc_info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Сортируем по использованию памяти
    python_processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)

    # Формируем результат
    system_info = {
        'cpu': {
            'percent': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count(),
            'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else None
        },
        'memory': {
            'total_gb': mem.total / (1024 * 1024 * 1024),
            'used_gb': mem.used / (1024 * 1024 * 1024),
            'free_gb': mem.free / (1024 * 1024 * 1024),
            'percent': mem.percent
        },
        'disk': {
            'total_gb': disk.total / (1024 * 1024 * 1024),
            'used_gb': disk.used / (1024 * 1024 * 1024),
            'free_gb': disk.free / (1024 * 1024 * 1024),
            'percent': disk.percent
        },
        'python_processes': python_processes[:5],  # Только топ 5 процессов
        'timestamp': datetime.datetime.now().isoformat()
    }

    return system_info

def print_system_info(system_info):
    """Выводит информацию о системе в консоль"""
    print("\n=== Информация о системе ===")

    # Вывод информации о процессоре
    print("\nПроцессор:")
    print(f"  Загрузка CPU: {system_info['cpu']['percent']}%")
    print(f"  Количество ядер: {system_info['cpu']['count']}")
    if system_info['cpu']['load_avg']:
        print(f"  Средняя нагрузка: {', '.join([str(round(x, 2)) for x in system_info['cpu']['load_avg']])}")

    # Вывод информации о памяти
    print("\nПамять:")
    print(f"  Всего: {system_info['memory']['total_gb']:.2f} ГБ")
    print(f"  Используется: {system_info['memory']['used_gb']:.2f} ГБ ({system_info['memory']['percent']}%)")
    print(f"  Свободно: {system_info['memory']['free_gb']:.2f} ГБ")

    # Вывод информации о диске
    print("\nДиск:")
    print(f"  Всего: {system_info['disk']['total_gb']:.2f} ГБ")
    print(f"  Используется: {system_info['disk']['used_gb']:.2f} ГБ ({system_info['disk']['percent']}%)")
    print(f"  Свободно: {system_info['disk']['free_gb']:.2f} ГБ")

    # Вывод информации о Python процессах
    print("\nPython процессы (топ 5):")
    if system_info['python_processes']:
        for i, proc in enumerate(system_info['python_processes'], 1):
            print(f"  {i}. PID: {proc['pid']}, Память: {proc.get('memory_mb', 0):.2f} МБ")
    else:
        print("  Нет активных Python процессов")

    print(f"\nВремя проверки: {system_info['timestamp']}")
    print("\n==============================\n")

def save_system_info(system_info, filename="system_info.json"):
    """Сохраняет информацию о системе в JSON-файл"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(system_info, f, indent=4, ensure_ascii=False)
        print(f"Информация о системе сохранена в файл {filename}")
        return True
    except Exception as e:
        print(f"Ошибка при сохранении информации о системе: {e}")
        return False

if __name__ == "__main__":
    try:
        system_info = get_system_info()
        print_system_info(system_info)

        # Сохраняем информацию, если передан флаг --save
        if len(sys.argv) > 1 and sys.argv[1] == "--save":
            save_system_info(system_info)
    except Exception as e:
        print(f"Ошибка при получении информации о системе: {e}")