"""
Модуль для логирования событий приложения.

Предоставляет расширенную систему логирования с поддержкой:
- Вывода в консоль и файл с автоматической ротацией по дням
- Различных уровней детализации (debug, info, warning, error)
- Форматированных сообщений об ошибках с дополнительной информацией
- Фильтрации и получения логов для административного интерфейса
"""

import os
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
import threading
import json
import time
from logging.handlers import RotatingFileHandler
from src.interfaces import ILogger

class BufferedLogger:
    """Буферизированный логгер для снижения I/O операций"""

    def __init__(self, logger, buffer_size=10, flush_interval=5):
        self.logger = logger
        self.buffer = []
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.last_flush = time.time()

    def _check_flush(self):
        # Сброс буфера по размеру или по времени
        current_time = time.time()
        if len(self.buffer) >= self.buffer_size or (current_time - self.last_flush) >= self.flush_interval:
            for level, msg in self.buffer:
                if level == 'debug':
                    self.logger.debug(msg)
                elif level == 'info':
                    self.logger.info(msg)
                elif level == 'warning':
                    self.logger.warning(msg)
                elif level == 'error':
                    self.logger.error(msg)
                elif level == 'critical':
                    self.logger.critical(msg)
            self.buffer = []
            self.last_flush = current_time

    def debug(self, msg):
        self.buffer.append(('debug', msg))
        self._check_flush()

    def info(self, msg):
        self.buffer.append(('info', msg))
        self._check_flush()

    def warning(self, msg):
        # Предупреждения и ошибки записываем сразу без буферизации
        self.logger.warning(msg)

    def error(self, msg):
        # Ошибки записываем сразу без буферизации
        self.logger.error(msg)

    def critical(self, msg):
        # Критические ошибки записываем сразу без буферизации
        self.logger.critical(msg)

class Logger(ILogger):
    """
    Имплементация интерфейса логирования.

    Особенности:
    - Поддержка вывода в консоль и файл с ротацией логов по дням
    - Потокобезопасное логирование
    - Детализированные сообщения об ошибках с контекстом
    - API для фильтрации и получения логов для административного интерфейса
    """

    def __init__(self, log_level: int = logging.WARNING, log_dir: str = 'logs'):
        """
        Инициализация системы логирования.

        Args:
            log_level (int): Уровень детализации логов (по умолчанию WARNING)
            log_dir (str): Директория для хранения файлов логов
        """
        self.log_level = log_level
        self.log_dir = log_dir
        self.error_descriptions = self._load_error_descriptions()
        self.lock = threading.RLock()  # Для потокобезопасности

        # Создаем директорию для логов, если не существует
        os.makedirs(self.log_dir, exist_ok=True)

        # Создаем и настраиваем логгер
        self.logger = logging.getLogger("bot_logger")
        self.logger.setLevel(self.log_level)

        # Очищаем обработчики логов, если они уже были настроены
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Настраиваем форматирование
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Создаем и настраиваем обработчик для вывода только ошибок в консоль
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Создаем и настраиваем обработчик для записи в файл с ротацией
        log_file = os.path.join(self.log_dir, 'bot.log')
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=3,         # Хранить 3 бэкапа
            encoding='utf-8'
        )
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Создаем буферизированный логгер для оптимизации I/O операций
        self.buffered_logger = BufferedLogger(self.logger, buffer_size=20, flush_interval=10)

        self.warning("Система логирования инициализирована с уровнем WARNING")

    def _load_error_descriptions(self) -> Dict[str, str]:
        """
        Загружает словарь с описаниями ошибок для более информативного логирования.

        Returns:
            Dict[str, str]: Словарь с типами ошибок и их человекочитаемыми описаниями
        """
        # Базовые описания типичных ошибок
        descriptions = {
            "ConnectionError": "Ошибка подключения к внешнему API. Проверьте интернет-соединение.",
            "Timeout": "Превышено время ожидания ответа от внешнего API.",
            "JSONDecodeError": "Ошибка при разборе JSON ответа от API.",
            "HTTPError": "Ошибка HTTP при запросе к внешнему API.",
            "TelegramError": "Ошибка при взаимодействии с Telegram API.",
            "KeyboardInterrupt": "Бот был остановлен вручную.",
            "ApiError": "Ошибка при взаимодействии с внешним API.",
            "TelegramError": "Ошибка Telegram API",
            "Unauthorized": "Неверный токен бота",
            "BadRequest": "Неверный запрос к Telegram API",
            "TimedOut": "Превышено время ожидания ответа от Telegram API",
            "NetworkError": "Проблемы с сетью",
            "ChatMigrated": "Чат был перенесен",
            "RetryAfter": "Превышен лимит запросов, ожидание",
            "InvalidToken": "Неверный токен бота",
            "Conflict": "Конфликт запросов getUpdates. Проверьте, что запущен только один экземпляр бота"
        }

        return descriptions

    def info(self, message: str) -> None:
        """
        Логирование информационного сообщения с буферизацией.
        """
        if self.log_level <= logging.INFO:
            self.buffered_logger.info(message)

    def error(self, message: str) -> None:
        """
        Логирование сообщения об ошибке.
        """
        self.buffered_logger.error(message)

    def warning(self, message: str) -> None:
        """
        Логирование предупреждения.
        """
        self.buffered_logger.warning(message)

    def debug(self, message: str) -> None:
        """
        Логирование отладочного сообщения с буферизацией.
        """
        if self.log_level <= logging.DEBUG:
            self.buffered_logger.debug(message)

    def log_error(self, error: Exception, additional_info: Optional[Dict[str, Any]] = None) -> None:
        """
        Расширенное логирование исключения с дополнительной информацией.

        Args:
            error (Exception): Объект исключения для логирования
            additional_info (Dict[str, Any], optional): Дополнительная информация
                о контексте возникновения ошибки
        """
        # Получаем тип ошибки
        error_type = type(error).__name__

        # Получаем описание ошибки из словаря или используем сообщение ошибки
        error_description = self.error_descriptions.get(error_type, str(error))

        # Формируем сообщение об ошибке
        error_message = f"Ошибка [{error_type}]: {error_description}"

        # Добавляем дополнительную информацию, если она предоставлена
        if additional_info:
            info_str = json.dumps(additional_info, ensure_ascii=False, default=str)
            error_message += f" Дополнительная информация: {info_str}"

        # Логируем сообщение об ошибке
        self.buffered_logger.error(error_message)

        # Логируем стек вызовов для упрощения отладки
        self.buffered_logger.error(f"Стек вызовов:\n{traceback.format_exc()}")

    def get_logs(self, level: Optional[str] = None, 
                 start_date: Optional[datetime] = None, 
                 end_date: Optional[datetime] = None, 
                 limit: int = 100) -> List[Dict[str, Any]]:
        """
        Получение логов с фильтрацией по уровню, дате и ограничением количества.

        Метод для административного интерфейса, позволяющий просматривать
        и фильтровать логи по различным параметрам.

        Args:
            level (str, optional): Уровень логирования для фильтрации (DEBUG, INFO, WARNING, ERROR)
            start_date (datetime, optional): Начальная дата для фильтрации
            end_date (datetime, optional): Конечная дата для фильтрации
            limit (int): Максимальное количество возвращаемых записей (по умолчанию 100)

        Returns:
            List[Dict[str, Any]]: Список записей логов, соответствующих параметрам фильтрации
        """
        logs = []

        # Определяем период для поиска логов
        if not start_date:
            # Если начальная дата не указана, берем логи только за текущий день
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if not end_date:
            # Если конечная дата не указана, берем до текущего момента
            end_date = datetime.now()

        # Преобразуем уровень логирования в числовое значение
        level_num = None
        if level:
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL
            }
            level_num = level_map.get(level.upper())

        # Получаем список файлов логов в заданном периоде
        log_files = []
        current_date = start_date
        while current_date <= end_date:
            log_filename = os.path.join(self.log_dir, f'bot_log_{current_date.strftime("%Y%m%d")}.log')
            if os.path.exists(log_filename):
                log_files.append(log_filename)

            # Переходим к следующему дню
            current_date = current_date.replace(day=current_date.day + 1)

        # Обрабатываем файлы логов в обратном порядке (от новых к старым)
        for log_file in reversed(log_files):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in reversed(f.readlines()):
                        try:
                            # Разбираем строку лога
                            parts = line.strip().split(' - ', 2)
                            if len(parts) < 3:
                                continue

                            timestamp_str, log_level, message = parts

                            # Парсим временную метку
                            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')

                            # Проверяем, входит ли запись в указанный период
                            if timestamp < start_date or timestamp > end_date:
                                continue

                            # Проверяем, соответствует ли запись указанному уровню
                            if level_num is not None:
                                current_level_num = {
                                    "DEBUG": logging.DEBUG,
                                    "INFO": logging.INFO,
                                    "WARNING": logging.WARNING,
                                    "ERROR": logging.ERROR,
                                    "CRITICAL": logging.CRITICAL
                                }.get(log_level)

                                if current_level_num is None or current_level_num < level_num:
                                    continue

                            # Добавляем запись в результат
                            logs.append({
                                "timestamp": timestamp,
                                "level": log_level,
                                "message": message
                            })

                            # Проверяем ограничение на количество
                            if len(logs) >= limit:
                                break
                        except Exception:
                            # Пропускаем некорректные строки
                            continue

                # Если достигнуто ограничение, прекращаем обработку файлов
                if len(logs) >= limit:
                    break

            except Exception as e:
                self.error(f"Ошибка при чтении файла логов {log_file}: {e}")

        return logs