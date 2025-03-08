
import os
import sys
import threading
import time

def run_bot():
    print("Запуск Telegram бота...")
    os.system("python main.py")

def run_webapp():
    print("Запуск веб-приложения с картой...")
    os.system("python run_webapp.py")

if __name__ == "__main__":
    # Запускаем веб-приложение в отдельном потоке
    webapp_thread = threading.Thread(target=run_webapp)
    webapp_thread.daemon = True  # Поток завершится вместе с основной программой
    webapp_thread.start()
    
    # Даем веб-приложению время на запуск
    print("Инициализация веб-приложения...")
    time.sleep(3)
    
    # Запускаем бота в основном потоке
    run_bot()
