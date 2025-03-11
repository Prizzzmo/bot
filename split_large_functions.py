
"""
Скрипт для разделения больших функций на более мелкие
Анализирует Python файлы и предлагает разделить функции длиннее заданного порога
"""

import os
import ast
import re
import json
import astor

class FunctionAnalyzer(ast.NodeVisitor):
    """Анализатор функций для поиска больших функций"""
    
    def __init__(self, content, threshold=50):
        self.content = content
        self.threshold = threshold
        self.large_functions = []
        self.current_class = None
    
    def visit_ClassDef(self, node):
        """Обрабатывает определения классов"""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)  # Посещаем все дочерние узлы
        self.current_class = old_class
    
    def visit_FunctionDef(self, node):
        """Обрабатывает определения функций"""
        # Получаем начальную и конечную строки функции
        start_line = node.lineno
        end_line = self._get_function_end_line(node)
        
        # Подсчитываем фактическое количество строк кода
        lines_count = end_line - start_line + 1
        
        if lines_count > self.threshold:
            # Сохраняем информацию о большой функции
            function_info = {
                'name': node.name,
                'class': self.current_class,
                'start_line': start_line,
                'end_line': end_line,
                'lines_count': lines_count,
                'source': astor.to_source(node)
            }
            self.large_functions.append(function_info)
        
        self.generic_visit(node)  # Посещаем все дочерние узлы
    
    def _get_function_end_line(self, node):
        """Определяет номер последней строки функции"""
        # Находим последнюю строку в исходном коде
        content_lines = self.content.split('\n')
        indentation = self._get_indentation(content_lines[node.lineno - 1])
        
        # Ищем следующую строку с таким же или меньшим отступом
        for i in range(node.lineno, len(content_lines)):
            line = content_lines[i]
            if line.strip() and self._get_indentation(line) <= indentation:
                if i > node.lineno:  # Если нашли следующий блок
                    return i - 1
        
        # Если не нашли, возвращаем последнюю строку файла
        return len(content_lines)
    
    def _get_indentation(self, line):
        """Определяет уровень отступа строки"""
        return len(line) - len(line.lstrip())

def analyze_file(file_path, threshold=50):
    """Анализирует файл и возвращает большие функции"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Парсим код в AST
        tree = ast.parse(content)
        
        # Анализируем функции
        analyzer = FunctionAnalyzer(content, threshold)
        analyzer.visit(tree)
        
        return analyzer.large_functions
    except Exception as e:
        print(f"Ошибка при анализе файла {file_path}: {e}")
        return []

def suggest_function_split(function_info):
    """Предлагает разделение функции на более мелкие"""
    source = function_info['source']
    name = function_info['name']
    
    # Анализируем блоки в функции
    blocks = []
    lines = source.split('\n')
    
    # Ищем комментарии как разделители логических блоков
    current_block = []
    current_block_comment = None
    
    for line in lines:
        if line.strip().startswith('#') and len(line.strip()) > 2:
            # Если нашли комментарий и уже есть блок, добавляем его
            if current_block:
                blocks.append({
                    'lines': current_block,
                    'comment': current_block_comment
                })
                current_block = []
            current_block_comment = line.strip()[1:].strip()
        else:
            current_block.append(line)
    
    # Добавляем последний блок
    if current_block:
        blocks.append({
            'lines': current_block,
            'comment': current_block_comment
        })
    
    # Если есть только один блок или нет комментариев, используем другую стратегию
    if len(blocks) <= 1 or all(b['comment'] is None for b in blocks):
        # Простой подход: делим на части примерно равного размера
        lines = source.split('\n')
        block_size = min(20, len(lines) // 3)
        blocks = []
        
        for i in range(0, len(lines), block_size):
            block_lines = lines[i:i+block_size]
            blocks.append({
                'lines': block_lines,
                'comment': f"Part {i//block_size + 1}"
            })
    
    # Генерируем предложения по разделению
    suggestions = []
    
    for i, block in enumerate(blocks):
        if not block['lines']:
            continue
            
        # Создаем имя для новой функции
        if block['comment']:
            subname = '_'.join(re.findall(r'\w+', block['comment'].lower()))[:20]
            new_func_name = f"{name}_{subname}"
        else:
            new_func_name = f"{name}_part{i+1}"
        
        # Определяем параметры на основе используемых переменных
        # Это упрощенный подход, для реального кода потребуется более сложный анализ
        params = []
        returns = []
        
        suggestions.append({
            'original_name': name,
            'new_func_name': new_func_name,
            'params': params,
            'returns': returns,
            'body': '\n'.join(block['lines'])
        })
    
    return suggestions

def main():
    """Основная функция для запуска анализа функций"""
    try:
        # Загружаем отчет об оптимизации
        with open('optimization_report.json', 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        # Получаем рекомендации по большим функциям
        large_function_recs = [rec for rec in report.get("code_recommendations", []) 
                              if rec.get("type") == "large_functions"]
        
        if not large_function_recs:
            print("В отчете нет рекомендаций по большим функциям")
            return
        
        # Анализируем каждый файл с большими функциями
        for rec in large_function_recs:
            file_path = rec.get("file")
            if not file_path or not os.path.exists(file_path):
                print(f"Файл {file_path} не найден")
                continue
            
            print(f"\nАнализ файла {file_path}...")
            large_functions = analyze_file(file_path)
            
            if not large_functions:
                print(f"В файле {file_path} не найдено больших функций")
                continue
            
            print(f"Найдено {len(large_functions)} больших функций:")
            
            for func_info in large_functions:
                print(f"\n- {func_info['name']} ({func_info['lines_count']} строк)")
                
                # Получаем предложения по разделению
                suggestions = suggest_function_split(func_info)
                
                print(f"  Предлагаемое разделение на {len(suggestions)} функции:")
                for i, suggestion in enumerate(suggestions):
                    print(f"  {i+1}. {suggestion['new_func_name']}")
    
    except Exception as e:
        print(f"Ошибка при анализе больших функций: {e}")

if __name__ == "__main__":
    main()
