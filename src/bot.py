import threading
import time
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
import logging
import logging.handlers
import os

from src.config import TOPIC, CHOOSE_TOPIC, TEST, ANSWER, CONVERSATION

class Bot:
    """Класс для управления Telegram ботом"""

    def __init__(self, config, logger, command_handlers, test_service=None, topic_service=None, 
              api_client=None, analytics=None, text_cache_service=None):
        self.config = config
        self.logger = logger
        self.handlers = command_handlers
        self.updater = None
        self.test_service = test_service
        self.topic_service = topic_service

        # Сервисы бота
        self.api_client = api_client
        self.analytics = analytics
        self.text_cache_service = text_cache_service

        # Контейнер сервисов, будет установлен из фабрики
        self.service_container = None

    def setup(self):
        """
        Настраивает бота, инициализирует обработчики команд и сообщений.
        Возвращает True, если настройка успешна, иначе False.
        """
        try:
            # Инициализируем компоненты бота
            if not self._initialize_components():
                return False

            # Создаем и сохраняем Updater
            self._setup_updater()
            
            # Логгер уже настроен при инициализации
            self.logger.info("Настройка бота завершена успешно")
            return True
        except Exception as e:
            self.logger.log_error(e, "Ошибка при настройке бота")
            return False

    def run(self):
        """Запускает бота"""
        self.logger.info("Запуск бота...")

        try:
            # Проверка, что updater был успешно создан
            if not self.updater:
                self.logger.error("Ошибка запуска бота: updater не инициализирован")
                return

            # Проверка наличия обработчиков
            if not hasattr(self, 'handlers') or self.handlers is None:
                self.logger.error("Ошибка запуска бота: handlers не инициализированы")
                return
                
            # Инициализируем обработчики, если это не было сделано ранее
            if not hasattr(self.updater.dispatcher, 'handlers') or not self.updater.dispatcher.handlers:
                self.logger.info("Инициализируем обработчики команд...")
                self._initialize_handlers()

            # Проверка валидности токена
            import telegram
            try:
                self.logger.info("Проверка соединения с Telegram API...")
                telegram_bot = self.updater.bot
                bot_info = telegram_bot.get_me()
                self.logger.info(f"Соединение успешно, бот: @{bot_info.username}")
            except telegram.error.TelegramError as e:
                self.logger.error(f"Ошибка соединения с Telegram API: {e}")
                self.logger.error("Проверьте корректность TELEGRAM_TOKEN в .env файле")
                return

            # Проверяем, что все необходимые обработчики добавлены
            if not self.updater.dispatcher.handlers:
                self.logger.error("Обработчики не добавлены в диспетчер")
                return

            # Оптимизированные настройки для более эффективного сбора обновлений
            self.logger.info("Запуск start_polling...")
            try:
                self.updater.start_polling(
                    timeout=10,  # Таймаут для стабильной работы
                    drop_pending_updates=True,  # Пропуск накопившихся обновлений
                    allowed_updates=['message', 'callback_query', 'chat_member', 'chosen_inline_result'],  # Необходимые типы обновлений
                    poll_interval=0.5  # Интервал опроса для снижения нагрузки
                )
                self.logger.info("Бот успешно запущен")
                self.logger.info(f"Dispatcher running: {self.updater.dispatcher.running}")
            except Exception as e:
                self.logger.error(f"Ошибка при запуске polling: {e}")
                import traceback
                self.logger.error(f"Стек вызовов: {traceback.format_exc()}")
                return

            # Используем встроенный метод idle для блокировки
            try:
                self.logger.info("Входим в режим idle...")
                # Добавляем обработку сигналов
                import signal
                def signal_handler(signum, frame):
                    self.logger.info(f"Получен сигнал {signum}, останавливаем бота...")
                    self.updater.stop()
                
                # Регистрируем обработчики сигналов
                signal.signal(signal.SIGINT, signal_handler)
                signal.signal(signal.SIGTERM, signal_handler)
                
                self.updater.idle()
            except Exception as e:
                self.logger.error(f"Ошибка в idle режиме: {e}")
                import traceback
                self.logger.error(f"Стек вызовов: {traceback.format_exc()}")

            # Если idle вернул управление, значит бот завершает работу
            self.logger.info("Бот завершил работу")
        except Exception as e:
            import traceback
            self.logger.log_error(e, {"context": "bot.run()"})
            self.logger.error(f"Полный стек вызовов: {traceback.format_exc()}")
            # Попытка принудительного завершения updater если он был создан
            if hasattr(self, 'updater') and self.updater:
                try:
                    self.updater.stop()
                except Exception as stop_error:
                    self.logger.error(f"Ошибка при остановке updater: {stop_error}")

    def setup_log_rotation(self):
        log_dir = "logs"
        log_file = os.path.join(log_dir, "bot.log")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Configure logging
        self.logger.setLevel(logging.INFO)  # Set logging level
        handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5) # 10MB max file size, 5 backups
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _setup_updater(self):
        """
        Создает и настраивает Updater и Dispatcher для бота
        """
        if not hasattr(self, 'updater') or self.updater is None:
            from telegram.ext import Updater, CallbackQueryHandler
            self.updater = Updater(self.config.telegram_token, use_context=True, workers=8, request_kwargs={'read_timeout': 6, 'connect_timeout': 7})
            dp = self.updater.dispatcher

            # Регистрируем обработчик callback-запросов для админки
            if hasattr(self, 'admin_panel') and self.admin_panel:
                try:
                    dp.add_handler(CallbackQueryHandler(self.admin_panel.handle_admin_callback, pattern='^admin_'))
                    self.logger.info("Зарегистрирован обработчик админских callback-запросов")
                except Exception as e:
                    self.logger.error(f"Ошибка при регистрации обработчика админских callback-запросов: {e}")
            else:
                self.logger.warning("Админ-панель не инициализирована, обработчик не добавлен")

    def _initialize_components(self):
        """
        Инициализирует компоненты бота.
        Возвращает True, если инициализация успешна, иначе False.
        """
        return True


    def _initialize_handlers(self):
        """Инициализирует обработчики команд и сообщений"""
        if not self.updater:
            self.logger.error("Updater не инициализирован, невозможно добавить обработчики")
            return False

        try:
            from telegram.ext import CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
            from src.config import TOPIC, CHOOSE_TOPIC, TEST, ANSWER, CONVERSATION
            
            # Создаем ConversationHandler
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
                        CallbackQueryHandler(self.handlers.button_handler)  # Добавляем обработчик для кнопки завершения теста
                    ],
                    CONVERSATION: [
                        MessageHandler(Filters.text & ~Filters.command, self.handlers.handle_conversation),
                        CallbackQueryHandler(self.handlers.button_handler)  # Обработчик для кнопки возврата в меню
                    ]
                },
                fallbacks=[CommandHandler('start', self.handlers.start)],
                allow_reentry=True,
                per_message=False
            )

            # Добавляем ссылку на admin_panel в handlers, если она доступна
            if hasattr(self, 'admin_panel'):
                self.handlers.admin_panel = self.admin_panel
                self.logger.info("Admin panel подключен к handlers")
            
            # Добавляем обработчик в диспетчер
            self.updater.dispatcher.add_handler(conv_handler)
            self.logger.info("Обработчики успешно добавлены в диспетчер")
            return True
        except Exception as e:
            self.logger.log_error(e, "Ошибка при инициализации обработчиков")
            return False


class BotManager:
    """Класс для управления запуском бота и его жизненным циклом"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)


    def run(self):
        """Запускает основную функцию для инициализации и запуска бота"""
        from main import main
        main()