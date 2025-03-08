"""Контейнер сервисов для централизованного управления всеми сервисами бота"""

from typing import Dict, Any, Type, List
from src.base_service import BaseService
from src.interfaces import ILogger

class ServiceContainer:
    """
    Контейнер для управления всеми сервисами приложения.
    Реализует паттерн Service Locator для централизованного управления сервисами.
    """

    def __init__(self, logger: ILogger):
        """
        Инициализация контейнера сервисов

        Args:
            logger (ILogger): Логгер для записи информации
        """
        self._logger = logger
        self._services: Dict[str, BaseService] = {}
        self._initialized = False
        self._logger.info("Контейнер сервисов создан")

    def register(self, service_name: str, service: BaseService) -> bool:
        """
        Регистрирует сервис в контейнере

        Args:
            service_name (str): Имя сервиса для доступа к нему
            service (BaseService): Экземпляр сервиса

        Returns:
            bool: True, если сервис успешно зарегистрирован, иначе False
        """
        if service_name in self._services:
            self._logger.warning(f"Сервис с именем '{service_name}' уже зарегистрирован")
            return False

        if not isinstance(service, BaseService):
            self._logger.error(f"Объект '{service_name}' не является экземпляром BaseService")
            return False

        self._services[service_name] = service
        self._logger.debug(f"Сервис '{service_name}' успешно зарегистрирован")
        return True

    def get(self, service_name: str) -> BaseService:
        """
        Получает сервис по имени

        Args:
            service_name (str): Имя сервиса

        Returns:
            BaseService: Экземпляр сервиса или None, если сервис не найден
        """
        if service_name not in self._services:
            self._logger.warning(f"Сервис '{service_name}' не найден в контейнере")
            return None

        return self._services[service_name]

    def initialize_all(self) -> bool:
        """
        Инициализирует все зарегистрированные сервисы

        Returns:
            bool: True, если все сервисы успешно инициализированы, иначе False
        """
        if self._initialized:
            self._logger.warning("Попытка повторной инициализации контейнера сервисов")
            return True

        self._logger.info(f"Инициализация {len(self._services)} сервисов...")

        failed_services = []
        for name, service in self._services.items():
            self._logger.debug(f"Инициализация сервиса '{name}'")
            if not service.initialize():
                failed_services.append(name)
                self._logger.error(f"Ошибка инициализации сервиса '{name}'")

        if failed_services:
            self._logger.error(f"Не удалось инициализировать сервисы: {', '.join(failed_services)}")
            return False

        self._initialized = True
        self._logger.info("Все сервисы успешно инициализированы")
        return True

    def shutdown_all(self) -> bool:
        """
        Завершает работу всех сервисов

        Returns:
            bool: True, если все сервисы успешно завершены, иначе False
        """
        if not self._initialized:
            self._logger.warning("Попытка завершить работу неинициализированного контейнера сервисов")
            return True

        self._logger.info(f"Завершение работы {len(self._services)} сервисов...")

        success = True
        for name in reversed(list(self._services.keys())):  # Обратный порядок для корректного завершения зависимостей
            service = self._services[name]
            self._logger.debug(f"Завершение работы сервиса '{name}'")
            if not service.shutdown():
                self._logger.error(f"Ошибка при завершении сервиса '{name}'")
                success = False

        if success:
            self._initialized = False
            self._logger.info("Все сервисы успешно завершили работу")
        else:
            self._logger.warning("Не все сервисы корректно завершили работу")

        return success

    def get_health_report(self) -> Dict[str, Any]:
        """
        Получает отчет о состоянии всех сервисов

        Returns:
            Dict[str, Any]: Отчет о состоянии всех сервисов
        """
        health_report = {
            "container_initialized": self._initialized,
            "total_services": len(self._services),
            "services": {}
        }

        for name, service in self._services.items():
            health_report["services"][name] = service.health_check()

        return health_report

    def get_all_service_names(self) -> List[str]:
        """
        Получает список имен всех зарегистрированных сервисов

        Returns:
            List[str]: Список имен сервисов
        """
        return list(self._services.keys())

    def create_services(self):
        """
        Создает и настраивает сервисы, используемые ботом.
        Порядок важен, так как некоторые сервисы зависят от других.
        """
        # Создаем базовые сервисы

        # Инициализируем кэш (обычный или распределенный)
        use_distributed_cache = self.config.use_distributed_cache if hasattr(self.config, 'use_distributed_cache') else False

        if use_distributed_cache and hasattr(self.config, 'redis_url'):
            # Используем распределенный кэш
            try:
                from src.distributed_cache import DistributedCache
                api_cache = DistributedCache(self.logger, redis_url=self.config.redis_url)
                self.logger.info("Инициализирован распределенный кэш")
            except ImportError:
                # Если модуль не установлен, используем обычный кэш
                self.logger.warning("Модуль распределенного кэша не установлен, используется локальный кэш")
                api_cache = APICache(self.logger)
        else:
            # Используем обычный кэш
            api_cache = APICache(self.logger)

        # Инициализируем систему мониторинга производительности
        try:
            from src.performance_monitor import PerformanceMonitor
            performance_monitor = PerformanceMonitor(self.logger)
            self.logger.info("Инициализирован монитор производительности")
        except Exception as e:
            self.logger.warning(f"Не удалось инициализировать монитор производительности: {e}")
            performance_monitor = None

        # Создаем клиент API с учетом мониторинга производительности
        api_client = APIClient(self.config.gemini_api_key, api_cache, self.logger)

        # Регистрируем систему мониторинга, если она создана
        if performance_monitor:
            self.register_service('performance_monitor', performance_monitor)