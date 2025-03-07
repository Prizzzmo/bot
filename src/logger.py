
import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime

from src.config import ERROR_DESCRIPTIONS

class Logger:
    """Класс для управления логированием приложения"""
    
    def __init__(self):
        self.logger = None
        self.setup_logging()
    
    def clean_logs(self):
        """
        Очищает лог-файлы при запуске бота.

        Returns:
            tuple: Кортеж (директория логов, путь к файлу лога)
        """
        try:
            # Проверяем наличие директории для логов
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Дата для имени файла лога
            log_date = datetime.now().strftime('%Y%m%d')
            log_file_path = f"{log_dir}/bot_log_{log_date}.log"

            # Очищаем текущий лог бота, если он существует
            if os.path.exists(log_file_path):
                with open(log_file_path, 'w') as f:
                    f.write("")

            # Очищаем временные логи в корневой директории, если они есть
            root_log_path = f"bot_log_{log_date}.log"
            if os.path.exists(root_log_path):
                with open(root_log_path, 'w') as f:
                    f.write("")

            return log_dir, log_file_path
        except Exception as e:
            print(f"Ошибка при очистке логов: {e}")
            # Возвращаем стандартные пути в случае ошибки
            return "logs", f"logs/bot_log_{datetime.now().strftime('%Y%m%d')}.log"
    
    def setup_logging(self):
        """
        Настраивает систему логирования для бота.

        Returns:
            logging.Logger: Настроенный логгер
        """
        # Очищаем логи и получаем пути
        log_dir, log_file_path = self.clean_logs()

        # Расширенная настройка логирования
        log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Используем RotatingFileHandler для ограничения размера файлов логов
        file_handler = RotatingFileHandler(
            log_file_path, 
            maxBytes=10485760,  # 10 МБ
            backupCount=3
        )
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(logging.ERROR)  # Записываем в файл только ошибки

        # Консольный вывод
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        console_handler.setLevel(logging.ERROR)  # Выводим в консоль только ошибки и критические сообщения

        # Настройка корневого логгера
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)  # Базовый уровень логирования

        # Удаляем существующие обработчики, чтобы избежать дублирования
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        print(f"Логирование настроено. Сохраняются только записи о запуске и ошибках.")
        self.logger = loggerf.logger = logger
        return logger
    
    def log_error(self, error, additional_info=None):
        """
        Логирует ошибку с дополнительной информацией и комментариями.

        Args:
            error (Exception): Объект ошибки
            additional_info (str, optional): Дополнительная информация
        """
        error_type = type(error).__name__
        error_message = str(error)

        # Добавляем комментарий к известным типам ошибок
        if error_type in ERROR_DESCRIPTIONS:
            comment = ERROR_DESCRIPTIONS[error_type]
            self.logger.error(f"{error_type}: {error_message} => {comment}")
        else:
            self.logger.error(f"{error_type}: {error_message}")

        if additional_info:
            self.logger.error(f"Дополнительная информация: {additional_info}")
    
    def info(self, message):
        """Логирование информационного сообщения о запуске"""
        # Логируем только сообщения о запуске и критичные операции
        important_keywords = ["запуск", "старт", "инициализ", "остановк", "завершен", "конфликт"]
        if any(keyword in message.lower() for keyword in important_keywords):
            self.logger.info(message)
            print(message)
    
    def warning(self, message):
        """Логирование только важных предупреждений"""
        pass
    
    def error(self, message):
        """Логирование ошибки"""
        self.logger.error(message)
        print(f"ОШИБКА: {message}")
    
    def debug(self, message):
        """Логирование отладочных сообщений отключено"""
        pass
    
    def critical(self, message):
        """Логирование критической ошибки"""
        self.logger.critical(message)
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {message}")
