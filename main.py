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
from telegram.ext import CallbackQueryHandler # Added import

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

def setup_logger():
    """
    Настраивает логгер.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def main():
    """
    Основная функция для инициализации и запуска бота
    """
    # Настройка логгера
    logger = setup_logger()
    logger.info("Запуск программы")

    # Загружаем конфигурацию
    config = Config()

    # Создаем фабрику с использованием переданного логгера
    factory = BotFactory(logger)

    # Создаем бота и все необходимые сервисы
    bot = BotFactory.create_bot(config)

    # Проверяем наличие админ-панели в обработчиках
    if hasattr(bot.handlers, 'admin_panel'):
        logger.info("Админ-панель успешно инициализирована")
    else:
        logger.warning("Админ-панель не инициализирована")

    try:
        # Запускаем бота
        bot.run()
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запуске бота: {e}")
        raise


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

        # Создаем экземпляр бота через фабрику
        logger.info("Создание бота через фабрику")
        bot = BotFactory.create_bot(config)
        import handlers # Added import

        # Проверяем, что бот был успешно создан
        if not bot:
            logger.error("Не удалось создать экземпляр бота!")
            return

        # Настраиваем бота
        logger.info("Настройка бота")
        # Убеждаемся, что обработчик callback-запросов админ-панели правильно зарегистрирован
        # Это нужно сделать явно, даже если setup() содержит подобную логику
        dp = bot.updater.dispatcher
        dp.add_handler(CallbackQueryHandler(handlers.admin_callback, pattern='^admin_'))

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

if __name__ == "__main__":
    main()