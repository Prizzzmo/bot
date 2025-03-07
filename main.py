import os
from src.config import Config, MAP
from src.logger import Logger
from src.api_cache import APICache
from src.api_client import APIClient
from src.message_manager import MessageManager
from src.ui_manager import UIManager
from src.content_service import ContentService
from src.handlers import CommandHandlers
from src.bot import Bot, BotManager
import fcntl

def is_bot_already_running():
    """Проверяет, запущен ли уже бот, используя механизм блокировки файла"""
    lockfile = "/tmp/history_bot.lock"
    try:
        fd = open(lockfile, 'w')
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd  # Возвращаем файловый дескриптор для сохранения блокировки
    except IOError:
        return False  # Бот уже запущен

def main():
    # Создаем экземпляр логгера
    logger = Logger()

    # Загружаем конфигурацию
    config = Config()

    # Создаем необходимые сервисы
    ui_manager = UIManager(logger)
    # Создаем кэш для API запросов
    api_cache = APICache(logger)
    api_client = APIClient(config.gemini_api_key, api_cache, logger)
    message_manager = MessageManager(logger)
    content_service = ContentService(api_client, logger)

    # Инициализируем сервис аналитики
    from src.analytics import Analytics
    analytics = Analytics(logger)

    # Создаем карту исторических событий
    from src.history_map import HistoryMap
    history_map = HistoryMap(logger)

    # Создаем и запускаем веб-сервер
    from src.web_server import MapServer
    map_server = MapServer(history_map, logger)
    map_server.run()

    # Создаем обработчик команд
    handlers = CommandHandlers(ui_manager, api_client, message_manager, content_service, logger, config)
    # Прикрепляем карту к обработчику
    handlers.history_map = history_map

    # Создаем и настраиваем бота
    bot = Bot(config, logger, handlers)
    if bot.setup():
        logger.info("Бот успешно настроен")
        bot.run()
    else:
        logger.error("Не удалось настроить бота")


if __name__ == "__main__":
    # Проверяем, запущен ли уже бот
    lock_fd = is_bot_already_running()

    if not lock_fd:
        print("Бот уже запущен! Завершение работы.")
        exit(1)

    # Инициализируем логгер
    logger = Logger()
    logger.info("Запуск бота и веб-сервера логов...")

    # Загружаем токен и API ключ
    #load_dotenv()  # Загружаем переменные окружения из .env файла  - This line is commented out because it's not in the original code and the changes don't explicitly mention it.
    config = Config()

    # Инициализируем LRU-кэш для API
    api_cache = APICache(logger)

    bot_manager = BotManager() # Initialize BotManager here
    bot_manager.run()