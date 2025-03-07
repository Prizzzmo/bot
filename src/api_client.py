import requests
import time
import json
import google.generativeai as genai
from typing import Dict, Any, Optional

class APIClient:
    """Клиент для работы с Gemini API"""

    def __init__(self, api_key, api_cache, logger):
        self.api_key = api_key
        self.cache = api_cache
        self.logger = logger

        # Настраиваем API Gemini
        genai.configure(api_key=self.api_key)

        # Получаем доступные модели
        try:
            self.models = list(genai.list_models())
            self.logger.info(f"Доступно моделей Gemini: {len(self.models)}")

            # Выбираем модель для работы (gemini-pro)
            self.model = genai.GenerativeModel('gemini-pro')
            self.logger.info("Инициализирована модель gemini-pro")
        except Exception as e:
            self.logger.error(f"Ошибка при инициализации Gemini API: {e}")
            raise

    def generate_response(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1024, use_cache: bool = True) -> Optional[str]:
        """Генерирует ответ с помощью модели Gemini"""
        try:
            # Создаем ключ для кэша
            cache_key = f"{prompt}_{temperature}_{max_tokens}"

            # Проверяем кэш
            if use_cache:
                cached_response = self.cache.get(cache_key)
                if cached_response:
                    self.logger.info("Получен ответ из кэша")
                    return cached_response

            # Готовим запрос
            start_time = time.time()

            # Генерируем ответ
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                    "top_p": 0.95,
                    "top_k": 40
                }
            )

            # Получаем текст ответа
            if response and response.text:
                response_text = response.text

                # Добавляем в кэш
                if use_cache:
                    self.cache.set(cache_key, response_text)

                # Логируем время выполнения
                execution_time = time.time() - start_time
                self.logger.info(f"Получен ответ от API за {execution_time:.2f} сек")

                return response_text
            else:
                self.logger.warning("Получен пустой ответ от API")
                return None

        except Exception as e:
            self.logger.error(f"Ошибка при генерации ответа: {e}")
            return None

    def check_api_health(self) -> bool:
        """Проверяет доступность API"""
        try:
            # Отправляем простой запрос
            response = self.generate_response(
                "Привет", 
                temperature=0.1, 
                max_tokens=10,
                use_cache=False
            )

            return response is not None
        except Exception as e:
            self.logger.error(f"API недоступен: {e}")
            return False