"""
Главный модуль для запуска образовательного Telegram бота по истории России.

Этот модуль инициализирует всю экосистему приложения, включая:
- Настройку логирования
- Загрузку конфигурации из .env файла
- Создание и запуск бота через фабрику
- Обработку исключений и корректное завершение работы
"""

import logging
import os
import traceback
import sys
import atexit
from dotenv import load_dotenv
import threading

from src.config import Config
from src.factory import BotFactory
from src.data_migration import DataMigration
from src.task_queue import TaskQueue

def check_running_bot():
    """
    Проверяет, не запущен ли уже экземпляр бота.
    Создает и проверяет lock-файл.

    Returns:
        bool: True если можно запускать бота, False если уже запущен
    """
    import os
    import sys

    lock_file = "bot.lock"

    # Проверяем существование lock-файла
    if os.path.exists(lock_file):
        try:
            # Читаем PID из lock-файла
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())

            # Проверяем, существует ли процесс с таким PID
            # Для Linux
            if os.path.exists(f"/proc/{pid}"):
                return False

            # Если процесс не существует, удаляем устаревший lock-файл
            os.remove(lock_file)
        except (IOError, ValueError):
            # Если файл поврежден или не содержит PID, удаляем его
            os.remove(lock_file)

    # Создаем новый lock-файл с текущим PID
    with open(lock_file, 'w') as f:
        f.write(str(os.getpid()))

    return True

def start_bot(config, logger):
    """Creates and runs the bot."""
    logger.info("Создание бота через фабрику")
    bot = BotFactory.create_bot(config)

    # Проверяем, что бот был успешно создан
    if not bot:
        logger.error("Не удалось создать экземпляр бота!")
        return

    # Настраиваем бота
    logger.info("Настройка бота")
    if not bot.setup():
        logger.error("Ошибка при настройке бота!")
        return

    logger.info("Бот успешно настроен и готов к запуску")

    # Проверяем необходимость миграции данных
    data_migration = DataMigration(logger)
    if data_migration.check_and_migrate():
        logger.info("Миграция данных успешно завершена или не требовалась")
    else:
        logger.warning("Возникли проблемы при миграции данных, проверьте логи")

    # Инициализируем очередь отложенных задач
    task_queue = TaskQueue(num_workers=2, logger=logger)
    task_queue.start()
    logger.info("Инициализирована система отложенных задач")

    # Регистрируем очередь задач в конфигурации для доступа из других модулей
    config.set_task_queue(task_queue)

    # Запускаем бота напрямую в основном потоке
    bot.run()


def start_admin_panel():
    """Запускает админ-панель в отдельном потоке"""
    from webapp.admin_server import run_admin_server
    import threading

    # Запускаем админ-сервер в отдельном потоке
    admin_thread = threading.Thread(target=run_admin_server, kwargs={'host': '0.0.0.0', 'port': 8000})
    admin_thread.daemon = True
    admin_thread.start()
    logging.info("Сервер админ-панели запущен на порту 8000")

def main():
    """
    Основная функция для запуска бота и веб-сервера
    """
    # Запуск веб-сервера в отдельном потоке
    import threading
    from webapp.server import run_server

    # Устанавливаем переменную окружения для вебсервера
    repl_id = os.environ.get('REPL_ID', '')
    repl_slug = os.environ.get('REPL_SLUG', '')
    repl_owner = os.environ.get('REPL_OWNER', '')
    deployment_id = os.environ.get('REPL_DEPLOYMENT_ID', '')

    # Сохраняем URL в переменной окружения для использования в bot_integration.py
    if deployment_id:
        os.environ['WEBAPP_URL'] = f"https://{deployment_id}.deployment.repl.co"
    elif repl_slug and repl_owner:
        os.environ['WEBAPP_URL'] = f"https://{repl_slug}.{repl_owner}.repl.co"
    else:
        os.environ['WEBAPP_URL'] = f"https://{repl_id}.id.repl.co"

    # Запускаем веб-сервер
    webapp_thread = threading.Thread(target=run_server, args=('0.0.0.0', 8080), daemon=True)
    webapp_thread.start()
    print(f"Веб-сервер запущен на порту 8080 с URL: {os.environ.get('WEBAPP_URL')}")

    logger = None

    try:
        # Проверяем, не запущен ли уже бот
        if not check_running_bot():
            print("Бот уже запущен в другом процессе. Завершение работы.")
            sys.exit(1)

        # Загружаем переменные окружения из .env файла
        load_dotenv()

        # Настраиваем базовое логирование с оптимизированными параметрами
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)
        logger.info("Запуск историчеcкого образовательного бота")

        # Предварительно проверяем наличие всех необходимых директорий
        # для предотвращения ошибок при параллельной работе
        for directory in ["logs", "generated_maps"]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        # Загружаем конфигурацию
        logger.info("Загрузка конфигурации")
        config = Config()

        # Проверяем валидность конфигурации
        if not config.validate():
            logger.error("Ошибка в конфигурации! Проверьте .env файл.")
            return

        start_admin_panel()
        start_bot(config, logger)


    except KeyboardInterrupt:
        if logger:
            logger.info("Бот остановлен пользователем")
        # Удаляем lock-файл при завершении работы
        if os.path.exists("bot.lock"):
            os.remove("bot.lock")
    except Exception as e:
        if logger:
            logger.error(f"Критическая ошибка: {e}")
            logger.error(traceback.format_exc())
        else:
            print(f"Критическая ошибка: {e}")
            print(traceback.format_exc())

        # Удаляем lock-файл при завершении работы с ошибкой
        if os.path.exists("bot.lock"):
            os.remove("bot.lock")

        # Завершаем процесс с кодом ошибки
        sys.exit(1)
    finally:
        # Гарантированное удаление lock-файла в любом случае
        if os.path.exists("bot.lock"):
            os.remove("bot.lock")

def clear_caches():
    """Очищает все кэши при запуске проекта"""
    from src.logger import Logger
    from src.config import Config
    
    logger = Logger()
    config = Config()
    
    # Проверяем, включена ли автоматическая очистка кэша
    if not hasattr(config, 'clear_cache_on_startup') or not config.clear_cache_on_startup:
        logger.info("Автоматическая очистка кэша при запуске отключена в конфигурации")
        return
    
    try:
        # Очистка API кэша
        from src.api_cache import APICache
        api_cache = APICache(logger)
        cleared_items = api_cache.clear_cache()
        logger.info(f"При запуске проекта очищено {cleared_items} записей из API кэша")
        
        # Очистка распределенного кэша, если он используется
        try:
            from src.distributed_cache import DistributedCache
            distributed_cache = DistributedCache(logger)
            cleared_distributed = distributed_cache.clear_cache()
            logger.info(f"При запуске проекта очищено {cleared_distributed} записей из распределенного кэша")
        except Exception as e:
            logger.debug(f"Распределенный кэш не используется или произошла ошибка: {e}")
        
        # Очистка текстового кэша, если он используется
        try:
            from src.text_cache_service import TextCacheService
            text_cache = TextCacheService(logger)
            cleared_text = text_cache.clear_cache()
            logger.info(f"При запуске проекта очищено {cleared_text} записей из текстового кэша")
        except Exception as e:
            logger.debug(f"Текстовый кэш не используется или произошла ошибка: {e}")
            
        logger.info("Автоматическая очистка кэша при запуске успешно выполнена")
    except Exception as e:
        logger.error(f"Ошибка при автоматической очистке кэша при запуске: {e}")

if __name__ == "__main__":
    # Очистка кэшей при запуске
    clear_caches()
    # Запуск основного приложения
    main()