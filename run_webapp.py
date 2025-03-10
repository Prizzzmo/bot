
"""
Скрипт для запуска веб-сервера с картой исторических событий
"""

import os
import sys
from webapp.server import run_server

if __name__ == "__main__":
    print("Запуск веб-сервера с картой исторических событий...")
    # Запускаем веб-сервер на порту 8080
    run_server(host='0.0.0.0', port=8080)
