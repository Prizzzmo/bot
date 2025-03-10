
#!/usr/bin/env python3
import os
import sys
import subprocess

def main():
    """
    Запускает веб-приложение для интерактивной карты истории
    """
    print("Запуск веб-приложения для интерактивной карты...")
    
    # Проверка наличия директории webapp
    if not os.path.exists('webapp'):
        print("Ошибка: директория 'webapp' не найдена!")
        return 1
        
    # Проверка наличия основных файлов
    required_files = ['index.html', 'styles.css', 'app.js', 'server.py']
    for file in required_files:
        if not os.path.exists(os.path.join('webapp', file)):
            print(f"Ошибка: файл '{file}' не найден в директории 'webapp'!")
            return 1
    
    # Проверка базы данных с историческими событиями
    db_path = "history_db_generator/russian_history_database.json"
    if not os.path.exists(db_path):
        print(f"Предупреждение: файл базы данных '{db_path}' не найден!")
        print("Приложение запустится, но данные событий будут отсутствовать.")
    
    # Переходим в директорию webapp и запускаем сервер
    os.chdir('webapp')
    try:
        # Запускаем Flask сервер
        subprocess.run([sys.executable, 'server.py'], check=True)
    except KeyboardInterrupt:
        print("\nВеб-приложение остановлено.")
    except Exception as e:
        print(f"Ошибка при запуске веб-приложения: {e}")
        return 1
    finally:
        # Возвращаемся в исходную директорию
        os.chdir('..')
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
