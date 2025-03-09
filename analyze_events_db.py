
import json
import collections
from pprint import pprint

def analyze_history_database(file_path="historical_events.json"):
    """
    Анализирует базу данных исторических событий и выводит подробную статистику.
    
    Args:
        file_path (str): Путь к файлу с базой данных исторических событий
    """
    try:
        # Загрузка данных из файла
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Извлечение событий из данных
        events = data.get('events', [])
        categories = data.get('categories', [])
        
        # Подсчет общего количества событий
        total_events = len(events)
        
        # Подсчет событий по различным критериям
        topics = set()
        topics_with_count = collections.defaultdict(int)
        categories_count = collections.defaultdict(int)
        centuries = collections.defaultdict(int)
        
        for event in events:
            # Подсчет тем
            if 'topic' in event:
                topics.add(event['topic'])
                topics_with_count[event['topic']] += 1
            
            # Подсчет категорий
            if 'category' in event:
                categories_count[event['category']] += 1
            
            # Подсчет событий по векам
            if 'date' in event and event['date']:
                try:
                    # Извлекаем год из даты (разные форматы)
                    year = None
                    if '-' in event['date']:
                        # Формат типа "1812-09-07"
                        year = int(event['date'].split('-')[0])
                    else:
                        # Просто год "1812"
                        year = int(event['date'])
                    
                    # Определяем век
                    century = (year // 100) + 1
                    centuries[f"{century} век"] += 1
                except (ValueError, IndexError):
                    # Ошибка при парсинге даты
                    centuries["Неизвестный век"] += 1
        
        # Вывод статистики
        print("\n===== СТАТИСТИКА БАЗЫ ДАННЫХ ИСТОРИЧЕСКИХ СОБЫТИЙ =====\n")
        
        print(f"Общее количество событий: {total_events}")
        print(f"Количество уникальных тем: {len(topics)}")
        print(f"Количество категорий: {len(categories)}")
        
        print("\n----- Топ-5 тем по количеству событий -----")
        for topic, count in sorted(topics_with_count.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  • {topic}: {count} событий")
        
        print("\n----- Распределение событий по категориям -----")
        for category, count in sorted(categories_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  • {category}: {count} событий ({count/total_events*100:.1f}%)")
        
        print("\n----- Распределение событий по векам -----")
        for century, count in sorted(centuries.items(), key=lambda x: int(x[0].split()[0]) if x[0].split()[0].isdigit() else 0):
            print(f"  • {century}: {count} событий ({count/total_events*100:.1f}%)")
        
        # Список всех тем
        print("\n----- Полный список тем -----")
        for i, topic in enumerate(sorted(topics), 1):
            print(f"  {i}. {topic}")
        
        return {
            "total_events": total_events,
            "total_topics": len(topics),
            "topics_list": sorted(topics),
            "categories": dict(categories_count)
        }
        
    except FileNotFoundError:
        print(f"Ошибка: Файл {file_path} не найден")
        return None
    except json.JSONDecodeError:
        print(f"Ошибка: Невозможно прочитать JSON из файла {file_path}")
        return None
    except Exception as e:
        print(f"Произошла ошибка при анализе базы данных: {e}")
        return None

if __name__ == "__main__":
    print("Анализируем базу данных исторических событий...")
    analyze_history_database()
