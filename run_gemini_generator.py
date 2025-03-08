
import sys
import os
from history_db_generator.generator import generate_database, ensure_directories
from dotenv import load_dotenv

if __name__ == "__main__":
    print("=== Запуск генератора базы данных с использованием Gemini API ===")
    
    # Загружаем переменные окружения для доступа к API ключу
    load_dotenv()
    
    # Проверяем наличие API ключа
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("ОШИБКА: API ключ для Gemini не найден в файле .env")
        print("Пожалуйста, добавьте строку GEMINI_API_KEY=ваш_ключ в файл .env")
        sys.exit(1)
    
    # Создаем необходимые директории
    ensure_directories()
    
    # Запускаем генерацию
    try:
        print(f"Используется API ключ: {gemini_api_key[:5]}...{gemini_api_key[-5:]}")
        database = generate_database()
        print(f"Генерация базы данных успешно завершена! Всего событий: {len(database['events'])}")
    except Exception as e:
        print(f"Ошибка при генерации базы данных: {e}")
        import traceback
        traceback.print_exc()
