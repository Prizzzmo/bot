
import requests
import json

def check_lepton_api(api_key):
    """
    Проверяет работоспособность Lepton API с использованием предоставленного ключа.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Эндпоинт API Lepton
    url = "https://api.lepton.ai/api/v1/completions"
    
    # Тестовый запрос к API
    payload = {
        "model": "meta-llama/Llama-3-8b-chat-hf",  # Используем Llama-3 модель
        "prompt": "Расскажи кратко, что такое Lepton AI?",
        "max_tokens": 150,
        "temperature": 0.7
    }
    
    print(f"Проверка API Lepton с ключом: {api_key[:5]}...{api_key[-5:]}")
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ API ключ работает!")
            print(f"Статус код: {response.status_code}")
            print("\nТекст ответа:")
            if "choices" in result and len(result["choices"]) > 0:
                print(result["choices"][0]["text"].strip())
            else:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"\n❌ Ошибка API: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"\n❌ Исключение при обращении к API: {e}")
        return False

if __name__ == "__main__":
    # Проверяем API ключ Lepton
    api_key = "DHtXHKngQUq2bpI6YoiKpHb3oe9uWYeD"
    check_lepton_api(api_key)
