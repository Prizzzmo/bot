
import sys
import os
from history_db_generator.mistral_generator import generate_database, ensure_directories

if __name__ == "__main__":
    print("=== Запуск генератора базы данных с использованием Mistral AI ===")
    
    # Создаем необходимые директории
    ensure_directories()
    
    # Запускаем генерацию
    try:
        generate_database()
        print("Генерация базы данных успешно завершена!")
    except Exception as e:
        print(f"Ошибка при генерации базы данных: {e}")
        import traceback
        traceback.print_exc()
