
"""API клиент для работы с Gemini API"""

import json
import time
from typing import Dict, Any, Optional, List

import google.generativeai as genai

from src.base_client import BaseClient
from src.interfaces import ILogger, ICache

class APIClient(BaseClient):
    """
    Клиент для работы с Google Gemini API.
    Наследует базовую функциональность из BaseClient.
    """
    
    def __init__(self, api_key: str, cache: ICache, logger: ILogger):
        """
        Инициализация API клиента для Google Gemini.
        
        Args:
            api_key (str): API ключ для Google Gemini
            cache (ICache): Имплементация интерфейса кэширования
            logger (ILogger): Имплементация интерфейса логирования
        """
        super().__init__(api_key, cache, logger)
        self.model = None
        self.initialize_model()
        
    def initialize_model(self) -> None:
        """
        Инициализация модели Google Gemini.
        Устанавливает API ключ и настраивает модель.
        """
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.logger.info("Gemini API успешно инициализирован")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации Gemini API: {e}")
            raise
    
    def call_api(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1024, 
                use_cache: bool = True, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Выполняет запрос к API Gemini с оптимизированными настройками.
        
        Args:
            prompt (str): Текст запроса
            temperature (float): Параметр случайности генерации (0.0-1.0)
            max_tokens (int): Максимальное количество токенов ответа
            use_cache (bool): Использовать ли кэш для данного запроса
            system_prompt (str, optional): Системный промпт для настройки поведения модели
            
        Returns:
            Dict[str, Any]: Результат запроса
            
        Raises:
            Exception: При ошибке выполнения запроса к API
        """
        # Создаем ключ кэша на основе параметров запроса
        if use_cache:
            import hashlib
            cache_key_data = f"{prompt}:{temperature}:{max_tokens}:{system_prompt}"
            cache_key = hashlib.md5(cache_key_data.encode()).hexdigest()
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.logger.debug(f"Получен ответ из кэша для промпта: {prompt[:50]}...")
                return cached_result
        
        # Выполняем запрос с механизмом повторных попыток
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                self.logger.debug(f"Отправка запроса к Gemini API: {prompt[:50]}...")
                
                # Настройка параметров генерации
                generation_config = {
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                    "top_p": 0.95,
                    "top_k": 40,
                }
                
                # Формирование промпта с системной инструкцией если она предоставлена
                if system_prompt:
                    chat = self.model.start_chat(history=[
                        {"role": "user", "parts": [system_prompt]},
                        {"role": "model", "parts": ["Понял инструкции. Готов к работе."]}
                    ])
                    response = chat.send_message(prompt, generation_config=generation_config)
                else:
                    response = self.model.generate_content(prompt, generation_config=generation_config)
                
                elapsed_time = time.time() - start_time
                self.logger.debug(f"Ответ получен за {elapsed_time:.2f}с")
                
                # Обработка ответа
                result = {
                    "text": response.text,
                    "status": "success",
                    "model": "gemini-pro",
                    "elapsed_time": elapsed_time
                }
                
                # Сохраняем в кэш
                if use_cache:
                    self.cache.set(cache_key, result, ttl=24*60*60)  # TTL 24 часа
                
                return result
                
            except Exception as e:
                self.logger.warning(f"Ошибка запроса к Gemini API (попытка {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Экспоненциальная задержка
                else:
                    self.logger.error(f"Не удалось получить ответ от Gemini API после {max_retries} попыток: {e}")
                    raise
    
    def validate_historical_topic(self, topic: str) -> bool:
        """
        Проверяет, является ли тема исторической.
        
        Args:
            topic (str): Тема для проверки
            
        Returns:
            bool: True если тема историческая, False в противном случае
        """
        prompt = f"""
        Определи, относится ли следующий запрос к истории России:
        
        "{topic}"
        
        Ответь только "да" или "нет".
        """
        
        try:
            result = self.call_api(
                prompt=prompt,
                temperature=0.1,
                max_tokens=10,
                use_cache=True
            )
            
            response_text = result.get("text", "").strip().lower()
            is_historical = "да" in response_text
            
            self.logger.debug(f"Проверка темы '{topic}': {is_historical}")
            return is_historical
            
        except Exception as e:
            self.logger.error(f"Ошибка при проверке исторической темы: {e}")
            # В случае ошибки считаем, что тема может быть исторической
            return True
    
    def get_historical_info(self, topic: str) -> Dict[str, Any]:
        """
        Получает информацию по исторической теме.
        
        Args:
            topic (str): Историческая тема
            
        Returns:
            Dict[str, Any]: Информация по теме
        """
        prompt = f"""
        Предоставь точную историческую информацию о следующей теме из истории России: "{topic}".
        
        Структурируй ответ следующим образом:
        1. Хронологические рамки события или периода
        2. Ключевые участники и их роли
        3. Основные этапы и события
        4. Причины и предпосылки
        5. Последствия и историческое значение
        
        Используй только проверенные исторические факты. Избегай личных оценок и интерпретаций.
        Ответ должен быть информативным, но лаконичным (не более 800 слов).
        """
        
        try:
            result = self.call_api(
                prompt=prompt,
                temperature=0.2,
                max_tokens=2048,
                use_cache=True
            )
            
            return {
                "status": "success",
                "topic": topic,
                "content": result.get("text", ""),
                "source": "gemini-pro"
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении исторической информации: {e}")
            return {
                "status": "error",
                "topic": topic,
                "content": "К сожалению, произошла ошибка при получении информации. Пожалуйста, попробуйте еще раз или выберите другую тему.",
                "error": str(e)
            }
    
    def generate_historical_test(self, topic: str) -> Dict[str, Any]:
        """
        Генерирует тест по исторической теме.
        
        Args:
            topic (str): Историческая тема
            
        Returns:
            Dict[str, Any]: Тест по исторической теме
        """
        prompt = f"""
        Создай тест по следующей теме из истории России: "{topic}".
        
        Структура ответа должна быть в следующем формате JSON:
        {{
            "title": "Название теста",
            "questions": [
                {{
                    "text": "Текст вопроса 1",
                    "options": ["Вариант А", "Вариант Б", "Вариант В", "Вариант Г"],
                    "correct_answer": 0,
                    "explanation": "Объяснение правильного ответа"
                }},
                ...еще 4 вопроса по такой же структуре...
            ]
        }}
        
        Создай ровно 5 вопросов. Индекс правильного ответа должен быть числом от 0 до 3.
        Вопросы должны быть разнообразными по сложности и охватывать разные аспекты темы.
        """
        
        try:
            result = self.call_api(
                prompt=prompt,
                temperature=0.7,  # Увеличиваем разнообразие для тестов
                max_tokens=2048,
                use_cache=True
            )
            
            # Извлекаем JSON из ответа
            import re
            json_str = re.search(r'\{.*\}', result.get("text", ""), re.DOTALL)
            
            if not json_str:
                raise ValueError("Не удалось найти JSON в ответе API")
                
            test_data = json.loads(json_str.group(0))
            return {
                "status": "success",
                "topic": topic,
                "test": test_data
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при генерации теста: {e}")
            return {
                "status": "error",
                "topic": topic,
                "content": "К сожалению, произошла ошибка при генерации теста. Пожалуйста, попробуйте еще раз или выберите другую тему.",
                "error": str(e)
            }
