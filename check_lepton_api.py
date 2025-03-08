
import json
import os
from leptonai.client import Client

def check_lepton_api(api_key):
    """
    Проверяет работоспособность Lepton API с использованием предоставленного ключа.
    Использует официальную библиотеку leptonai для более надежного соединения.
    """
    os.environ["LEPTON_API_TOKEN"] = api_key
    
    print(f"Проверка API Lepton с ключом: {api_key[:5]}...{api_key[-5:]}")
    try:
        # Создаем клиент Lepton
        client = Client(api_key=api_key)
        
        # Проверяем доступность API
        models = client.list_models()
        
        print("\n✅ API ключ работает!")
        print("\nДоступные модели:")
        for model in models:
            print(f" - {model}")
        
        # Тестовый запрос к модели
        prompt = "Расскажи кратко, что такое Lepton AI?"
        print(f"\nОтправка тестового запроса к модели: {models[0] if models else 'meta-llama/Llama-3-8b-chat-hf'}")
        
        response = client.completion(
            model=models[0] if models else "meta-llama/Llama-3-8b-chat-hf",
            prompt=prompt,
            max_tokens=150,
            temperature=0.7
        )
        
        print("\nТекст ответа:")
        if "choices" in response and len(response["choices"]) > 0:
            print(response["choices"][0]["text"].strip())
        else:
            print(json.dumps(response, indent=2, ensure_ascii=False))
        
        return True
        
    except Exception as e:
        print(f"\n❌ Исключение при обращении к API: {e}")
        return False

if __name__ == "__main__":
    # Проверяем API ключ Lepton
    api_key = "DHtXHKngQUq2bpI6YoiKpHb3oe9uWYeD"
    check_lepton_api(api_key)
