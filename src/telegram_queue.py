
import time
import queue
import threading
from functools import wraps
import telegram

class TelegramRequestQueue:
    """Класс для управления очередью запросов к Telegram API"""
    
    def __init__(self, max_requests_per_second=30, logger=None):
        self.queue = queue.Queue()
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()
        self.logger = logger
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()
    
    # Создаем кэш для запросов, чтобы избежать дублирования
    def __init__(self, max_requests_per_second=30, logger=None, cache_size=100):
        self.queue = queue.Queue()
        self.max_requests_per_second = max_requests_per_second
        self.min_interval = 1.0 / max_requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()
        self.logger = logger
        self.running = True
        # Добавляем кэш для хранения результатов запросов
        self.request_cache = {}
        self.cache_size = cache_size
        self.cache_hits = 0
        self.worker_thread = threading.Thread(target=self._process_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()
    
    def _process_queue(self):
        """Обрабатывает очередь запросов с учетом ограничений частоты"""
        while self.running:
            try:
                # Получаем запрос из очереди с меньшим таймаутом для более быстрой обработки
                try:
                    func, args, kwargs, callback = self.queue.get(block=True, timeout=0.2)
                except queue.Empty:
                    # Очередь пуста, продолжаем цикл без дополнительных действий
                    continue
                
                # Генерируем ключ кэша на основе функции и аргументов
                cache_key = self._generate_cache_key(func, args, kwargs)
                
                # Проверяем, есть ли результат в кэше
                cached_result = self._get_from_cache(cache_key)
                if cached_result is not None:
                    self.cache_hits += 1
                    if callback:
                        callback(cached_result, None)
                    self.queue.task_done()
                    continue
                
                # Проверяем интервал между запросами
                with self.lock:
                    current_time = time.time()
                    time_since_last = current_time - self.last_request_time
                    
                    # Оптимизированная проверка и ожидание
                    if time_since_last < self.min_interval:
                        sleep_time = self.min_interval - time_since_last
                        # Выходим из блокировки на время ожидания
                        self.lock.release()
                        time.sleep(sleep_time)
                        self.lock.acquire()
                    
                    # Выполняем запрос
                    try:
                        result = func(*args, **kwargs)
                        success = True
                        # Сохраняем результат в кэше
                        self._add_to_cache(cache_key, result)
                    except telegram.error.RetryAfter as e:
                        # Оптимизированная обработка RetryAfter
                        if self.logger:
                            self.logger.warning(f"Превышен лимит запросов. Ожидание {e.retry_after} секунд")
                        
                        # Возвращаем элемент в очередь и ждем
                        self.queue.put((func, args, kwargs, callback))
                        self.lock.release()
                        time.sleep(e.retry_after)
                        self.lock.acquire()
                        # Сообщаем о завершении обработки текущего элемента очереди
                        self.queue.task_done()
                        continue
                    except Exception as e:
                        if self.logger:
                            self.logger.error(f"Ошибка при выполнении запроса к Telegram API: {e}")
                        success = False
                        result = e
                    
                    # Обновляем время последнего запроса
                    self.last_request_time = time.time()
                
                # Вызываем callback вне блокировки для повышения производительности
                if callback:
                    if success:
                        callback(result, None)
                    else:
                        callback(None, result)
                
                # Сообщаем о завершении обработки элемента очереди
                self.queue.task_done()
                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Ошибка в обработчике очереди: {e}")
                    
    def _generate_cache_key(self, func, args, kwargs):
        """Генерирует ключ для кэширования запроса"""
        try:
            # Используем имя функции и хэш аргументов для создания ключа
            return f"{func.__name__}:{hash(str(args))}:{hash(str(kwargs))}"
        except Exception:
            # Если не удалось создать хэш, возвращаем None (не будем кэшировать)
            return None
            
    def _get_from_cache(self, cache_key):
        """Получает результат из кэша"""
        if not cache_key:
            return None
        return self.request_cache.get(cache_key)
        
    def _add_to_cache(self, cache_key, result):
        """Добавляет результат в кэш"""
        if not cache_key:
            return
            
        # Если кэш слишком большой, удаляем старые записи
        if len(self.request_cache) >= self.cache_size:
            # Используем списковое включение для получения ключей
            keys = list(self.request_cache.keys())[:len(self.request_cache) // 4]
            # Удаляем четверть старых ключей
            for k in keys:
                del self.request_cache[k]
                
        self.request_cache[cache_key] = result
    
    def enqueue(self, func, *args, callback=None, **kwargs):
        """Добавляет запрос в очередь"""
        self.queue.put((func, args, kwargs, callback))
    
    def stop(self):
        """Останавливает обработчик очереди"""
        self.running = False
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)

def rate_limited(queue_instance):
    """Декоратор для ограничения частоты вызовов функций Telegram API"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            future_result = {"completed": False, "result": None, "error": None}
            
            def callback(result, error):
                future_result["completed"] = True
                future_result["result"] = result
                future_result["error"] = error
            
            # Добавляем запрос в очередь
            queue_instance.enqueue(func, *args, callback=callback, **kwargs)
            
            # Ждем результата (можно убрать для асинхронной работы)
            timeout = kwargs.pop('_timeout', 30)  # 30 секунд по умолчанию
            start_time = time.time()
            
            while not future_result["completed"] and (time.time() - start_time < timeout):
                time.sleep(0.1)
            
            if not future_result["completed"]:
                raise TimeoutError(f"Запрос к Telegram API не завершился за {timeout} секунд")
            
            if future_result["error"]:
                raise future_result["error"]
                
            return future_result["result"]
        
        return wrapper
    return decorator
