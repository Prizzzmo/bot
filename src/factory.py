"""Фабрика для создания компонентов бота"""

from typing import Dict, Any

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
from src.analytics import AnalyticsService
from src.web_server import WebServer
from src.test_service import TestService
from src.topic_service import TopicService
from src.conversation_service import ConversationService #Added import
from src.text_cache_service import TextCacheService
from src.data_migration import DataMigration # Added import


class BotFactory:
    """
    Фабрика для создания объектов бота.
    Реализует паттерн Factory для создания и инициализации компонентов системы.
    """

    def __init__(self, logger):
        self.logger = logger

    def create_api_cache(self):
        """Создание кэша для API запросов"""
        from src.api_cache import APICache
        return APICache(self.logger, max_size=1000, cache_file='api_cache.json')

    def create_text_cache_service(self):
        """Создание сервиса кэширования текстов"""
        from src.text_cache_service import TextCacheService
        return TextCacheService(self.logger, cache_file='texts_cache.json', ttl=604800)  # TTL = 7 дней

    @staticmethod
    def create_bot(config):
        """
        Создает экземпляр бота и все необходимые компоненты.

        Args:
            config: Конфигурация приложения

        Returns:
            Bot: Настроенный экземпляр бота
        """
        # Создаем логгер
        logger = Logger()
        logger.info("Инициализация компонентов бота")

        # Создаем фабрику и контейнер сервисов
        factory = BotFactory(logger)

        # Импортируем здесь, чтобы избежать циклических импортов
        from src.service_container import ServiceContainer
        container = ServiceContainer(logger)

        # Создаем и регистрируем все сервисы

        # Кэш для API
        api_cache = factory.create_api_cache()

        # API-клиент
        api_client = APIClient(config.gemini_api_key, api_cache, logger)
        container.register("api_client", api_client)

        # Менеджер состояний
        state_manager = StateManager(logger)
        container.register("state_manager", state_manager)

        # Менеджер сообщений
        message_manager = MessageManager(logger)
        container.register("message_manager", message_manager)

        # Сервис для кэширования текстов
        text_cache_service = factory.create_text_cache_service()
        container.register("text_cache_service", text_cache_service)

        # Сервисы для тестов и тем
        test_service = TestService(api_client, logger)
        container.register("test_service", test_service)

        topic_service = TopicService(api_client, logger)
        container.register("topic_service", topic_service)

        # UI-менеджер
        ui_manager = UIManager(logger, topic_service)
        container.register("ui_manager", ui_manager)

        # Сервис контента
        content_service = ContentService(api_client, logger, 'historical_events.json', text_cache_service)
        container.register("content_service", content_service)

        # Аналитический сервис
        analytics_service = AnalyticsService(logger)
        container.register("analytics_service", analytics_service)

        # Админ-панель
        admin_panel = AdminPanel(logger, config)

        # Обработчик команд
        command_handlers = CommandHandlers(
            ui_manager=ui_manager,
            api_client=api_client,
            message_manager=message_manager,
            content_service=content_service,
            logger=logger,
            config=config
        )
        command_handlers.admin_panel = admin_panel

        # Веб-сервер
        web_server = WebServer(
            logger=logger,
            analytics_service=analytics_service,
            admin_panel=admin_panel
        )
        container.register("web_server", web_server)

        #Data Migration Initialization
        data_migration = DataMigration(logger) # Use default data directory
        container.register("data_migration", data_migration)

        # Инициализируем все сервисы
        logger.info("Инициализация всех сервисов...")
        container.initialize_all()

        # Создаем бота
        bot = Bot(
            config=config,
            logger=logger,
            command_handlers=command_handlers,
            test_service=test_service,
            topic_service=topic_service,
            api_client=api_client,
            analytics=analytics_service,
            text_cache_service=text_cache_service
        )

        # Сохраняем ссылку на контейнер сервисов в боте
        bot.service_container = container

        logger.info("Все компоненты бота инициализированы успешно")

        return bot