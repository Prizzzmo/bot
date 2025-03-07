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
    import psutil
    import os
    import time
    import signal

    print("Проверка других запущенных экземпляров бота...")
    current_pid = os.getpid()

    # Ищем процессы Python с main.py в командной строке
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Пропускаем текущий процесс
            if proc.info['pid'] == current_pid:
                continue

            cmdline = proc.info.get('cmdline', [])
            if not cmdline:
                continue

            # Проверяем, запущен ли это наш бот
            is_bot = False
            for cmd in cmdline:
                if 'python' in cmd.lower() and 'main.py' in cmdline:
                    is_bot = True
                    break

            if is_bot:
                print(f"Найден другой экземпляр бота (PID: {proc.info['pid']}). Завершение...")
                try:
                    os.kill(proc.info['pid'], signal.SIGTERM)
                    # Ждем немного, чтобы процесс успел завершиться
                    time.sleep(1)
                except Exception as e:
                    print(f"Ошибка при завершении процесса: {e}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    print("Проверка завершена, запуск нового экземпляра...")


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


if __name__ == '__main__':
    # Проверяем и завершаем другие экземпляры бота перед запуском
    check_running_instances()

    bot_manager = BotManager() # Initialize BotManager here
    bot_manager.run()