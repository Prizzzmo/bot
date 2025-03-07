
from abc import ABC, abstractmethod

class ILogger(ABC):
    """Интерфейс для системы логирования"""
    
    @abstractmethod
    def info(self, message):
        pass
        
    @abstractmethod
    def error(self, message):
        pass
        
    @abstractmethod
    def warning(self, message):
        pass
        
    @abstractmethod
    def debug(self, message):
        pass
        
    @abstractmethod
    def log_error(self, error, additional_info=None):
        pass

class ICache(ABC):
    """Интерфейс для системы кэширования"""
    
    @abstractmethod
    def get(self, key):
        pass
        
    @abstractmethod
    def set(self, key, value, ttl=None):
        pass
        
    @abstractmethod
    def clear(self):
        pass

class IContentProvider(ABC):
    """Интерфейс для поставщика контента"""
    
    @abstractmethod
    def get_topic_info(self, topic, update_callback=None):
        pass
        
    @abstractmethod
    def generate_test(self, topic):
        pass
