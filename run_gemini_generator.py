
import sys
import os
from history_db_generator.generator import generate_database, ensure_directories
from gemini_api_keys import GEMINI_API_KEYS

if __name__ == "__main__":
    print("=== Запуск генератора базы данных с использованием Gemini API ===")
    
    # Создаем необходимые директории
    ensure_directories()
    
    # Проверяем наличие API ключей
    if not GEMINI_API_KEYS or len(GEMINI_API_KEYS) == 0:
        print("ОШИБКА: API ключи для Gemini не найдены в файле gemini_api_keys.py")
        print("Пожалуйста, добавьте API ключи в файл gemini_api_keys.py")
        sys.exit(1)
    
    # Запускаем генерацию
    try:
        print(f"Используется {len(GEMINI_API_KEYS)} API ключей Gemini")
        database = generate_database()
        print(f"Генерация базы данных завершена успешно. Всего событий: {len(database['events'])}")
    except Exception as e:
        print(f"Произошла ошибка при генерации базы данных: {e}")
        sys.exit(1)
