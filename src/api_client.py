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
from src.base_service import BaseService

class APIClient(BaseService):
    """
    Клиент для работы с Google Gemini API.

    Обеспечивает взаимодействие с моделью Gemini Pro для:
    - Генерации исторического контента
    - Проверки релевантности запросов
    - Создания тестовых заданий

    Версионирование API:
    - v1: Базовая версия API с основной функциональностью
    - v2: Добавлены методы для кэширования и повторных попыток
    - v3: Усовершенствованные промпты и обработка ошибок
    """

    # Текущая версия API
    API_VERSION = "3.0.0"

    def __init__(self, api_key: str, cache: ICache, logger: ILogger):
        """
        Инициализация API клиента для Google Gemini.

        Args:
            api_key (str): API ключ для Google Gemini
            cache (ICache): Компонент для кэширования запросов
            logger (ILogger): Компонент для логирования операций
        """
        super().__init__(logger)
        self.api_key = api_key
        self.cache = cache
        self.model = None
        self.initialize_model()
        # Добавляем кэширование для API запросов
        self.request_cache = {}
        self.cache_ttl = 3600  # Время жизни кэша в секундах (1 час)
        self.cache_hits = 0
        self.cache_misses = 0

    def _do_initialize(self) -> bool:
        """
        Выполняет фактическую инициализацию сервиса.

        Returns:
            bool: True если инициализация прошла успешно, иначе False
        """
        try:
            # Проверяем доступность API ключа
            if not self.api_key:
                self._logger.error("API ключ не указан")
                return False
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            self._logger.info("Gemini API успешно инициализирован (модель: gemini-2.0-flash)")
            return True
        except Exception as e:
            self._logger.error(f"Ошибка при инициализации APIClient: {e}")
            return False


    def initialize_model(self) -> None:
        """
        Инициализация модели Google Gemini с повторными попытками.
        """
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                if not self.api_key:
                    raise ValueError("API ключ не указан")
                    
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-pro')
                
                # Проверяем работоспособность модели
                test_response = self.model.generate_content("Test connection")
                if test_response and hasattr(test_response, 'text'):
                    self._logger.info("Gemini API успешно инициализирован")
                    return
                    
            except Exception as e:
                self._logger.warning(f"Попытка {attempt + 1}/{max_retries} инициализации модели не удалась: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    self._logger.error("Не удалось инициализировать модель Gemini после всех попыток")
                    raise

    # Хэш-функция для создания ключа кэша
    def _create_cache_key(self, prompt: str, temperature: float, max_tokens: int, system_prompt: Optional[str]) -> str:
        """Создает ключ для кэша на основе параметров запроса"""
        import hashlib
        cache_key_data = f"{prompt}:{temperature}:{max_tokens}:{system_prompt}"
        return hashlib.md5(cache_key_data.encode()).hexdigest()

    def _get_cache_key(self, prompt, model=None, max_tokens=None):
        """Создает ключ для кэширования на основе параметров запроса"""
        return f"{hash(prompt)}:{model}:{max_tokens}"

    def _get_from_cache(self, key):
        """Получает данные из кэша с проверкой времени жизни"""
        if key not in self.request_cache:
            return None

        cache_entry = self.request_cache[key]
        # Проверяем, не истекло ли время жизни кэша
        if time.time() - cache_entry['timestamp'] > self.cache_ttl:
            # Кэш устарел, удаляем запись
            del self.request_cache[key]
            return None

        self.cache_hits += 1
        return cache_entry['data']

    def _add_to_cache(self, key, data):
        """Добавляет данные в кэш"""
        self.request_cache[key] = {
            'data': data,
            'timestamp': time.time()
        }

        # Если размер кэша слишком большой, удаляем старые записи
        if len(self.request_cache) > 1000:
            # Используем списковое включение для получения старых ключей
            old_keys = [k for k, v in self.request_cache.items() 
                       if time.time() - v['timestamp'] > self.cache_ttl]

            # Если старых записей недостаточно, удаляем самые старые
            if len(old_keys) < 100:
                # Сортируем по времени создания и берем 20% самых старых
                sorted_keys = sorted(self.request_cache.keys(), 
                                   key=lambda k: self.request_cache[k]['timestamp'])
                old_keys = sorted_keys[:max(100, len(sorted_keys) // 5)]

            # Удаляем старые записи
            for key in old_keys:
                del self.request_cache[key]

    def clear_cache(self):
        """Очищает кэш API запросов"""
        cache_size = len(self.request_cache)
        self.request_cache.clear()
        self.logger.info(f"API кэш очищен, удалено {cache_size} записей")
        return cache_size


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
        # Проверяем кэш, если нужно
        if use_cache:
            cache_key = self._get_cache_key(prompt, 'gemini-2.0-flash', max_tokens)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                self._logger.debug(f"Получен ответ из кэша для промпта: {prompt[:50]}...")
                return cached_result

        # Настройка параметров генерации - вынесена вне цикла для оптимизации
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "top_p": 0.95,
            "top_k": 40,
        }

        # Выполняем запрос с механизмом повторных попыток
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                start_time = time.time()
                self._logger.debug(f"Отправка запроса к Gemini API: {prompt[:50]}...")

                # Добавляем информацию о версии API в запрос
                api_info = f"API Version: {self.API_VERSION}"

                # Формирование промпта с системной инструкцией если она предоставлена
                try:
                    if system_prompt:
                        # Для Gemini 2.0 используем обновленный метод формирования чата
                        # Добавляем информацию о версии API в системный промпт
                        versioned_system_prompt = f"{system_prompt}\n\n{api_info}"
                        chat = self.model.start_chat(history=[
                            {"role": "user", "parts": [versioned_system_prompt]},
                            {"role": "model", "parts": ["Понял инструкции. Готов к работе."]}
                        ])
                        response = chat.send_message(prompt, generation_config=generation_config)
                    else:
                        # Стандартный запрос к модели с добавлением версии в метаданные
                        versioned_prompt = f"{prompt}\n\n{api_info}"
                        response = self.model.generate_content(versioned_prompt, generation_config=generation_config)
                except AttributeError:
                    try:
                        # Альтернативный метод для новой версии API с дополнительной обработкой ошибок
                        response = self.model.generate_content(
                            content=prompt,
                            generation_config=generation_config,
                            safety_settings=[
                                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                            ]
                        )
                        
                        if not response or not hasattr(response, 'text'):
                            raise Exception("Пустой ответ от API")
                            
                    except Exception as api_error:
                        self._logger.error(f"Ошибка при генерации контента: {str(api_error)}")
                        # Пробуем упрощенный запрос без дополнительных настроек
                        response = self.model.generate_content(prompt)

                elapsed_time = time.time() - start_time
                self._logger.debug(f"Ответ получен за {elapsed_time:.2f}с")

                # Обработка ответа
                result = {
                    "text": response.text,
                    "status": "success",
                    "model": "gemini-2.0-flash",
                    "elapsed_time": elapsed_time
                }

                # Сохраняем в кэш
                if use_cache:
                    cache_key = self._get_cache_key(prompt, 'gemini-2.0-flash', max_tokens)
                    self._add_to_cache(cache_key, result)

                return result

            except Exception as e:
                error_type = type(e).__name__
                error_details = str(e)

                # Classify error for better handling
                if "quota" in error_details.lower() or "rate" in error_details.lower():
                    self._logger.warning(f"Превышен лимит запросов к Gemini API (попытка {attempt+1}/{max_retries}): {error_type} - {error_details}")
                    retry_delay_extended = retry_delay * (3 ** attempt)  # Более длительная задержка для rate-limiting
                elif "timeout" in error_type.lower() or "timeout" in error_details.lower():
                    self._logger.warning(f"Таймаут запроса к Gemini API (попытка {attempt+1}/{max_retries}): {error_details}")
                    retry_delay_extended = retry_delay * (2 ** attempt)
                elif "connection" in error_type.lower() or "network" in error_details.lower():
                    self._logger.warning(f"Проблема сетевого подключения к Gemini API (попытка {attempt+1}/{max_retries}): {error_details}")
                    retry_delay_extended = retry_delay * (2 ** attempt)
                else:
                    self._logger.warning(f"Ошибка запроса к Gemini API (попытка {attempt+1}/{max_retries}): {error_type} - {error_details}")
                    retry_delay_extended = retry_delay * (2 ** attempt)

                if attempt < max_retries - 1:
                    # Применяем стратегию отступа в зависимости от типа ошибки
                    self._logger.info(f"Повторная попытка через {retry_delay_extended} секунд")
                    time.sleep(retry_delay_extended)
                else:
                    self._logger.error(f"Не удалось получить ответ от Gemini API после {max_retries} попыток: {error_type} - {error_details}")
                    # Создаем более информативное исключение
                    raise Exception(f"Исчерпаны попытки запроса к Gemini API: {error_type} - {error_details}")

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

            self._logger.debug(f"Проверка темы '{topic}': {is_historical}")
            return is_historical

        except Exception as e:
            self._logger.error(f"Ошибка при проверке исторической темы: {e}")
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
            self._logger.error(f"Ошибка при получении исторической информации: {e}")
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
            self._logger.error(f"Ошибка в методе ask_grok: {e}")
            # Попробуем запасной метод для Gemini 2.0
            try:
                self._logger.info("Пробуем альтернативный метод вызова API...")
                response = self.model.generate_content(content=prompt)
                return response.text
            except Exception as e2:
                self._logger.error(f"Вторая ошибка в методе ask_grok: {e2}")
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
        - Используй ТОЛЬКО цифры 1, 2, 3, 4 для нумерации варианта ответа
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
                self._logger.warning(f"Слишком короткий ответ от API при генерации теста: {response_text[:50]}...")
                raise ValueError("Получен слишком короткий ответ от API")

            # Проверяем наличие правильных ответов в тексте
            import re
            if not re.search(r"Правильный ответ:\s*[1-4]", response_text):
                self._logger.warning("В ответе API нет указаний на правильные ответы")
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
                self._logger.warning(f"Не удалось разбить ответ на вопросы: {response_text[:100]}...")
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
            self._logger.error(f"Ошибка при генерации теста по теме '{topic}': {e}")

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
                self._logger.error(f"Не удалось создать аварийный тест: {e2}")

            # Если и аварийный вариант не сработал
            return {
                "status": "error",
                "topic": topic,
                "content": f"Произошла ошибка при генерации теста: {str(e)}. Пожалуйста, попробуйте еще раз."
            }

    def clear_cache(self, topic_filter=None):
        """
        Очищает кэш API запросов

        Args:
            topic_filter (str, optional): Если указан, очищает только кэш по определенной теме

        Returns:
            int: Количество удаленных записей из кэша
        """
        try:
            count = self.clear_cache() #Using the new clear_cache method.
            self._logger.info(f"Очищено {count} записей из кэша API запросов")
            return count
        except Exception as e:
            self._logger.error(f"Ошибка при очистке кэша API запросов: {e}")
            return 0