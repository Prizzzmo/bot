
"""
Главный модуль для запуска образовательного Telegram бота по истории России.

Этот модуль инициализирует всю экосистему приложения, включая:
- Настройку логирования
- Загрузку конфигурации из .env файла
- Создание и запуск бота через фабрику
- Обработку исключений и корректное завершение работы
"""

import logging
import traceback
import sys
from dotenv import load_dotenv

from src.config import Config
from src.factory import BotFactory

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

        # Настраиваем базовое логирование для начального этапа запуска
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)
        logger.info("Запуск историчеcкого образовательного бота")

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

        # Запускаем бота
        logger.info("Запуск бота")
        bot.run()

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
