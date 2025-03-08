
"""Базовый класс для всех сервисов бота"""

from abc import ABC, abstractmethod
from src.interfaces import ILogger

class BaseService(ABC):
    """
    Абстрактный базовый класс, определяющий общий функционал 
    для всех сервисов в системе
    """
    
    def __init__(self, logger: ILogger):
        """
        Инициализация базового класса сервиса
        
        Args:
            logger (ILogger): Логгер для записи информации о работе сервиса
        """
        self._logger = logger
        self._initialized = False
        self._logger.debug(f"Сервис {self.__class__.__name__} создан")
    
    def initialize(self) -> bool:
        """
        Инициализирует сервис. Вызывает _do_initialize() и записывает результат.
        
        Returns:
            bool: True если инициализация прошла успешно, иначе False
        """
        try:
            result = self._do_initialize()
            self._initialized = result
            if result:
                self._logger.info(f"Сервис {self.__class__.__name__} успешно инициализирован")
            else:
                self._logger.warning(f"Сервис {self.__class__.__name__} не удалось инициализировать")
            return result
        except Exception as e:
            self._logger.log_error(e, f"Ошибка при инициализации сервиса {self.__class__.__name__}")
            self._initialized = False
            return False
    
    @abstractmethod
    def _do_initialize(self) -> bool:
        """
        Выполняет фактическую инициализацию сервиса.
        Должен быть переопределен в дочерних классах.
        
        Returns:
            bool: True если инициализация прошла успешно, иначе False
        """
        pass
    
    def is_initialized(self) -> bool:
        """
        Проверяет, инициализирован ли сервис
        
        Returns:
            bool: True если сервис инициализирован, иначе False
        """
        return self._initialized
    
    def shutdown(self) -> bool:
        """
        Завершает работу сервиса. Вызывает _do_shutdown() и записывает результат.
        
        Returns:
            bool: True если завершение прошло успешно, иначе False
        """
        if not self._initialized:
            self._logger.debug(f"Сервис {self.__class__.__name__} не был инициализирован, нечего завершать")
            return True
            
        try:
            result = self._do_shutdown()
            if result:
                self._logger.info(f"Сервис {self.__class__.__name__} успешно завершил работу")
                self._initialized = False
            else:
                self._logger.warning(f"Сервис {self.__class__.__name__} не удалось корректно завершить")
            return result
        except Exception as e:
            self._logger.log_error(e, f"Ошибка при завершении сервиса {self.__class__.__name__}")
            return False
    
    def _do_shutdown(self) -> bool:
        """
        Выполняет фактическое завершение работы сервиса.
        Может быть переопределен в дочерних классах.
        
        Returns:
            bool: True если завершение прошло успешно, иначе False
        """
        return True
    
    def health_check(self) -> dict:
        """
        Проверяет состояние здоровья сервиса
        
        Returns:
            dict: Словарь с информацией о состоянии сервиса
        """
        health_info = {
            "service": self.__class__.__name__,
            "initialized": self._initialized,
            "status": "healthy" if self._initialized else "not_initialized"
        }
        
        # Добавляем дополнительную информацию о здоровье, если она есть
        additional_health = self._get_health_info()
        if additional_health:
            health_info.update(additional_health)
            
        return health_info
    
    def _get_health_info(self) -> dict:
        """
        Получает дополнительную информацию о состоянии сервиса.
        Может быть переопределен в дочерних классах.
        
        Returns:
            dict: Словарь с дополнительной информацией о состоянии сервиса
        """
        return {}
