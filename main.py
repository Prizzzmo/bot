
"""
Главный модуль для запуска исторического образовательного Telegram бота.

Этот модуль инициализирует и запускает всю систему бота,
обрабатывает исключения и настраивает логирование.
"""

import logging
import os
import traceback
import sys
from dotenv import load_dotenv

from src.config import Config
from src.factory import BotFactory

def main():
    """Главная функция для запуска бота"""
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
