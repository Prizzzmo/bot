
import os
import threading
import json
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ChatAction
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, ConversationHandler, CallbackContext

from src.handlers import Handler
from src.service_container import ServiceContainer
from src.factory import BotFactory
from src.config import Config, TOPIC, CHOOSE_TOPIC, CONVERSATION, TEST, ANSWER, MAP, ANALYTICS, ADMIN
from src.logger import BotLogger
from src.interfaces import IBot, ILogger


class Bot(IBot):
    """
    Основной класс бота, реализующий основные функции взаимодействия с Telegram API.
    """

    def __init__(self, config: Config, handlers: Handler, logger: ILogger, web_server=None):
        """
        Инициализация бота.

        Args:
            config (Config): Конфигурация бота
            handlers (Handler): Обработчики команд
            logger (ILogger): Логгер
            web_server: Веб-сервер для админ-панели (опционально)
        """
        self.config = config
        self.handlers = handlers
        self.logger = logger
        self.web_server = web_server
        self.updater = None
        self.is_running = False

    def setup(self) -> bool:
        """
        Настройка бота и диспетчера.

        Returns:
            bool: True, если настройка успешна
        """
        try:
            # Инициализируем бота и диспетчер
            self.updater = Updater(self.config.telegram_token, use_context=True, workers=self.config.workers)
            dp = self.updater.dispatcher

            # Создаем ConversationHandler для управления диалогом
            conv_handler = ConversationHandler(
                entry_points=[CommandHandler('start', self.handlers.start)],
                states={
                    TOPIC: [
                        CallbackQueryHandler(self.handlers.button_handler)
                    ],
                    CHOOSE_TOPIC: [
                        CallbackQueryHandler(self.handlers.button_handler, pattern='^(more_topics|custom_topic|back_to_menu)$'),
                        CallbackQueryHandler(self.handlers.choose_topic, pattern='^topic_'),
                        MessageHandler(Filters.text & ~Filters.command, self.handlers.handle_custom_topic)
                    ],
                    TEST: [
                        CallbackQueryHandler(self.handlers.button_handler)
                    ],
                    ANSWER: [
                        MessageHandler(Filters.text & ~Filters.command, self.handlers.handle_answer),
                        CallbackQueryHandler(self.handlers.button_handler)
                    ],
                    CONVERSATION: [
                        MessageHandler(Filters.text & ~Filters.command, self.handlers.handle_conversation),
                        CallbackQueryHandler(self.handlers.button_handler)
                    ],
                    MAP: [
                        CallbackQueryHandler(self.handlers.map_handler, pattern='^map_'),
                        CallbackQueryHandler(self.handlers.button_handler, pattern='^back_to_menu$'),
                        MessageHandler(Filters.text & ~Filters.command, self.handlers.handle_map_topic)
                    ],
                    ANALYTICS: [
                        CallbackQueryHandler(self.handlers.analytics_handler, pattern='^analytics_'),
                        CallbackQueryHandler(self.handlers.button_handler, pattern='^back_to_menu$')
                    ],
                    ADMIN: [
                        MessageHandler(Filters.text & ~Filters.command, self.handlers.handle_admin_input),
                        CallbackQueryHandler(self.handlers.admin_callback_handler, pattern='^admin_')
                    ]
                },
                fallbacks=[CommandHandler('start', self.handlers.start)],
                allow_reentry=True
            )

            # Добавляем обработчики
            dp.add_handler(CommandHandler('admin', self.handlers.admin_command))
            dp.add_handler(CommandHandler('help', self.handlers.help_command))
            dp.add_handler(CommandHandler('stats', self.handlers.stats_command))
            dp.add_handler(CommandHandler('info', self.handlers.info_command))
            dp.add_handler(CommandHandler('clear', self.handlers.clear_command))
            dp.add_handler(conv_handler)
            dp.add_error_handler(self.handlers.error_handler)

            # Запускаем веб-сервер для админ-панели в отдельном потоке
            if self.web_server:
                web_thread = threading.Thread(target=self.web_server.run, daemon=True)
                web_thread.start()
                self.logger.info("Веб-сервер для админ-панели запущен")

            return True
        except Exception as e:
            self.logger.log_error(e, "Ошибка при настройке бота")
            return False

    def start(self, use_webhook: bool = False, webhook_url: str = "", port: int = 8443) -> bool:
        """
        Запуск бота.

        Args:
            use_webhook (bool): Использовать webhook вместо поллинга
            webhook_url (str): URL для webhook
            port (int): Порт для webhook

        Returns:
            bool: True, если запуск успешен
        """
        try:
            if use_webhook and webhook_url:
                # Настраиваем webhook
                self.updater.start_webhook(
                    listen="0.0.0.0",
                    port=port,
                    url_path=self.config.telegram_token,
                    webhook_url=webhook_url + self.config.telegram_token
                )
                self.logger.info(f"Бот запущен в режиме webhook на {webhook_url}")
            else:
                # Запускаем бота в режиме поллинга
                self.updater.start_polling()
                self.logger.info("Бот запущен в режиме поллинга")

            # Устанавливаем флаг запуска
            self.is_running = True

            # Сохраняем информацию о запуске
            self._update_startup_info()

            # Блокируем выполнение до остановки бота
            self.updater.idle()

            return True
        except Exception as e:
            self.logger.log_error(e, "Ошибка при запуске бота")
            return False

    def stop(self) -> bool:
        """
        Остановка бота.

        Returns:
            bool: True, если остановка успешна
        """
        try:
            if self.updater:
                self.updater.stop()
                self.is_running = False
                self.logger.info("Бот остановлен")
                return True
            return False
        except Exception as e:
            self.logger.log_error(e, "Ошибка при остановке бота")
            return False

    def _update_startup_info(self) -> None:
        """
        Обновляет информацию о запуске бота.
        """
        try:
            current_time = int(time.time())
            startup_info = {
                "last_startup": current_time,
                "startup_count": 0,
                "version": self.config.version
            }

            # Загружаем существующую информацию, если она есть
            if os.path.exists('bot_settings.json'):
                with open('bot_settings.json', 'r', encoding='utf-8') as f:
                    try:
                        existing_info = json.load(f)
                        if "startup_count" in existing_info:
                            startup_info["startup_count"] = existing_info["startup_count"] + 1
                    except json.JSONDecodeError:
                        pass

            # Сохраняем обновленную информацию
            with open('bot_settings.json', 'w', encoding='utf-8') as f:
                json.dump(startup_info, f, indent=2)

        except Exception as e:
            self.logger.error(f"Ошибка при обновлении информации о запуске: {e}")


class BotManager:
    """
    Менеджер для управления ботом и его зависимостями.
    """

    def __init__(self, config_path: str = None):
        """
        Инициализация менеджера бота.

        Args:
            config_path (str, optional): Путь к файлу конфигурации
        """
        # Инициализируем логгер
        self.logger = BotLogger("bot.log", "INFO")
        self.logger.info("Запуск историчеcкого образовательного бота")

        # Загружаем конфигурацию
        self.logger.info("Загрузка конфигурации")
        self.config = Config.load_from_env()

        # Создаем фабрику ботов
        self.factory = BotFactory()

        # Создаем контейнер сервисов
        self.services = ServiceContainer(self.logger)

        # Бот будет создан в методе initialize
        self.bot = None

    def initialize(self) -> bool:
        """
        Инициализация бота и всех зависимостей.

        Returns:
            bool: True, если инициализация успешна
        """
        try:
            # Создаем экземпляр бота через фабрику
            self.logger.info("Создание бота через фабрику")
            self.bot = self.factory.create_bot(self.config, self.services, self.logger)

            # Настраиваем бота
            self.logger.info("Настройка бота")
            if not self.bot.setup():
                self.logger.error("Не удалось настроить бота")
                return False

            self.logger.info("Бот успешно настроен и готов к запуску")

            # Выполняем миграцию данных, если необходимо
            self._run_data_migration()

            return True
        except Exception as e:
            self.logger.log_error(e, "Ошибка при инициализации бота")
            return False

    def start(self, use_webhook: bool = False, webhook_url: str = "", port: int = 8443) -> bool:
        """
        Запуск бота.

        Args:
            use_webhook (bool): Использовать webhook вместо поллинга
            webhook_url (str): URL для webhook
            port (int): Порт для webhook

        Returns:
            bool: True, если запуск успешен
        """
        if not self.bot:
            self.logger.error("Бот не инициализирован")
            return False

        return self.bot.start(use_webhook, webhook_url, port)

    def _run_data_migration(self) -> None:
        """
        Выполняет миграцию данных, если необходима.
        """
        try:
            # Проверяем необходимость миграции данных
            current_version = 0
            target_version = 2  # Текущая версия схемы данных

            # Загружаем информацию о текущей версии данных
            if os.path.exists('data_version.json'):
                with open('data_version.json', 'r', encoding='utf-8') as f:
                    try:
                        version_info = json.load(f)
                        current_version = version_info.get("version", 0)
                    except json.JSONDecodeError:
                        pass

            self.logger.info(f"Текущая версия данных: {current_version}")

            # Если текущая версия меньше целевой, выполняем миграцию
            if current_version < target_version:
                self.logger.info(f"Требуется миграция данных с версии {current_version} до версии {target_version}")

                # Здесь код миграции данных...
                # Для демонстрации просто обновляем версию

                # Сохраняем обновленную версию
                with open('data_version.json', 'w', encoding='utf-8') as f:
                    json.dump({"version": target_version}, f, indent=2)

                self.logger.info(f"Миграция данных успешно выполнена до версии {target_version}")
            else:
                self.logger.info("Миграция не требуется, данные в актуальном состоянии")

            # Запускаем системы, требующие инициализации после миграции
            self._initialize_systems()

            self.logger.info("Миграция данных успешно завершена или не требовалась")
        except Exception as e:
            self.logger.log_error(e, "Ошибка при миграции данных")

    def _initialize_systems(self) -> None:
        """
        Инициализирует дополнительные системы после загрузки данных.
        """
        try:
            # Инициализируем очередь задач
            task_queue = self.services.get_task_queue()
            if task_queue:
                worker_count = self.config.worker_threads
                task_queue.start_workers(worker_count)
                self.logger.info(f"Запущена очередь задач с {worker_count} рабочими потоками")

            # Инициализируем систему отложенных задач
            if hasattr(self.services, 'initialize_scheduler'):
                self.services.initialize_scheduler()
                self.logger.info("Инициализирована система отложенных задач")
        except Exception as e:
            self.logger.log_error(e, "Ошибка при инициализации систем")

# Изменено приветственное сообщение для отображения при команде /start
WELCOME_MESSAGE = """
👋 *Добро пожаловать в образовательного бота по истории России!*

Я помогу вам изучить ключевые события, личности и периоды российской истории в интерактивном формате.

*Возможности бота:*
• 📚 Изучение исторических тем в структурированной форме
• 🧠 Проверка знаний через тестирование
• 🗣️ Ответы на вопросы по истории России
• 🗺️ Интерактивные исторические карты и визуализации

_Выберите нужный раздел в меню ниже:_
"""
