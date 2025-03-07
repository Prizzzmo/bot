
"""
API клиент для работы с Google Gemini API.

Обеспечивает взаимодействие с моделью искусственного интеллекта Google Gemini Pro:
- Инициализация и настройка модели
- Выполнение запросов к API с различными параметрами
- Валидация исторических тем
- Получение исторической информации и генерация тестов
"""

import json
import time
from typing import Dict, Any, Optional, List

import google.generativeai as genai

from src.base_client import BaseClient
from src.interfaces import ILogger, ICache

class APIClient(BaseClient):
    """
    Клиент для работы с Google Gemini API.
    
    Обеспечивает взаимодействие с моделью Gemini Pro для:
    - Генерации исторического контента
    - Проверки релевантности запросов
    - Создания тестовых заданий
    """
    
    def __init__(self, api_key: str, cache: ICache, logger: ILogger):
        """
        Инициализация API клиента для Google Gemini.
        
        Args:
            api_key (str): API ключ для Google Gemini
            cache (ICache): Компонент для кэширования запросов
            logger (ILogger): Компонент для логирования операций
        """
        super().__init__(api_key, cache, logger)
        self.model = None
        self.initialize_model()
        
    def initialize_model(self) -> None:
        """
        Инициализация модели Google Gemini.
        
        Настраивает модель Gemini Pro, которая обеспечивает:
        - Продвинутое понимание запросов на естественном языке
        - Генерацию структурированных и информативных ответов
        - Проверку фактологической точности контента
        """
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            self.logger.info("Gemini API успешно инициализирован (модель: gemini-2.0-flash)")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации Gemini API: {e}")
            raise
    
    def call_api(self, prompt: str, temperature: float = 0.3, max_tokens: int = 1024, 
                use_cache: bool = True, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Выполняет запрос к API Gemini с оптимизированными настройками.
        
        Параметры запроса:
        - temperature: контролирует креативность/случайность ответов
          (низкие значения для фактов, высокие для творческих задач)
        - max_tokens: максимальная длина ответа
        - system_prompt: системный промпт для настройки поведения модели
        
        Args:
            prompt (str): Основной текст запроса
            temperature (float): Параметр случайности генерации (0.0-1.0)
            max_tokens (int): Максимальное количество токенов ответа
            use_cache (bool): Использовать ли кэш для данного запроса
            system_prompt (str, optional): Системный промпт для настройки поведения модели
            
        Returns:
            Dict[str, Any]: Результат запроса с текстом ответа и метаданными
            
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
                try:
                    if system_prompt:
                        # Для Gemini 2.0 используем обновленный метод формирования чата
                        chat = self.model.start_chat(history=[
                            {"role": "user", "parts": [system_prompt]},
                            {"role": "model", "parts": ["Понял инструкции. Готов к работе."]}
                        ])
                        response = chat.send_message(prompt, generation_config=generation_config)
                    else:
                        # Стандартный запрос к модели
                        response = self.model.generate_content(prompt, generation_config=generation_config)
                except AttributeError as ae:
                    # Обработка возможных изменений в API Gemini 2.0
                    self.logger.warning(f"Возникла ошибка атрибута при вызове API: {ae}. Пробуем альтернативный метод.")
                    # Альтернативный метод для новой версии API
                    response = self.model.generate_content(content=prompt, generation_config=generation_config)
                
                elapsed_time = time.time() - start_time
                self.logger.debug(f"Ответ получен за {elapsed_time:.2f}с")
                
                # Обработка ответа
                result = {
                    "text": response.text,
                    "status": "success",
                    "model": "gemini-2.0-flash",
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
        Проверяет, относится ли тема к истории России.
        
        Выполняет проверку с помощью специального запроса к модели Gemini
        с низкой температурой для максимальной точности определения.
        
        Args:
            topic (str): Тема для проверки
            
        Returns:
            bool: True если тема относится к истории России, False в противном случае
        """
        prompt = f"""
        Определи, относится ли следующий запрос к истории России:
        
        "{topic}"
        
        Ответь только "да" или "нет".
        """
        
        try:
            result = self.call_api(
                prompt=prompt,
                temperature=0.1,  # Низкая температура для определенности ответа
                max_tokens=10,     # Короткий ответ (да/нет)
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
        Получает структурированную информацию по исторической теме.
        
        Создает запрос к Gemini для получения подробной информации
        об историческом периоде или событии с акцентом на фактологическую точность.
        
        Args:
            topic (str): Историческая тема
            
        Returns:
            Dict[str, Any]: Структурированная информация по теме с разделами
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
                temperature=0.2,  # Низкая температура для фактической точности
                max_tokens=2048,   # Достаточно для подробного ответа
                use_cache=True
            )
            
            return {
                "status": "success",
                "topic": topic,
                "content": result.get("text", ""),
                "source": "gemini-2.0-flash"
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении исторической информации: {e}")
            return {
                "status": "error",
                "topic": topic,
                "content": "К сожалению, произошла ошибка при получении информации. Пожалуйста, попробуйте еще раз или выберите другую тему.",
                "error": str(e)
            }
    
    def ask_grok(self, prompt: str, use_cache: bool = True) -> str:
        """
        Упрощенный метод для отправки запроса к Gemini API и получения текстового ответа.
        Адаптирован для работы с Gemini 2.0 Flash.
        
        Args:
            prompt (str): Текст запроса для модели
            use_cache (bool): Использовать ли кэширование для этого запроса
            
        Returns:
            str: Текстовый ответ от модели
        """
        try:
            result = self.call_api(
                prompt=prompt, 
                temperature=0.3,
                max_tokens=1024,
                use_cache=use_cache
            )
            return result.get("text", "")
        except Exception as e:
            self.logger.error(f"Ошибка в методе ask_grok: {e}")
            # Попробуем запасной метод для Gemini 2.0
            try:
                self.logger.info("Пробуем альтернативный метод вызова API...")
                response = self.model.generate_content(content=prompt)
                return response.text
            except Exception as e2:
                self.logger.error(f"Вторая ошибка в методе ask_grok: {e2}")
                return f"Произошла ошибка при обработке запроса: {str(e)}. Повторная попытка также не удалась: {str(e2)}"
    
    def generate_historical_test(self, topic: str) -> Dict[str, Any]:
        """
        Генерирует тестовые задания по исторической теме.
        
        Создает структурированный тест с вопросами и вариантами ответов
        в простом текстовом формате для максимальной надежности.
        
        Args:
            topic (str): Историческая тема для генерации теста
            
        Returns:
            Dict[str, Any]: Тест по исторической теме
        """
        prompt = f"""
        Создай тест по теме "{topic}" из истории России.
        Тест должен содержать ровно 20 вопросов с 4 вариантами ответов для каждого.
        
        Формат должен быть строго такой:
        
        1. Вопрос 1?
        1) Вариант ответа 1
        2) Вариант ответа 2
        3) Вариант ответа 3
        4) Вариант ответа 4
        Правильный ответ: [номер от 1 до 4]
        
        2. Вопрос 2?
        1) Вариант ответа 1
        2) Вариант ответа 2
        3) Вариант ответа 3
        4) Вариант ответа 4
        Правильный ответ: [номер от 1 до 4]
        
        И так далее для всех 20 вопросов. Строго соблюдай формат с нумерацией вопросов и вариантов ответов. В каждом вопросе ОБЯЗАТЕЛЬНО должны быть варианты ответов с номерами от 1 до 4 и указан правильный ответ.
        
        Дополнительные требования:
        - Используй только знания о событиях, людях и фактах из истории России
        - Убедись, что в каждом вопросе указан правильный ответ в формате "Правильный ответ: X"
        - Не используй символы форматирования Markdown (* _ ` и т.д.)
        - Используй ТОЛЬКО цифры 1, 2, 3, 4 для нумерации вариантов ответа
        - Между вариантами ответов должен быть перенос строки
        - Каждый вопрос должен быть качественным и содержательным
        """
        
        try:
            # Получаем текстовый ответ API с вопросами
            result = self.call_api(
                prompt=prompt,
                temperature=0.7,  # Для разнообразия вопросов
                max_tokens=2048,   # Достаточно для полного теста
                use_cache=False    # Отключаем кэширование для получения свежих вопросов
            )
            
            response_text = result.get("text", "")
            
            # Проверяем наличие вопросов в ответе
            if not response_text or len(response_text) < 100:
                self.logger.warning(f"Слишком короткий ответ от API при генерации теста: {response_text[:50]}...")
                raise ValueError("Получен слишком короткий ответ от API")
            
            # Проверяем наличие правильных ответов в тексте
            import re
            if not re.search(r"Правильный ответ:\s*[1-4]", response_text):
                self.logger.warning("В ответе API нет указаний на правильные ответы")
                # Пробуем альтернативный формат
                if re.search(r"Ответ:\s*[1-4]", response_text):
                    response_text = response_text.replace("Ответ:", "Правильный ответ:")
                else:
                    raise ValueError("В ответе не указаны правильные ответы")
            
            # Разбиваем текст на отдельные вопросы
            questions = []
            raw_questions = re.split(r'\n\s*\n|\n\d+[\.\)]\s+', response_text)
            
            for q in raw_questions:
                q = q.strip()
                if q and len(q) > 10 and ('?' in q):
                    # Удаляем начальные цифры, если они есть
                    q = re.sub(r'^(\d+[\.\)]|\d+\.)\s*', '', q).strip()
                    questions.append(q)
            
            # Проверяем, есть ли вопросы
            if not questions:
                self.logger.warning(f"Не удалось разбить ответ на вопросы: {response_text[:100]}...")
                # Используем весь текст как один вопрос
                questions = [response_text]
            
            # Форматируем результат для обратной совместимости
            return {
                "status": "success",
                "topic": topic,
                "content": questions,
                "original_questions": questions,
                "display_questions": questions
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка при генерации теста по теме '{topic}': {e}")
            
            # Создаем базовый тест в аварийном режиме
            try:
                # Простой запрос для генерации теста
                emergency_prompt = f"Создай 5 простых вопросов для тестирования по теме '{topic}'. Каждый вопрос должен иметь 4 варианта ответа (1-4) и указанный правильный ответ. Нумеруй вопросы."
                emergency_response = self.model.generate_content(emergency_prompt)
                emergency_text = emergency_response.text
                
                if emergency_text and len(emergency_text) > 100:
                    return {
                        "status": "success",
                        "topic": topic,
                        "content": [emergency_text],
                        "original_questions": [emergency_text],
                        "display_questions": [emergency_text]
                    }
            except Exception as e2:
                self.logger.error(f"Не удалось создать аварийный тест: {e2}")
            
            # Если и аварийный вариант не сработал
            return {
                "status": "error",
                "topic": topic,
                "content": f"Произошла ошибка при генерации теста: {str(e)}. Пожалуйста, попробуйте еще раз."
            }
