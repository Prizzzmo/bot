
"""
Скрипт для автоматической оптимизации кода
Выполняет рефакторинг файлов Python в соответствии с рекомендациями из optimization_report.json
"""

import os
import json
import re
import ast
import astor

def load_optimization_report():
    """Загружает отчет об оптимизации из файла"""
    try:
        with open('optimization_report.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Ошибка при загрузке отчета оптимизации: {e}")
        return None

def optimize_imports(file_path):
    """Оптимизирует импорты в файле, заменяя 'import *' на конкретные импорты"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ищем импорты вида "from X import *"
        import_pattern = re.compile(r'from\s+(\S+)\s+import\s+\*')
        matches = import_pattern.findall(content)
        
        if not matches:
            return False, "Нет импортов * для оптимизации"
        
        # Для каждого импорта пытаемся определить конкретные импортируемые имена
        for module_name in matches:
            try:
                # Пытаемся импортировать модуль, чтобы получить список имен
                module = __import__(module_name, fromlist=['*'])
                names = dir(module)
                
                # Фильтруем встроенные имена и имена начинающиеся с "_"
                names = [name for name in names if not name.startswith('_') and not name == name.upper()]
                
                # Создаем новый импорт
                new_import = f"from {module_name} import {', '.join(names[:10])}"
                if len(names) > 10:
                    new_import += f"  # и еще {len(names) - 10} имен"
                
                # Заменяем импорт в файле
                content = content.replace(f"from {module_name} import *", new_import)
            except:
                continue
        
        # Записываем обновленный контент
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True, f"Оптимизированы импорты * в {file_path}"
    except Exception as e:
        return False, f"Ошибка при оптимизации импортов в {file_path}: {e}"

def optimize_loops(file_path):
    """Заменяет циклы с append на списковые включения"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ищем паттерны циклов с append
        loop_pattern = re.compile(r'(\w+)\s*=\s*\[\]\s*(?:\n|.)*?for\s+(\w+)\s+in\s+(.+?):\s*(?:\n|.)*?\1\.append\((.+?)\)')
        matches = loop_pattern.findall(content)
        
        if not matches:
            return False, "Нет циклов с append для оптимизации"
        
        # Для каждого найденного цикла создаем списковое включение
        for result_var, item_var, iterable, append_expr in matches:
            original_code = f"{result_var} = []\nfor {item_var} in {iterable}:\n    {result_var}.append({append_expr})"
            list_comprehension = f"{result_var} = [{append_expr} for {item_var} in {iterable}]"
            
            content = content.replace(original_code, list_comprehension)
        
        # Записываем обновленный контент
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True, f"Заменены циклы на списковые включения в {file_path}"
    except Exception as e:
        return False, f"Ошибка при оптимизации циклов в {file_path}: {e}"

def add_caching(file_path):
    """Добавляет базовое кэширование для функций в файле"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Проверяем, есть ли уже кэширование в файле
        if "cache" in content.lower() or "cached" in content.lower():
            return False, "Кэширование уже присутствует в файле"
        
        # Добавляем импорт для функции lru_cache
        if "from functools import lru_cache" not in content:
            content = "from functools import lru_cache\n" + content
        
        # Парсим AST для анализа функций
        tree = ast.parse(content)
        
        # Ищем функции, которые можно кэшировать
        functions_to_cache = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Проверяем, не является ли функция методом класса
                if not any(isinstance(parent, ast.ClassDef) for parent in ast.iter_child_nodes(node.parent)):
                    # Только если функция принимает аргументы (чтобы кэширование имело смысл)
                    if node.args.args:
                        functions_to_cache.append(node.name)
        
        # Добавляем декоратор @lru_cache к функциям
        for func_name in functions_to_cache:
            func_pattern = re.compile(f"def {func_name}\(")
            content = func_pattern.sub(f"@lru_cache(maxsize=128)\ndef {func_name}(", content)
        
        # Записываем обновленный контент
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True, f"Добавлено кэширование для {len(functions_to_cache)} функций в {file_path}"
    except Exception as e:
        return False, f"Ошибка при добавлении кэширования в {file_path}: {e}"

def main():
    """Основная функция для запуска оптимизаций"""
    report = load_optimization_report()
    if not report:
        print("Не удалось загрузить отчет об оптимизации")
        return
    
    recommendations = report.get("code_recommendations", [])
    if not recommendations:
        print("В отчете нет рекомендаций для оптимизации")
        return
    
    # Группируем рекомендации по файлам и типам
    optimizations_by_file = {}
    for rec in recommendations:
        file_path = rec.get("file")
        rec_type = rec.get("type")
        
        if not file_path or not rec_type:
            continue
        
        if file_path not in optimizations_by_file:
            optimizations_by_file[file_path] = set()
        
        optimizations_by_file[file_path].add(rec_type)
    
    # Выполняем оптимизации для каждого файла
    results = []
    for file_path, optimization_types in optimizations_by_file.items():
        # Проверяем, существует ли файл
        if not os.path.exists(file_path):
            results.append(f"Файл {file_path} не найден")
            continue
            
        print(f"Оптимизация файла {file_path}...")
        
        # Применяем соответствующие оптимизации
        if "import_optimization" in optimization_types:
            success, message = optimize_imports(file_path)
            results.append(message)
        
        if "loop_optimization" in optimization_types:
            success, message = optimize_loops(file_path)
            results.append(message)
        
        if "missing_cache" in optimization_types:
            success, message = add_caching(file_path)
            results.append(message)
    
    # Выводим результаты
    print("\nРезультаты оптимизации:")
    for result in results:
        print(f"- {result}")

if __name__ == "__main__":
    main()
