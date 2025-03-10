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

def main():
    """
    Основная функция для запуска бота и веб-сервера
    """
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
        
        # Установка логирования для telegram библиотеки
        logging.getLogger('telegram').setLevel(logging.INFO)
        logging.getLogger('telegram.ext').setLevel(logging.INFO)
        
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

        print("\n=== НАЧАЛО ЗАПУСКА TELEGRAM БОТА ===\n")
        
        # Проверяем наличие токена Telegram
        if not config.telegram_token:
            logger.error("ОШИБКА: Не найден TELEGRAM_TOKEN в .env файле!")
            print("ОШИБКА: Не найден TELEGRAM_TOKEN в .env файле!")
            return
            
        logger.info(f"Используется TELEGRAM_TOKEN: {config.telegram_token[:6]}...{config.telegram_token[-4:]}")

        # Запускаем бота напрямую в основном потоке
        logger.info("Вызов метода bot.run()...")
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