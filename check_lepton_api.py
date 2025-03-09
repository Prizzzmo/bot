
#!/usr/bin/env python3
"""
Скрипт для проверки работоспособности API ключей (Gemini, Lepton)
Проверяет доступность API и валидность ключей
"""

import os
import sys
import json
import requests
import time
from dotenv import load_dotenv
import traceback

# Пытаемся импортировать Google API клиент
try:
    import google.generativeai as genai
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    print("Warning: Google Generative AI package not installed. Run 'pip install google-generativeai'")

def load_gemini_keys():
    """Загружает API ключи Gemini из файла или переменных окружения"""
    keys = []
    
    # Пытаемся загрузить ключи из файла
    try:
        from gemini_api_keys import GEMINI_API_KEYS
        if isinstance(GEMINI_API_KEYS, list) and GEMINI_API_KEYS:
            keys.extend(GEMINI_API_KEYS)
            print(f"Загружено {len(GEMINI_API_KEYS)} API ключей из файла gemini_api_keys.py")
    except ImportError:
        print("Файл gemini_api_keys.py не найден")
    except Exception as e:
        print(f"Ошибка при загрузке ключей из файла: {e}")
    
    # Загружаем переменные окружения
    load_dotenv()
    
    # Пытаемся получить ключ из переменной окружения
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key and env_key not in keys:
        keys.append(env_key)
        print("Загружен API ключ из переменной окружения GEMINI_API_KEY")
    
    return keys

def check_gemini_api(api_keys):
    """
    Проверяет работоспособность API ключей Gemini.
    
    Args:
        api_keys (list): Список API ключей для проверки
        
    Returns:
        dict: Словарь с результатами проверки {key: {"status": bool, "message": str}}
    """
    if not GOOGLE_API_AVAILABLE:
        return {key: {"status": False, "message": "Google Generative AI package not installed"} for key in api_keys}
    
    results = {}
    
    for i, key in enumerate(api_keys):
        key_id = f"API ключ {i+1}"
        print(f"\nПроверка {key_id}...")
        
        try:
            # Настраиваем клиент Gemini
            genai.configure(api_key=key)
            
            # Создаем модель и отправляем тестовый запрос
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content("Привет! Напиши короткое приветствие на русском языке.")
            
            # Проверяем ответ
            if response and hasattr(response, 'text') and response.text:
                results[key_id] = {
                    "status": True, 
                    "message": f"API успешно работает. Ответ: {response.text[:50]}..."
                }
                print(f"✅ {key_id}: API работает корректно")
            else:
                results[key_id] = {
                    "status": False, 
                    "message": "Получен пустой ответ от API"
                }
                print(f"❌ {key_id}: Получен пустой ответ")
        except Exception as e:
            error_message = str(e)
            results[key_id] = {
                "status": False, 
                "message": f"Ошибка: {error_message}"
            }
            print(f"❌ {key_id}: {error_message}")
            traceback.print_exc()
        
        # Небольшая пауза между запросами
        if i < len(api_keys) - 1:
            time.sleep(1)
    
    return results

def main():
    """Основная функция проверки API ключей"""
    print("=== Проверка API ключей ===\n")
    
    # Загружаем и проверяем ключи Gemini
    gemini_keys = load_gemini_keys()
    
    if not gemini_keys:
        print("❌ Не найдено ни одного API ключа Gemini")
        print("Пожалуйста, добавьте API ключи в файл gemini_api_keys.py или в переменную окружения GEMINI_API_KEY")
        return
    
    # Проверяем ключи Gemini
    print(f"\n=== Проверка {len(gemini_keys)} ключей Gemini API ===")
    gemini_results = check_gemini_api(gemini_keys)
    
    # Выводим общую статистику
    working_keys = sum(1 for result in gemini_results.values() if result["status"])
    
    print("\n=== Итоги проверки ===")
    print(f"Gemini API: {working_keys} из {len(gemini_keys)} ключей работает")
    
    # Детальная информация о каждом ключе
    print("\n=== Подробные результаты ===")
    for key_id, result in gemini_results.items():
        status = "✅ Работает" if result["status"] else "❌ Не работает"
        print(f"{key_id}: {status}")
        print(f"  Сообщение: {result['message']}")
    
    # Вывод рекомендаций
    if working_keys == 0:
        print("\n❌ ВНИМАНИЕ: Ни один API ключ не работает!")
        print("Возможные причины:")
        print("1. Ключи недействительны или истекли")
        print("2. Проблемы с подключением к API")
        print("3. Превышены лимиты запросов")
        print("\nРекомендации:")
        print("1. Проверьте правильность API ключей")
        print("2. Проверьте подключение к интернету")
        print("3. Получите новые API ключи")
    elif working_keys < len(gemini_keys):
        print("\n⚠️ Некоторые ключи не работают. Рекомендуется обновить недействительные ключи.")
    else:
        print("\n✅ Все API ключи работают корректно!")

if __name__ == "__main__":
    main()
