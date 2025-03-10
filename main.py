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
    Основная функция для инициализации и запуска бота - оптимизированная версия
    """
    # Проверяем, не запущен ли уже бот
    if not check_running_bot():
        print("Бот уже запущен в другом процессе. Завершение работы.")
        sys.exit(1)

    # Регистрируем обработчик при завершении для гарантированной очистки
    @atexit.register
    def cleanup():
        if os.path.exists("bot.lock"):
            try:
                os.remove("bot.lock")
            except:
                pass

    # Загружаем переменные окружения из .env файла один раз
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

    # Предварительно проверяем и создаем необходимые директории
    for directory in ["logs", "generated_maps"]:
        if not os.path.exists(directory):
            os.makedirs(directory)

    # Инициализируем веб-сервер в фоновом режиме параллельно с запуском бота
    def start_web_server():
        try:
            from webapp.server import run_server
            
            # Определяем URL для веб-сервера
            repl_id = os.environ.get('REPL_ID', '')
            repl_slug = os.environ.get('REPL_SLUG', '')
            repl_owner = os.environ.get('REPL_OWNER', '')
            deployment_id = os.environ.get('REPL_DEPLOYMENT_ID', '')
            
            # Устанавливаем URL веб-сервера
            if deployment_id:
                os.environ['WEBAPP_URL'] = f"https://{deployment_id}.deployment.repl.co"
            elif repl_slug and repl_owner:
                os.environ['WEBAPP_URL'] = f"https://{repl_slug}.{repl_owner}.repl.co"
            else:
                os.environ['WEBAPP_URL'] = f"https://{repl_id}.id.repl.co"
                
            print(f"Веб-сервер запускается на порту 8080 с URL: {os.environ.get('WEBAPP_URL')}")
            run_server('0.0.0.0', 8080)
        except Exception as e:
            logger.error(f"Ошибка при запуске веб-сервера: {e}")

    # Запускаем веб-сервер в отдельном потоке
    webapp_thread = threading.Thread(target=start_web_server, daemon=True)
    webapp_thread.start()

    try:
        # Загружаем конфигурацию
        logger.info("Загрузка конфигурации")
        config = Config()

        # Проверяем валидность конфигурации
        if not config.validate():
            logger.error("Ошибка в конфигурации! Проверьте .env файл.")
            return

        # Инициализируем очередь отложенных задач заранее
        task_queue = TaskQueue(num_workers=2, logger=logger)
        task_queue.start()
        logger.info("Инициализирована система отложенных задач")
        
        # Регистрируем очередь задач в конфигурации
        config.set_task_queue(task_queue)

        # Создаем экземпляр бота через фабрику
        logger.info("Создание бота через фабрику")
        bot = BotFactory.create_bot(config)

        # Проверяем, что бот был успешно создан
        if not bot:
            logger.error("Не удалось создать экземпляр бота!")
            return

        # Проверяем необходимость миграции данных параллельно с настройкой бота
        def run_data_migration():
            try:
                data_migration = DataMigration(logger)
                if data_migration.check_and_migrate():
                    logger.info("Миграция данных успешно завершена или не требовалась")
                else:
                    logger.warning("Возникли проблемы при миграции данных, проверьте логи")
            except Exception as e:
                logger.error(f"Ошибка при миграции данных: {e}")
        
        # Запускаем миграцию данных в фоновом режиме
        migration_thread = threading.Thread(target=run_data_migration, daemon=True)
        migration_thread.start()

        # Настраиваем бота
        logger.info("Настройка бота")
        
        # Проверяем, был ли успешно инициализирован updater и настраиваем бота
        if not hasattr(bot, 'updater') or bot.updater is None:
            logger.info("Updater не инициализирован, вызываем bot.setup()")
            if not bot.setup():
                logger.error("Ошибка при настройке бота!")
                return
        
        # Регистрируем обработчик callback-запросов админ-панели
        dp = bot.updater.dispatcher
        dp.add_handler(CallbackQueryHandler(bot.handlers.admin_callback, pattern='^admin_'))

        # Проверяем наличие админ-панели в обработчиках
        if hasattr(bot.handlers, 'admin_panel'):
            logger.info("Админ-панель успешно инициализирована")
        else:
            logger.warning("Админ-панель не инициализирована")
        
        logger.info("Бот успешно настроен и готов к запуску")

        # Запускаем бота в основном потоке
        bot.run()

    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()