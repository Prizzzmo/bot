
from src.api_client import APIClient
from src.api_cache import APICache
from src.logger import Logger
from src.content_service import ContentService
from src.ui_manager import UIManager
from src.message_manager import MessageManager
from src.state_manager import StateManager
from src.admin_panel import AdminPanel
from src.handlers import CommandHandlers
from src.bot import Bot

class BotFactory:
    """Фабрика для создания объектов бота"""
    
    @staticmethod
    def create_bot(config):
        """Создает экземпляр бота и все необходимые компоненты"""
        # Создаем логгер
        logger = Logger()
        
        # Создаем кэш для API
        api_cache = APICache(logger, max_size=100, cache_file='api_cache.json')
        
        # Создаем API-клиент
        api_client = APIClient(config.gemini_api_key, api_cache, logger)
        
        # Создаем менеджер сообщений
        message_manager = MessageManager(logger)
        
        # Создаем UI-менеджер
        ui_manager = UIManager(logger)
        
        # Создаем сервис контента
        content_service = ContentService(api_client, logger)
        
        # Создаем обработчик команд
        command_handlers = CommandHandlers(ui_manager, api_client, message_manager, content_service, logger, config)
        
        # Создаем бота
        bot = Bot(config, logger, command_handlers)
        
        # Создаем админ-панель
        admin_panel = AdminPanel(logger, config)
        command_handlers.admin_panel = admin_panel
        
        return bot
