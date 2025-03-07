
import requests
import time
import telegram

class APIClient:
    """Класс для взаимодействия с API Gemini"""
    
    def __init__(self, api_key, api_cache, logger):
        self.api_key = api_key
        self.api_cache = api_cache
        self.logger = logger
        
    def ask_grok(self, prompt, max_tokens=1024, temp=0.7, use_cache=True):
        """
        Отправляет запрос к Google Gemini API и возвращает ответ с оптимизированным кэшированием.

        Args:
            prompt (str): Текст запроса
            max_tokens (int): Максимальное количество токенов в ответе
            temp (float): Температура генерации (0.0-1.0)
            use_cache (bool): Использовать ли кэширование

        Returns:
            str: Ответ от API или сообщение об ошибке
        """
        # Создаем более короткий уникальный ключ для кэша на основе хэша запроса
        if use_cache:
            cache_key = self.api_cache.generate_key(prompt, max_tokens, temp)

            # Проверяем кэш с улучшенной производительностью
            cached_response = self.api_cache.get(cache_key)
            if cached_response:
                self.logger.info("Использую кэшированный ответ")
                return cached_response

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temp,
                "maxOutputTokens": max_tokens
            }
        }

        try:
            self.logger.info(f"Отправка запроса к Gemini API: {prompt[:50]}...")

            # Оптимизируем запрос с таймаутом и пулингом соединений
            session = requests.Session()
            response = session.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            response_json = response.json()

            # Проверка наличия всех необходимых ключей в ответе
            if "candidates" not in response_json or not response_json["candidates"]:
                self.logger.warning(f"Ответ не содержит 'candidates': {response_json}")
                return "API вернул ответ без содержимого. Возможно, запрос был заблокирован фильтрами безопасности."

            candidate = response_json["candidates"][0]
            if "content" not in candidate:
                self.logger.warning(f"Ответ не содержит 'content': {candidate}")
                return "API вернул неверный формат ответа."

            content = candidate["content"]
            if "parts" not in content or not content["parts"]:
                self.logger.warning(f"Ответ не содержит 'parts': {content}")
                return "API вернул пустой ответ."

            result = content["parts"][0]["text"]
            self.logger.info(f"Получен ответ от API: {result[:50]}...")

            # Сохраняем результат в кэш с TTL в зависимости от типа запроса
            # Долгоживущий кэш для более общих запросов, короткий для специфичных
            if use_cache:
                ttl = 86400  # 24 часа по умолчанию
                if "тест" in prompt.lower():
                    ttl = 3600  # 1 час для тестов
                elif "беседа" in prompt.lower() or "разговор" in prompt.lower():
                    ttl = 1800  # 30 минут для бесед

                self.api_cache.set(cache_key, result, ttl=ttl)

            return result

        except requests.exceptions.RequestException as e:
            error_type = type(e).__name__
            error_msg = str(e)
            self.logger.error(f"{error_type}: {error_msg}")

            if isinstance(e, requests.exceptions.HTTPError) and hasattr(e, 'response'):
                self.logger.error(f"Статус код: {e.response.status_code}")
                self.logger.error(f"Ответ сервера: {e.response.text}")
                return f"Ошибка HTTP при запросе к Google Gemini ({e.response.status_code}): {error_msg}"

            error_messages = {
                "ConnectionError": "Ошибка соединения с API Google Gemini. Проверьте подключение к интернету.",
                "Timeout": "Превышено время ожидания ответа от API Google Gemini.",
                "JSONDecodeError": "Ошибка при обработке ответа от API Google Gemini.",
                "HTTPError": f"Ошибка HTTP при запросе к Google Gemini: {error_msg}"
            }

            return error_messages.get(error_type, f"Неизвестная ошибка при запросе к Google Gemini: {error_msg}")
