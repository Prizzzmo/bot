
"""
Скрипт для генерации диаграммы классов проекта.
Требует установленного graphviz: pip install graphviz
"""

import os
import inspect
import importlib
import pkgutil
from graphviz import Digraph
import src

def get_all_classes_in_module(module):
    """Получает все классы из модуля и его подмодулей"""
    classes = {}
    
    # Получаем все классы из текущего модуля
    for name, obj in inspect.getmembers(module, inspect.isclass):
        # Фильтруем только классы, которые определены в нашем пакете
        if obj.__module__.startswith('src.'):
            classes[obj.__module__ + '.' + name] = obj
    
    # Рекурсивно ищем в подмодулях
    if hasattr(module, '__path__'):
        for _, name, is_pkg in pkgutil.iter_modules(module.__path__):
            full_name = module.__name__ + '.' + name
            try:
                submodule = importlib.import_module(full_name)
                classes.update(get_all_classes_in_module(submodule))
            except ImportError as e:
                print(f"Ошибка импорта модуля {full_name}: {e}")
    
    return classes

def generate_class_diagram():
    """Генерирует диаграмму классов проекта"""
    # Создаем директорию для документации, если её нет
    os.makedirs('docs', exist_ok=True)
    
    # Создаем новую диаграмму
    dot = Digraph(comment='Диаграмма классов проекта', format='png')
    dot.attr(rankdir='TB', size='11,11')  # Ориентация сверху вниз
    
    # Получаем все классы из пакета src
    classes = get_all_classes_in_module(src)
    
    # Добавляем узлы для классов
    for full_name, cls in classes.items():
        # Форматируем имя класса для отображения
        name = full_name.split('.')[-1]
        module = '.'.join(full_name.split('.')[:-1])
        
        # Получаем все методы класса
        methods = []
        for method_name, method in inspect.getmembers(cls, inspect.isfunction):
            if not method_name.startswith('_') or method_name == '__init__':
                # Получаем сигнатуру метода
                try:
                    sig = inspect.signature(method)
                    methods.append(f"{method_name}{sig}")
                except ValueError:
                    methods.append(method_name + '(...)')
        
        # Создаем HTML-подобное представление для узла
        label = f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0">\n'
        label += f'<TR><TD BGCOLOR="#E0E0E0"><B>{name}</B></TD></TR>\n'
        label += f'<TR><TD ALIGN="LEFT" BGCOLOR="#F0F0F0">{module}</TD></TR>\n'
        
        # Добавляем методы
        if methods:
            label += '<TR><TD ALIGN="LEFT">'
            label += '<BR/>'.join(methods[:5])  # Ограничиваем количество методов для читаемости
            if len(methods) > 5:
                label += '<BR/>...'
            label += '</TD></TR>'
        
        label += '</TABLE>>'
        
        # Устанавливаем цвет для разных типов классов
        fillcolor = "#FFFFFF"
        if name.endswith('Service'):
            fillcolor = "#E0FFE0"  # Light green for services
        elif name.endswith('Manager'):
            fillcolor = "#FFE0E0"  # Light red for managers
        elif name.endswith('Client'):
            fillcolor = "#E0E0FF"  # Light blue for clients
        elif name.startswith('I'):
            fillcolor = "#FFFFD0"  # Light yellow for interfaces
        
        dot.node(full_name, label=label, shape='none', fillcolor=fillcolor, style='filled')
    
    # Добавляем связи между классами
    for full_name, cls in classes.items():
        # Наследование
        for base in cls.__bases__:
            base_full_name = base.__module__ + '.' + base.__name__
            if base_full_name in classes:
                dot.edge(base_full_name, full_name, arrowhead='empty')
        
        # Ассоциации на основе полей
        try:
            init_sig = inspect.signature(cls.__init__)
            for param_name, param in init_sig.parameters.items():
                if param_name != 'self':
                    for other_name, other_cls in classes.items():
                        # Проверяем, содержит ли имя параметра имя другого класса (упрощенный подход)
                        other_short_name = other_name.split('.')[-1]
                        if other_short_name.lower() in param_name.lower():
                            dot.edge(full_name, other_name, arrowhead='vee', style='dashed')
        except (ValueError, TypeError):
            pass
    
    # Сохраняем и рендерим диаграмму
    dot.render('docs/class_diagram', cleanup=True)
    print("Диаграмма классов сгенерирована в docs/class_diagram.png")

if __name__ == "__main__":
    generate_class_diagram()
