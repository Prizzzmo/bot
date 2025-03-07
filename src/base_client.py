
"""Базовый клиент для API запросов"""

import json
import time
from abc import ABC, abstractmethod
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from src.interfaces import ILogger, ICache

class BaseClient(ABC):
    """
    Абстрактный базовый класс для реализации API клиентов.
    Предоставляет общую функциональность для работы с внешними API.
    """

    def __init__(self, api_key, cache, logger):
        """
        Инициализация базового API клиента.
        
        Args:
            api_key (str): API ключ для авторизации
            cache (ICache): Имплементация интерфейса кэширования
            logger (ILogger): Имплементация интерфейса логирования
        """
        self.api_key = api_key
        self.cache = cache
        self.logger = logger
        self.base_url = None
        self.default_headers = {}
        self.default_timeout = 30
        self.retry_attempts = 3
        self.retry_delay = 2  # секунды

    def _make_request(self, method, endpoint, params=None, data=None, headers=None, timeout=None, use_cache=True):
        """
        Выполняет HTTP запрос с поддержкой кэширования, повторов и логирования.
        
        Args:
            method (str): HTTP метод ('GET', 'POST', etc.)
            endpoint (str): API эндпоинт
            params (dict, optional): Параметры запроса
            data (dict, optional): Данные для отправки в теле запроса
            headers (dict, optional): HTTP заголовки
            timeout (int, optional): Таймаут запроса в секундах
            use_cache (bool): Использовать ли кэш для данного запроса
            
        Returns:
            dict: Результат запроса в формате JSON
            
        Raises:
            RequestException: При ошибке выполнения запроса
        """
        url = f"{self.base_url}{endpoint}" if self.base_url else endpoint
        request_headers = {**self.default_headers, **(headers or {})}
        request_timeout = timeout or self.default_timeout
        
        # Формируем ключ кэша
        cache_key = None
        if use_cache and method.upper() == 'GET':
            cache_key = self._generate_cache_key(url, params)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                self.logger.debug(f"Данные получены из кэша: {url}")
                return cached_result
        
        for attempt in range(self.retry_attempts):
            try:
                self.logger.debug(f"Выполняется {method} запрос: {url}")
                start_time = time.time()
                
                response = requests.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data if method.upper() in ('POST', 'PUT', 'PATCH') else None,
                    headers=request_headers,
                    timeout=request_timeout
                )
                
                elapsed_time = time.time() - start_time
                self.logger.debug(f"Запрос выполнен за {elapsed_time:.2f}с, статус: {response.status_code}")
                
                # Проверяем успешность запроса
                response.raise_for_status()
                
                # Парсим ответ в JSON
                result = response.json()
                
                # Сохраняем в кэш если нужно
                if cache_key and use_cache:
                    self.cache.set(cache_key, result)
                
                return result
                
            except ConnectionError as e:
                self.logger.warning(f"Ошибка соединения: {e}. Попытка {attempt+1} из {self.retry_attempts}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Экспоненциальная задержка
                else:
                    self.logger.error(f"Не удалось выполнить запрос после {self.retry_attempts} попыток: {e}")
                    raise
            
            except Timeout as e:
                self.logger.warning(f"Превышен таймаут запроса: {e}")
                raise
                
            except RequestException as e:
                self.logger.error(f"Ошибка запроса к {url}: {e}")
                raise
    
    def _generate_cache_key(self, url, params=None):
        """
        Генерирует ключ кэша для запроса.
        
        Args:
            url (str): URL запроса
            params (dict, optional): Параметры запроса
            
        Returns:
            str: Хэш-ключ для кэширования
        """
        import hashlib
        key_data = f"{url}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
        
    @abstractmethod
    def call_api(self, *args, **kwargs):
        """
        Абстрактный метод для реализации конкретного API вызова
        """
        pass
