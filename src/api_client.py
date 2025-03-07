import requests
import time
import threading
import telegram
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src.base_client import BaseAPIClient

class APIClient(BaseAPIClient):
    """Класс для взаимодействия с API Gemini с оптимизацией пула соединений"""

    def __init__(self, api_key, api_cache, logger):
        self.api_key = api_key
        self.api_cache = api_cache
        self.logger = logger
        self.session = self._create_session()
        self.api_lock = threading.RLock()  # Блокировка для предотвращения лимитов API
        
    def _create_session(self):
        """Создает сессию с настроенными retry и пулингом соединений"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
            backoff_factor=0.5
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def send_request(self, prompt, **kwargs):
        """
        Отправляет запрос к API.
        
        Args:
            prompt (str): Текст запроса
            **kwargs: Дополнительные параметры запроса
            
        Returns:
            str: Ответ от API
        """
        return self.ask_grok(prompt, **kwargs)
        
    def ask_grok(self, prompt, temp=0.3, max_tokens=1024, use_cache=True, max_retries=3, retry_delay=2):
        """
        Отправляет запрос к Gemini API и возвращает ответ с оптимизированным пулингом соединений.

        Args:
            prompt (str): Запрос к API
            temp (float): Температура (от 0 до 1), влияет на случайность ответов
            max_tokens (int): Максимальное количество токенов в ответе
            use_cache (bool): Использовать ли кэширование
            max_retries (int): Максимальное количество повторных попыток при ошибке
            retry_delay (int): Задержка между повторными попытками в секундах

        Returns:
            str: Ответ от API
        """
        # Создаем более короткий уникальный ключ для кэша на основе хэша запроса
        if use_cache:
            cache_key = self.api_cache.generate_key(prompt, max_tokens, temp)

            # Проверяем кэш с улучшенной производительностью
            cached_response = self.api_cache.get(cache_key)
            if cached_response:
                return cached_response
        
        retries = 0
        while retries < max_retries:
            # Используем блокировку для ограничения параллельных запросов к API
            with self.api_lock:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
                    headers = {"Content-Type": "application/json"}
                    data = {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": temp,
                            "maxOutputTokens": max_tokens
                        }
                    }

                    self.logger.debug(f"Отправка запроса к Gemini API: {prompt[:30]}...")

                    # Используем общую сессию с пулом соединений
                    response = self.session.post(url, headers=headers, json=data, timeout=30)
                    response.raise_for_status()

                    response_json = response.json()

                    # Быстрая проверка структуры ответа
                    if "candidates" not in response_json or not response_json["candidates"]:
                        self.logger.warning(f"Ответ не содержит 'candidates'")
                        return "API вернул ответ без содержимого. Возможно, запрос был заблокирован."

                    text = response_json["candidates"][0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    
                    if not text:
                        self.logger.warning("Получен пустой ответ от API")
                        return "API вернул пустой ответ."

                    self.logger.debug(f"Получен ответ от API: {text[:30]}...")

                    # Сохраняем результат в кэш с оптимизированным TTL 
                    if use_cache:
                        ttl = 86400  # 24 часа по умолчанию
                        prompt_lower = prompt.lower()
                        if "тест" in prompt_lower:
                            ttl = 3600  # 1 час для тестов
                        elif "беседа" in prompt_lower or "разговор" in prompt_lower:
                            ttl = 1800  # 30 минут для бесед

                        self.api_cache.set(cache_key, text, ttl=ttl)

                    return text
                except requests.exceptions.RequestException as e:
                    retries += 1
                    if retries == max_retries:
                        error_type = type(e).__name__
                        error_msg = str(e)
                        self.logger.error(f"{error_type}: {error_msg}")

                        error_messages = {
                            "ConnectionError": "Ошибка соединения с API Google Gemini. Проверьте подключение к интернету.",
                            "Timeout": "Превышено время ожидания ответа от API Google Gemini.",
                            "JSONDecodeError": "Ошибка при обработке ответа от API Google Gemini.",
                            "HTTPError": f"Ошибка HTTP при запросе к Google Gemini"
                        }

                        return error_messages.get(error_type, f"Ошибка при запросе к Google Gemini")
                    else:
                        self.logger.warning(f"Ошибка при запросе к API Gemini. Попытка {retries}/{max_retries}...")
                        time.sleep(retry_delay)