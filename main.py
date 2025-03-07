import os
from src.config import Config
from src.logger import Logger
from src.api_cache import APICache
from src.api_client import APIClient
from src.message_manager import MessageManager
from src.ui_manager import UIManager
from src.content_service import ContentService
from src.handlers import CommandHandlers
from src.bot import Bot, BotManager


def check_running_instances():
    """Checks for other running instances of the bot and terminates them."""
    # Implement logic to check for and terminate other instances.  This is placeholder code.
    # Replace with actual implementation using process IDs, file locks, or other methods.
    print("Checking for other running instances...")
    # ... (Implementation to check and terminate other instances) ...
    pass


def main():
    """
    Основная функция для инициализации и запуска бота.
    """
    logger = None
    try:
        # Инициализируем логгер
        logger = Logger()
        logger.info("Запуск бота истории России...")

        # Инициализируем конфигурацию
        config = Config()

        # Проверяем наличие необходимых токенов
        try:
            config.validate()
        except ValueError as e:
            logger.error(str(e))
            print(f"ОШИБКА: {e}")
            return

        # Инициализируем кэш API и клиент API
        api_cache = APICache(logger, max_size=200, save_interval=10)
        api_client = APIClient(config.gemini_api_key, api_cache, logger)

        # Создаем менеджеры и сервисы
        message_manager = MessageManager(logger)
        ui_manager = UIManager(logger)
        content_service = ContentService(api_client, logger)

        # Создаем обработчики команд
        command_handlers = CommandHandlers(
            ui_manager=ui_manager,
            api_client=api_client,
            message_manager=message_manager,
            content_service=content_service,
            logger=logger,
            config=config
        )

        # Инициализируем и запускаем бота
        bot = Bot(config, logger, command_handlers)
        if bot.setup():
            bot.run()
        else:
            logger.error("Не удалось настроить бота")

    except Exception as e:
        if logger:
            logger.log_error(e, "Критическая ошибка при запуске бота")
            logger.critical(f"Бот не был запущен из-за критической ошибки: {e}")

if __name__ == '__main__':
    # Проверяем и завершаем другие экземпляры бота перед запуском
    check_running_instances()
    
    # Напрямую вызываем main(), так как BotManager просто вызывает его
    main()