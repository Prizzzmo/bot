import logging
import os
import traceback
import sys
from dotenv import load_dotenv

from src.config import Config
from src.factory import BotFactory

def main():
    """Главная функция для запуска бота"""
    try:
        # Загружаем переменные окружения из .env файла
        load_dotenv()

        # Настраиваем логирование
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)

        # Загружаем конфигурацию
        config = Config()

        # Проверяем валидность конфигурации
        if not config.validate():
            logger.error("Ошибка в конфигурации! Проверьте .env файл.")
            return

        # Создаем экземпляр бота через фабрику
        bot = BotFactory.create_bot(config)

        # Настраиваем бота
        if not bot.setup():
            logger.error("Ошибка при настройке бота!")
            return

        # Запускаем бота
        bot.run()

    except Exception as e:
        if logger:
            logger.error(f"Критическая ошибка: {e}")
            logger.error(traceback.format_exc())
        else:
            print(f"Критическая ошибка: {e}")
            print(traceback.format_exc())

if __name__ == "__main__":
    main()