
"""
Модуль для обработки отложенных задач

Позволяет выполнять длительные операции в фоновом режиме
без блокировки основного потока бота.
"""

import threading
import queue
import time
import traceback
from typing import Dict, Any, Callable, List, Optional
import uuid

class Task:
    """Представляет отложенную задачу для выполнения"""
    
    def __init__(self, func: Callable, args: List = None, kwargs: Dict = None):
        """
        Инициализация задачи

        Args:
            func: Функция для выполнения
            args: Позиционные аргументы для функции
            kwargs: Именованные аргументы для функции
        """
        self.id = str(uuid.uuid4())
        self.func = func
        self.args = args or []
        self.kwargs = kwargs or {}
        self.created_at = time.time()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self.status = "pending"  # pending, running, completed, failed

    def run(self):
        """Выполняет задачу и сохраняет результат или ошибку"""
        self.started_at = time.time()
        self.status = "running"
        
        try:
            self.result = self.func(*self.args, **self.kwargs)
            self.status = "completed"
        except Exception as e:
            self.error = str(e)
            self.status = "failed"
        
        self.completed_at = time.time()
        return self.result

    def get_info(self) -> Dict[str, Any]:
        """Возвращает информацию о задаче"""
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "execution_time": (self.completed_at - self.started_at) if self.completed_at else None,
            "wait_time": (self.started_at - self.created_at) if self.started_at else None,
            "error": self.error,
            "has_result": self.result is not None
        }


class TaskQueue:
    """Очередь для обработки отложенных задач в фоновом режиме"""
    
    def __init__(self, num_workers: int = 2, logger = None):
        """
        Инициализация очереди задач

        Args:
            num_workers: Количество рабочих потоков для выполнения задач
            logger: Логгер для записи информации о задачах
        """
        self.task_queue = queue.Queue()
        self.tasks = {}  # Хранилище задач по ID
        self.workers = []
        self.num_workers = num_workers
        self.logger = logger
        self.running = False
        self.lock = threading.RLock()
        
        # Статистика выполнения
        self.stats = {
            "completed": 0,
            "failed": 0,
            "total": 0
        }

    def start(self):
        """Запускает обработчики задач"""
        with self.lock:
            if self.running:
                return
            
            self.running = True
            self.workers = []
            
            for i in range(self.num_workers):
                worker = threading.Thread(
                    target=self._worker_loop,
                    name=f"TaskWorker-{i}",
                    daemon=True
                )
                self.workers.append(worker)
                worker.start()
            
            if self.logger:
                self.logger.info(f"Запущена очередь задач с {self.num_workers} рабочими потоками")

    def stop(self):
        """Останавливает обработчики задач"""
        with self.lock:
            self.running = False
            
            # Очищаем очередь, добавляя специальные задачи остановки
            for _ in range(self.num_workers):
                self.task_queue.put(None)
            
            # Ждем завершения рабочих потоков
            for worker in self.workers:
                if worker.is_alive():
                    worker.join(timeout=1.0)
            
            if self.logger:
                self.logger.info("Очередь задач остановлена")

    def _worker_loop(self):
        """Основной цикл рабочего потока"""
        while self.running:
            try:
                # Получаем задачу из очереди
                task = self.task_queue.get(block=True, timeout=1.0)
                
                # None используется как сигнал для остановки
                if task is None:
                    self.task_queue.task_done()
                    break
                
                # Выполняем задачу
                try:
                    task.run()
                    with self.lock:
                        if task.status == "completed":
                            self.stats["completed"] += 1
                        else:
                            self.stats["failed"] += 1
                
                except Exception as e:
                    # Обработка исключений при выполнении задачи
                    task.status = "failed"
                    task.error = f"Unhandled exception: {str(e)}\n{traceback.format_exc()}"
                    task.completed_at = time.time()
                    
                    with self.lock:
                        self.stats["failed"] += 1
                    
                    if self.logger:
                        self.logger.error(f"Ошибка при выполнении задачи {task.id}: {str(e)}")
                
                finally:
                    # Отмечаем задачу как завершенную в очереди
                    self.task_queue.task_done()
            
            except queue.Empty:
                # Таймаут получения задачи, проверяем флаг running
                continue
            except Exception as e:
                # Обработка других исключений в цикле обработчика
                if self.logger:
                    self.logger.error(f"Ошибка в цикле обработчика задач: {str(e)}")
                time.sleep(1.0)  # Небольшая пауза перед продолжением

    def add_task(self, func: Callable, args: List = None, kwargs: Dict = None) -> str:
        """
        Добавляет задачу в очередь

        Args:
            func: Функция для выполнения
            args: Позиционные аргументы для функции
            kwargs: Именованные аргументы для функции

        Returns:
            str: ID добавленной задачи
        """
        # Создаем задачу
        task = Task(func, args, kwargs)
        
        # Сохраняем задачу в хранилище
        with self.lock:
            self.tasks[task.id] = task
            self.stats["total"] += 1
        
        # Добавляем задачу в очередь
        self.task_queue.put(task)
        
        # Запускаем обработчики, если они еще не запущены
        if not self.running:
            self.start()
        
        if self.logger:
            self.logger.debug(f"Добавлена задача {task.id}")
        
        return task.id

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Возвращает задачу по ID

        Args:
            task_id: ID задачи

        Returns:
            Task: Задача или None, если не найдена
        """
        with self.lock:
            return self.tasks.get(task_id)

    def get_task_result(self, task_id: str, wait: bool = False, timeout: float = None) -> Dict[str, Any]:
        """
        Возвращает результат выполнения задачи

        Args:
            task_id: ID задачи
            wait: Ожидать завершения задачи, если она еще выполняется
            timeout: Таймаут ожидания в секундах (только если wait=True)

        Returns:
            Dict: Информация о задаче, включая статус и результат
        """
        task = self.get_task(task_id)
        
        if not task:
            return {
                "status": "not_found",
                "error": f"Задача с ID {task_id} не найдена"
            }
        
        # Если задача еще выполняется и нужно ожидать
        if wait and task.status in ["pending", "running"]:
            start_time = time.time()
            
            while task.status in ["pending", "running"]:
                # Проверяем таймаут
                if timeout and (time.time() - start_time) > timeout:
                    break
                
                # Ждем немного перед повторной проверкой
                time.sleep(0.1)
        
        # Формируем результат
        result = task.get_info()
        
        # Добавляем результат, если он есть
        if task.status == "completed" and task.result is not None:
            result["result"] = task.result
        
        return result

    def get_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику выполнения задач

        Returns:
            Dict: Статистика выполнения задач
        """
        with self.lock:
            stats = self.stats.copy()
            stats["pending"] = self.task_queue.qsize()
            stats["workers"] = self.num_workers
            stats["running"] = self.running
            
            # Добавляем информацию о производительности
            if stats["total"] > 0:
                stats["success_rate"] = (stats["completed"] / stats["total"]) * 100
            else:
                stats["success_rate"] = 0.0
            
            return stats

    def clean_old_tasks(self, max_age: float = 3600.0):
        """
        Очищает старые завершенные задачи из хранилища

        Args:
            max_age: Максимальный возраст задачи в секундах
        """
        current_time = time.time()
        
        with self.lock:
            old_tasks = []
            
            for task_id, task in self.tasks.items():
                # Очищаем только завершенные задачи
                if task.status in ["completed", "failed"]:
                    # Проверяем возраст задачи
                    if task.completed_at and (current_time - task.completed_at) > max_age:
                        old_tasks.append(task_id)
            
            # Удаляем старые задачи
            for task_id in old_tasks:
                del self.tasks[task_id]
            
            if self.logger and old_tasks:
                self.logger.debug(f"Очищено {len(old_tasks)} старых задач")
            
            return len(old_tasks)
