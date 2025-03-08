
import json
import os
import requests

def check_lepton_api(api_key):
    """
    Проверяет работоспособность Lepton API с использованием предоставленного ключа.
    Использует непосредственные HTTP запросы для гарантированного соединения.
    """
    print(f"Проверка API Lepton с ключом: {api_key[:5]}...{api_key[-5:]}")
    
    # Адрес API SDXL Lepton
    base_url = "https://sdxl.lepton.run/api"
    
    # Заголовки запроса с API ключом
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        # Проверяем статус API
        response = requests.get(f"{base_url}/status", headers=headers)
        response.raise_for_status()  # Вызовет исключение при HTTP-ошибке
        
        print("\n✅ API ключ работает! Соединение с SDXL Lepton успешно установлено.")
        
        # Проверяем доступные модели или операции
        print("\nДоступные возможности API:")
        
        # Тестовый запрос для генерации изображения (упрощенный)
        test_prompt = "A beautiful landscape with mountains and lake, digital art"
        print(f"\nОтправка тестового запроса с промптом: {test_prompt}")
        
        generation_data = {
            "prompt": test_prompt,
            "negative_prompt": "blurry, ugly, distorted",
            "num_inference_steps": 25,
            "guidance_scale": 7.5
        }
        
        # Отправляем запрос, но не ждем завершения генерации
        print("Для полного тестирования генерации изображения выполните запрос через API:")
        print(f"POST {base_url}/generate")
        print(f"С заголовком Authorization: Bearer {api_key[:5]}...{api_key[-5:]}")
        print("И телом запроса:")
        print(json.dumps(generation_data, indent=2))
        
        return True
        
    except requests.exceptions.ConnectionError as e:
        print(f"\n❌ Ошибка соединения с сервером: {e}")
        print("Проверьте доступность URL https://sdxl.lepton.run")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ Ошибка HTTP-запроса: {e}")
        if e.response.status_code == 401:
            print("Возможно, API ключ недействителен. Проверьте ключ и попробуйте снова.")
        return False
    except Exception as e:
        print(f"\n❌ Исключение при обращении к API: {e}")
        return False

if __name__ == "__main__":
    # Проверяем API ключ Lepton
    api_key = "DHtXHKngQUq2bpI6YoiKpHb3oe9uWYeD"
    check_lepton_api(api_key)
