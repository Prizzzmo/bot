
#!/usr/bin/env python3
"""
Скрипт для анализа целостности проекта и поиска потенциальных ошибок.
"""

import os
import sys
import ast
import importlib
import pkgutil
import logging
import json
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProjectAnalyzer:
    """Анализатор целостности проекта"""
    
    def __init__(self):
        self.issues = []
        self.files_analyzed = 0
        self.error_count = 0
        self.warning_count = 0
        self.info_count = 0
        self.python_files = []
        self.json_files = []
    
    def log_issue(self, severity, message, file_path=None, line=None):
        """Логирует обнаруженную проблему"""
        issue = {
            "severity": severity,
            "message": message,
            "file": file_path,
            "line": line
        }
        self.issues.append(issue)
        
        if severity == "ERROR":
            self.error_count += 1
            logger.error(f"{message} ({file_path}:{line if line else 'N/A'})")
        elif severity == "WARNING":
            self.warning_count += 1
            logger.warning(f"{message} ({file_path}:{line if line else 'N/A'})")
        else:
            self.info_count += 1
            logger.info(f"{message} ({file_path}:{line if line else 'N/A'})")
    
    def find_project_files(self):
        """Находит все файлы проекта для анализа"""
        for root, _, files in os.walk("."):
            # Пропускаем директории .git, __pycache__, .venv и т.д.
            if any(part.startswith(('.', '__')) for part in root.split(os.sep) if part):
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                
                # Анализируем только файлы проекта
                if file.endswith('.py'):
                    self.python_files.append(file_path)
                elif file.endswith('.json'):
                    self.json_files.append(file_path)
        
        logger.info(f"Найдено {len(self.python_files)} Python файлов и {len(self.json_files)} JSON файлов для анализа")
    
    def analyze_json_files(self):
        """Анализирует JSON файлы на корректность синтаксиса"""
        for file_path in self.json_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                self.files_analyzed += 1
            except json.JSONDecodeError as e:
                self.log_issue("ERROR", f"Некорректный JSON синтаксис: {str(e)}", file_path, e.lineno)
            except Exception as e:
                self.log_issue("ERROR", f"Ошибка при анализе файла: {str(e)}", file_path)
    
    def analyze_python_syntax(self):
        """Анализирует синтаксис Python файлов"""
        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source = f.read()
                    ast.parse(source, filename=file_path)
                self.files_analyzed += 1
            except SyntaxError as e:
                self.log_issue("ERROR", f"Синтаксическая ошибка: {str(e)}", file_path, e.lineno)
            except Exception as e:
                self.log_issue("ERROR", f"Ошибка при анализе файла: {str(e)}", file_path)
    
    def check_imports(self):
        """Проверяет импорты на наличие недоступных модулей"""
        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source = f.read()
                
                tree = ast.parse(source, filename=file_path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            if not self._is_module_available(name.name):
                                self.log_issue("WARNING", f"Импорт недоступного модуля: {name.name}", file_path, node.lineno)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and not self._is_module_available(node.module):
                            self.log_issue("WARNING", f"Импорт из недоступного модуля: {node.module}", file_path, node.lineno)
            except Exception as e:
                # Уже обрабатывается в analyze_python_syntax
                pass
    
    def _is_module_available(self, module_name):
        """Проверяет доступность модуля"""
        # Игнорируем внутренние импорты проекта
        if module_name.startswith('src.') or module_name == 'src':
            return True
        
        try:
            # Пробуем импортировать модуль
            importlib.util.find_spec(module_name)
            return True
        except (ImportError, ValueError):
            # Пробуем проверить, является ли это локальным модулем проекта
            return any(f.endswith(f"{module_name.replace('.', os.sep)}.py") for f in self.python_files)
    
    def check_for_common_issues(self):
        """Проверяет наличие типичных проблем в коде"""
        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source = f.read()
                    lines = source.splitlines()
                
                # Проверка на TODO комментарии
                for i, line in enumerate(lines):
                    if "TODO" in line or "FIXME" in line:
                        self.log_issue("INFO", f"Найден TODO/FIXME комментарий: {line.strip()}", file_path, i+1)
                
                # Проверка на незакрытые ресурсы
                tree = ast.parse(source, filename=file_path)
                for node in ast.walk(tree):
                    # Проверка на использование open без контекстного менеджера
                    if isinstance(node, ast.Call) and hasattr(node, 'func') and hasattr(node.func, 'id') and node.func.id == 'open':
                        # Проверяем, находится ли вызов open внутри with
                        if not self._is_inside_with(node):
                            self.log_issue("WARNING", "Использование open() без контекстного менеджера with", file_path, node.lineno)
                            
            except Exception as e:
                # Пропускаем файлы с синтаксическими ошибками
                pass
    
    def _is_inside_with(self, node):
        """Проверяет, находится ли узел внутри with-блока"""
        parent = getattr(node, 'parent', None)
        while parent:
            if isinstance(parent, ast.With):
                return True
            parent = getattr(parent, 'parent', None)
        return False
    
    def check_cache_implementations(self):
        """Проверяет реализации кэша на наличие проблем"""
        cache_files = [f for f in self.python_files if os.path.basename(f) in ['api_cache.py', 'distributed_cache.py', 'text_cache_service.py']]
        
        for file_path in cache_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source = f.read()
                
                # Проверка на использование threading.Lock
                if "threading" in source and ("Lock()" in source or "RLock()" in source):
                    if "with self.lock" not in source:
                        self.log_issue("WARNING", "Найден Lock, но не все методы используют его через 'with self.lock'", file_path)
                
                # Проверка корректности очистки кэша
                if "_clean_expired_items" in source and "_save_cache" in source:
                    if "self._save_cache()" not in source.split("def _clean_expired_items")[1].split("def ")[0]:
                        self.log_issue("WARNING", "Метод _clean_expired_items может не сохранять изменения после очистки", file_path)
                
            except Exception as e:
                self.log_issue("ERROR", f"Ошибка при анализе реализации кэша: {str(e)}", file_path)
    
    def check_file_references(self):
        """Проверяет ссылки на файлы в коде"""
        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source = f.read()
                
                # Ищем строки с путями к файлам
                for i, line in enumerate(source.splitlines()):
                    if "open(" in line or "file_path" in line or "os.path.join" in line:
                        # Извлекаем строковые литералы
                        for string in self._extract_string_literals(line):
                            if "/" in string or "\\" in string:
                                if not os.path.exists(string) and not string.startswith(("http", "https", "{", "/")):
                                    self.log_issue("INFO", f"Возможная ссылка на несуществующий файл: {string}", file_path, i+1)
            except Exception as e:
                # Пропускаем файлы с ошибками
                pass
    
    def _extract_string_literals(self, line):
        """Извлекает строковые литералы из строки кода"""
        strings = []
        # Ищем строки в одинарных кавычках
        in_single_quotes = False
        in_double_quotes = False
        current_str = ""
        
        for char in line:
            if char == "'" and not in_double_quotes:
                if in_single_quotes:
                    strings.append(current_str)
                    current_str = ""
                in_single_quotes = not in_single_quotes
            elif char == '"' and not in_single_quotes:
                if in_double_quotes:
                    strings.append(current_str)
                    current_str = ""
                in_double_quotes = not in_double_quotes
            elif in_single_quotes or in_double_quotes:
                current_str += char
        
        return strings
    
    def run_analysis(self):
        """Запускает полный анализ проекта"""
        logger.info("Начинаем анализ проекта...")
        
        # Находим файлы для анализа
        self.find_project_files()
        
        # Проверяем синтаксис Python файлов
        logger.info("Проверка синтаксиса Python файлов...")
        self.analyze_python_syntax()
        
        # Проверяем корректность JSON файлов
        logger.info("Проверка корректности JSON файлов...")
        self.analyze_json_files()
        
        # Проверяем импорты
        logger.info("Проверка импортов...")
        self.check_imports()
        
        # Проверяем типичные проблемы
        logger.info("Поиск типичных проблем в коде...")
        self.check_for_common_issues()
        
        # Проверяем реализации кэша
        logger.info("Проверка реализаций кэша...")
        self.check_cache_implementations()
        
        # Проверяем ссылки на файлы
        logger.info("Проверка ссылок на файлы...")
        self.check_file_references()
        
        # Формируем отчет
        logger.info("Анализ завершен!")
        logger.info(f"Проанализировано файлов: {self.files_analyzed}")
        logger.info(f"Обнаружено ошибок: {self.error_count}")
        logger.info(f"Обнаружено предупреждений: {self.warning_count}")
        logger.info(f"Информационных сообщений: {self.info_count}")
        
        return {
            "files_analyzed": self.files_analyzed,
            "errors": self.error_count,
            "warnings": self.warning_count,
            "info": self.info_count,
            "issues": self.issues
        }
    
    def save_report(self, filename="project_analysis_report.json"):
        """Сохраняет отчет об анализе в файл"""
        report = {
            "files_analyzed": self.files_analyzed,
            "summary": {
                "errors": self.error_count,
                "warnings": self.warning_count,
                "info": self.info_count,
                "total_issues": len(self.issues)
            },
            "issues": sorted(self.issues, key=lambda x: (
                0 if x["severity"] == "ERROR" else (1 if x["severity"] == "WARNING" else 2),
                x["file"] or "",
                x["line"] or 0
            ))
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"Отчет об анализе сохранен в файл: {filename}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении отчета: {str(e)}")

if __name__ == "__main__":
    analyzer = ProjectAnalyzer()
    analyzer.run_analysis()
    analyzer.save_report()
