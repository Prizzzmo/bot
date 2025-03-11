"""
Скрипт для запуска всех оптимизаций проекта
"""

import os
import time
import json
import subprocess
import sys

try:
    import astor
except ImportError:
    print("❌ Ошибка: Пакет astor не установлен. Устанавливаем...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "astor"])
    import astor

def print_progress(current, total, message="", width=50):
    """Выводит прогресс-бар в консоль"""
    progress = int(width * current / total)
    bar = "█" * progress + "░" * (width - progress)
    percent = 100 * current / total
    print(f"\r[{bar}] {percent:.1f}% {message}", end="")
    if current == total:
        print()

def run_command(command, description):
    """Запускает команду в подпроцессе с отображением прогресса"""
    print(f"\n{description}...")
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Читаем вывод команды
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"  {output.strip()}")

        # Проверяем, успешно ли завершилась команда
        if process.returncode == 0:
            print(f"✅ {description} успешно завершено")
            return True
        else:
            error = process.stderr.read()
            print(f"❌ Ошибка: {error}")
            return False
    except Exception as e:
        print(f"❌ Ошибка при выполнении команды: {e}")
        return False

def optimize_project():
    """Запускает все скрипты оптимизации проекта"""
    start_time = time.time()

    print("🔄 Запуск комплексной оптимизации проекта\n")

    # Список шагов оптимизации
    optimization_steps = [
        {
            "name": "Генерация отчета об оптимизации",
            "command": [sys.executable, "optimize_project.py"],
            "description": "Анализ проекта и генерация рекомендаций"
        },
        {
            "name": "Очистка кэша",
            "command": [sys.executable, "clear_cache.py"],
            "description": "Очистка кэша и временных файлов"
        },
        {
            "name": "Оптимизация кода",
            "command": [sys.executable, "code_optimizer.py"],
            "description": "Автоматическая оптимизация кода проекта"
        },
        {
            "name": "Анализ больших функций",
            "command": [sys.executable, "split_large_functions.py"],
            "description": "Анализ и предложения по разбиению больших функций"
        }
    ]

    # Запускаем каждый шаг оптимизации
    total_steps = len(optimization_steps)
    successful_steps = 0

    for i, step in enumerate(optimization_steps, 1):
        print(f"\n[{i}/{total_steps}] {step['name']}")
        success = run_command(step["command"], step["description"])
        if success:
            successful_steps += 1
        print_progress(i, total_steps, f"Выполнено шагов: {i}/{total_steps}")

    # Вычисляем процент успешных оптимизаций
    success_percent = 100 * successful_steps / total_steps

    # Вычисляем общее время выполнения
    execution_time = time.time() - start_time
    minutes = int(execution_time // 60)
    seconds = int(execution_time % 60)

    # Выводим итоговую информацию
    print(f"\n✨ Оптимизация завершена за {minutes} мин {seconds} сек")
    print(f"✅ Успешно выполнено {successful_steps} из {total_steps} шагов ({success_percent:.1f}%)")

    # Проверяем наличие отчета об оптимизации
    if os.path.exists('optimization_report.json'):
        try:
            with open('optimization_report.json', 'r', encoding='utf-8') as f:
                report = json.load(f)

            # Выводим сводку по результатам оптимизации
            optimizations_applied = report.get("optimizations_applied", [])
            if optimizations_applied:
                print(f"\n📊 Применено {len(optimizations_applied)} оптимизаций:")
                for opt in optimizations_applied[:5]:  # Показываем первые 5 оптимизаций
                    opt_type = opt.get("type", "unknown")
                    print(f"  - {opt_type}")
                if len(optimizations_applied) > 5:
                    print(f"  - ... и еще {len(optimizations_applied) - 5}")

            # Выводим рекомендации для ручной оптимизации
            code_recommendations = report.get("code_recommendations", [])
            if code_recommendations:
                remaining_recs = len(code_recommendations)
                print(f"\n🔍 Осталось {remaining_recs} рекомендаций для ручной оптимизации")
                print("   Запустите split_large_functions.py для подробного анализа больших функций")
        except:
            pass

    print("\n🎉 Процесс оптимизации проекта завершен!")

if __name__ == "__main__":
    optimize_project()