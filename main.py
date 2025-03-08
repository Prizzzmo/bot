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
from dotenv import load_dotenv

from src.config import Config
from src.factory import BotFactory
from src.data_migration import DataMigration
from src.task_queue import TaskQueue

def main():
    """
    Главная функция для инициализации и запуска бота.

    Выполняет следующие шаги:
    1. Загружает переменные окружения
    2. Настраивает базовое логирование
    3. Инициализирует конфигурацию
    4. Создает экземпляр бота с помощью фабрики
    5. Настраивает и запускает бота
    """
    logger = None

    try:
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

        # Настраиваем бота
        logger.info("Настройка бота")
        if not bot.setup():
            logger.error("Ошибка при настройке бота!")
            return

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
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        if logger:
            logger.error(f"Критическая ошибка: {e}")
            logger.error(traceback.format_exc())
        else:
            print(f"Критическая ошибка: {e}")
            print(traceback.format_exc())

        # Завершаем процесс с кодом ошибки
        sys.exit(1)

if __name__ == "__main__":
    main()