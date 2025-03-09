
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime

def analyze_historical_events_db(file_path="historical_events.json"):
    """
    Анализирует базу данных исторических событий и выводит подробную статистику.
    
    Args:
        file_path (str): Путь к файлу с базой данных исторических событий.
    
    Returns:
        dict: Словарь со статистикой базы данных.
    """
    print("Анализируем базу данных исторических событий...")
    
    # Проверка существования файла
    if not os.path.exists(file_path):
        print(f"Ошибка: Файл {file_path} не найден.")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            events = json.load(file)
    except json.JSONDecodeError:
        print(f"Ошибка: Файл {file_path} содержит некорректный JSON.")
        return None
    except Exception as e:
        print(f"Ошибка при чтении файла: {str(e)}")
        return None
    
    # Количество событий
    event_count = len(events)
    if event_count == 0:
        print("База данных пуста. Нет событий для анализа.")
        return {
            "event_count": 0,
            "theme_count": 0,
            "category_count": 0
        }
    
    # Извлечение тем и категорий
    themes = []
    categories = []
    events_by_century = defaultdict(list)
    events_by_decade = defaultdict(list)
    events_by_category = defaultdict(list)
    events_by_theme = defaultdict(list)
    
    for event in events:
        # Извлечение темы
        if "theme" in event and event["theme"]:
            themes.append(event["theme"])
            events_by_theme[event["theme"]].append(event)
        
        # Извлечение категории
        if "category" in event and event["category"]:
            categories.append(event["category"])
            events_by_category[event["category"]].append(event)
        
        # Определение века и десятилетия по дате
        if "date" in event and event["date"]:
            century, decade = extract_time_period(event["date"])
            if century:
                events_by_century[century].append(event)
            if decade:
                events_by_decade[decade].append(event)
    
    # Подсчет уникальных тем и категорий
    unique_themes = set(themes)
    unique_categories = set(categories)
    
    # Топ тем по количеству событий
    theme_counts = Counter(themes)
    top_themes = theme_counts.most_common(5)
    
    # Подсчет процентного соотношения событий по категориям
    category_counts = Counter(categories)
    category_percentages = {
        category: (count, count / event_count * 100) 
        for category, count in category_counts.items()
    }
    
    # Подсчет распределения событий по векам
    century_counts = {century: len(events) for century, events in events_by_century.items()}
    century_percentages = {
        century: (count, count / event_count * 100) 
        for century, count in century_counts.items()
    }
    
    # Формирование статистики
    stats = {
        "event_count": event_count,
        "theme_count": len(unique_themes),
        "category_count": len(unique_categories),
        "top_themes": top_themes,
        "categories": category_percentages,
        "centuries": century_percentages,
        "themes_list": sorted(list(unique_themes)),
        "events_by_theme": {theme: len(events) for theme, events in events_by_theme.items()},
        "events_by_category": {category: len(events) for category, events in events_by_category.items()},
        "events_by_century": {century: len(events) for century, events in events_by_century.items()},
        "events_by_decade": {decade: len(events) for decade, events in events_by_decade.items()}
    }
    
    # Вывод статистики
    print_statistics(stats)
    
    return stats

def extract_time_period(date_str):
    """
    Извлекает век и десятилетие из строки с датой события.
    
    Args:
        date_str (str): Строка с датой события.
    
    Returns:
        tuple: (век, десятилетие) или (None, None) если невозможно определить.
    """
    # Попытка найти год в строке даты
    year_match = re.search(r'\b(\d{3,4})\b', date_str)
    
    if year_match:
        year = int(year_match.group(1))
        century = (year // 100) + 1
        decade = (year // 10) * 10
        return f"{century} век", f"{decade}-е"
    
    # Проверка на прямое указание века
    century_match = re.search(r'(\d+)\s*век', date_str, re.IGNORECASE)
    if century_match:
        century = int(century_match.group(1))
        return f"{century} век", None
    
    return None, None

def print_statistics(stats):
    """
    Выводит статистику базы данных исторических событий.
    
    Args:
        stats (dict): Словарь со статистикой базы данных.
    """
    print("\n===== СТАТИСТИКА БАЗЫ ДАННЫХ ИСТОРИЧЕСКИХ СОБЫТИЙ =====\n")
    
    print(f"Общее количество событий: {stats['event_count']}")
    print(f"Количество уникальных тем: {stats['theme_count']}")
    print(f"Количество категорий: {stats['category_count']}")
    
    # Вывод топ-5 тем
    print("\n----- Топ-5 тем по количеству событий -----")
    if stats["top_themes"]:
        for theme, count in stats["top_themes"]:
            print(f"  • {theme}: {count} событий ({count/stats['event_count']*100:.1f}%)")
    else:
        print("  Темы не определены в базе данных")
    
    # Вывод распределения по категориям
    print("\n----- Распределение событий по категориям -----")
    if stats["categories"]:
        for category, (count, percentage) in sorted(
            stats["categories"].items(), 
            key=lambda x: x[1][0], 
            reverse=True
        ):
            print(f"  • {category}: {count} событий ({percentage:.1f}%)")
    else:
        print("  Категории не определены в базе данных")
    
    # Вывод распределения по векам
    print("\n----- Распределение событий по векам -----")
    if stats["centuries"]:
        for century, (count, percentage) in sorted(
            stats["centuries"].items(), 
            key=lambda x: x[0] if isinstance(x[0], int) else 0
        ):
            print(f"  • {century}: {count} событий ({percentage:.1f}%)")
    else:
        print("  Не удалось определить век для событий")
    
    # Вывод полного списка тем
    print("\n----- Полный список тем -----")
    if stats["themes_list"]:
        for theme in stats["themes_list"]:
            events_count = stats["events_by_theme"].get(theme, 0)
            print(f"  • {theme}: {events_count} событий")
    else:
        print("  Темы не определены в базе данных")
    
    print("\n=== Анализ завершен ===")

if __name__ == "__main__":
    analyze_historical_events_db()
