
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
    
    def _process_queue(self):
        """Обрабатывает очередь запросов с учетом ограничений частоты - оптимизированная версия"""
        consecutive_errors = 0
        max_consecutive_errors = 5
        backoff_factor = 1.5  # Множитель для экспоненциального отступа
        
        while self.running:
            try:
                # Адаптивный таймаут: меньше при наличии запросов, больше при пустой очереди
                queue_size = self.queue.qsize()
                timeout = 0.1 if queue_size > 0 else 0.5
                
                try:
                    func, args, kwargs, callback = self.queue.get(block=True, timeout=timeout)
                except queue.Empty:
                    continue
                
                # Проверяем интервал между запросами с минимальной блокировкой
                current_time = time.time()
                
                with self.lock:
                    time_since_last = current_time - self.last_request_time
                    if time_since_last < self.min_interval:
                        wait_time = self.min_interval - time_since_last
                    else:
                        wait_time = 0
                
                # Ожидаем без блокировки, если необходимо
                if wait_time > 0:
                    time.sleep(wait_time)
                
                # Выполняем запрос с минимальной блокировкой
                try:
                    result = func(*args, **kwargs)
                    success = True
                    # Сбрасываем счетчик ошибок при успехе
                    consecutive_errors = 0
                except telegram.error.RetryAfter as e:
                    retry_after = e.retry_after
                    
                    # Логируем с минимальной частотой
                    if self.logger:
                        self.logger.warning(f"Превышен лимит запросов. Ожидание {retry_after} секунд. Очередь: {queue_size}")
                    
                    # Приоритизируем запросы с RetryAfter
                    # Возвращаем в начало очереди для повторной попытки после задержки
                    temp_queue = queue.Queue()
                    temp_queue.put((func, args, kwargs, callback))
                    
                    # Переносим до 10 элементов из основной очереди во временную
                    for _ in range(min(10, self.queue.qsize())):
                        try:
                            temp_queue.put(self.queue.get_nowait())
                            self.queue.task_done()
                        except queue.Empty:
                            break
                    
                    # Возвращаем все элементы обратно после задержки
                    time.sleep(retry_after + 0.1)  # Небольшой дополнительный запас
                    
                    # Возвращаем элементы в основную очередь
                    while not temp_queue.empty():
                        self.queue.put(temp_queue.get_nowait())
                    
                    # Завершаем текущую итерацию
                    self.queue.task_done()
                    continue
                    
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"Ошибка при выполнении запроса к Telegram API: {e}")
                    success = False
                    result = e
                    consecutive_errors += 1
                    
                    # Экспоненциальный отступ при повторяющихся ошибках
                    if consecutive_errors > 1:
                        backoff_time = min(30, backoff_factor ** (consecutive_errors - 1))
                        time.sleep(backoff_time)
                
                # Обновляем время последнего запроса с минимальной блокировкой
                with self.lock:
                    self.last_request_time = time.time()
                
                # Вызываем callback вне блокировки
                if callback:
                    try:
                        if success:
                            callback(result, None)
                        else:
                            callback(None, result)
                    except Exception as callback_error:
                        if self.logger:
                            self.logger.error(f"Ошибка в callback-функции: {callback_error}")
                
                # Сообщаем о завершении обработки
                self.queue.task_done()
                
                # Останавливаем работу потока при множественных ошибках
                if consecutive_errors >= max_consecutive_errors:
                    if self.logger:
                        self.logger.critical(f"Превышено максимальное количество ошибок ({max_consecutive_errors}), перезапуск очереди")
                    # Перезапуск потока
                    return
                
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Критическая ошибка в обработчике очереди: {e}")
                # Небольшая пауза перед продолжением при ошибке
                time.sleep(0.5)
    
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
