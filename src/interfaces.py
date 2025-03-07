
"""Интерфейсы для модулей системы"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Callable

class ILogger(ABC):
    """Интерфейс для системы логирования"""
    
    @abstractmethod
    def info(self, message: str) -> None:
        """Логирование информационного сообщения"""
        pass
        
    @abstractmethod
    def error(self, message: str) -> None:
        """Логирование сообщения об ошибке"""
        pass
        
    @abstractmethod
    def warning(self, message: str) -> None:
        """Логирование предупреждения"""
        pass
        
    @abstractmethod
    def debug(self, message: str) -> None:
        """Логирование отладочного сообщения"""
        pass
        
    @abstractmethod
    def log_error(self, error: Exception, additional_info: Optional[Dict[str, Any]] = None) -> None:
        """Логирование исключения с дополнительной информацией"""
        pass

class ICache(ABC):
    """Интерфейс для системы кэширования"""
    
    @abstractmethod
    def get(self, key: str) -> Any:
        """Получение значения из кэша"""
        pass
        
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Установка значения в кэш"""
        pass
        
    @abstractmethod
    def clear(self) -> None:
        """Очистка кэша"""
        pass
        
    @abstractmethod
    def remove(self, key: str) -> bool:
        """Удаление элемента из кэша"""
        pass
        
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики использования кэша"""
        pass

class IContentProvider(ABC):
    """Интерфейс для поставщика контента"""
    
    @abstractmethod
    def get_topic_info(self, topic: str, update_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Получение информации по исторической теме"""
        pass
        
    @abstractmethod
    def generate_test(self, topic: str) -> Dict[str, Any]:
        """Генерация теста по исторической теме"""
        pass
        
    @abstractmethod
    def validate_topic(self, topic: str) -> bool:
        """Проверка является ли тема исторической"""
        pass

class IStateManager(ABC):
    """Интерфейс для управления состоянием диалога"""
    
    @abstractmethod
    def get_user_state(self, user_id: int) -> Dict[str, Any]:
        """Получение текущего состояния пользователя"""
        pass
        
    @abstractmethod
    def set_user_state(self, user_id: int, state_data: Dict[str, Any]) -> None:
        """Установка состояния пользователя"""
        pass
        
    @abstractmethod
    def update_user_state(self, user_id: int, updates: Dict[str, Any]) -> None:
        """Обновление состояния пользователя"""
        pass
        
    @abstractmethod
    def clear_user_state(self, user_id: int) -> None:
        """Очистка состояния пользователя"""
        pass
        
    @abstractmethod
    def has_active_conversation(self, user_id: int) -> bool:
        """Проверка наличия активного диалога"""
        pass

class IUIManager(ABC):
    """Интерфейс для управления пользовательским интерфейсом"""
    
    @abstractmethod
    def get_main_menu_keyboard(self) -> Any:
        """Получение клавиатуры главного меню"""
        pass
        
    @abstractmethod
    def get_topic_keyboard(self, topics: List[str]) -> Any:
        """Получение клавиатуры для выбора темы"""
        pass
        
    @abstractmethod
    def get_test_keyboard(self) -> Any:
        """Получение клавиатуры для теста"""
        pass
        
    @abstractmethod
    def get_admin_keyboard(self) -> Any:
        """Получение клавиатуры администратора"""
        pass

class IAdminPanel(ABC):
    """Интерфейс для административной панели"""
    
    @abstractmethod
    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        pass
        
    @abstractmethod
    def is_super_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь суперадминистратором"""
        pass
        
    @abstractmethod
    def add_admin(self, user_id: int) -> bool:
        """Добавление пользователя в администраторы"""
        pass
        
    @abstractmethod
    def remove_admin(self, user_id: int) -> bool:
        """Удаление пользователя из администраторов"""
        pass
        
    @abstractmethod
    def get_bot_stats(self) -> Dict[str, Any]:
        """Получение статистики бота"""
        pass
