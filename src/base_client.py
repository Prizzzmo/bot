
from abc import ABC, abstractmethod

class BaseAPIClient(ABC):
    """Абстрактный базовый класс для API-клиентов"""
    
    @abstractmethod
    def send_request(self, prompt, **kwargs):
        """
        Отправляет запрос к API.
        
        Args:
            prompt (str): Текст запроса
            **kwargs: Дополнительные параметры запроса
            
        Returns:
            str: Ответ от API
        """
        pass
