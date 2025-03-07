import threading
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler
import logging
import logging.handlers
import os

from src.config import TOPIC, CHOOSE_TOPIC, TEST, ANSWER, CONVERSATION
from src.config import MAP #Added import for MAP constant

class Bot:
    """Класс для управления Telegram ботом"""

    def __init__(self, config, logger, command_handlers, test_service=None, topic_service=None):
        self.config = config
        self.logger = logger
        self.handlers = command_handlers
        self.updater = None
        self.test_service = test_service
        self.topic_service = topic_service

        # Инициализируем админ-панель и привязываем её к обработчику команд
        from src.admin_panel import AdminPanel
        admin_panel = AdminPanel(logger, config)
        self.handlers.admin_panel = admin_panel

    def setup(self):
        """Настройка бота и диспетчера"""
        try:
            # Инициализируем бота и диспетчер с оптимизированными настройками
            self.updater = Updater(self.config.telegram_token, use_context=True, workers=4)  # Увеличиваем количество рабочих потоков
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
                        CallbackQueryHandler(self.handlers.button_handler)  # Добавляем обработчик для кнопки завершения теста
                    ],
                    CONVERSATION: [
                        MessageHandler(Filters.text & ~Filters.command, self.handlers.handle_conversation),
                        CallbackQueryHandler(self.handlers.button_handler)  # Обработчик для кнопки возврата в меню
                    ],
                    MAP: [
                        CallbackQueryHandler(self.handlers.button_handler)  # Обработчик для взаимодействия с картой
                    ]
                },
                fallbacks=[CommandHandler('start', self.handlers.start)],
                allow_reentry=True,
                per_message=False
            )

            # Добавляем обработчики
            dp.add_error_handler(self.handlers.error_handler)
            dp.add_handler(conv_handler)

            # Добавляем обработчик для команды администратора
            dp.add_handler(CommandHandler('admin', self.handlers.admin_command))

            # Добавляем обработчик для обработки callback запросов администратора
            dp.add_handler(CallbackQueryHandler(self.handlers.admin_callback, pattern='^admin_'))

            return True
        except Exception as e:
            self.logger.log_error(e, "Ошибка при настройке бота")
            return False

    def run(self):
        """Запускает бота"""
        self.logger.info("Запуск бота...")

        try:
            # Включаем сбор обновлений для реагирования на сообщения, запускаем бота
            # Установка более длинного таймаута для обработки конфликтов
            # Используем drop_pending_updates=True для пропуска обновлений, накопившихся во время остановки
            # Уменьшаем timeout для более быстрого обнаружения ошибок подключения
            self.updater.start_polling(timeout=10, drop_pending_updates=True, allowed_updates=['message', 'callback_query'])
            self.logger.info("Бот успешно запущен")

            # Остаемся в режиме работы до получения Ctrl+C
            self.updater.idle()
        except Exception as e:
            self.logger.error(f"Ошибка запуска бота: {e}")
            # Попытка принудительного завершения updater если он был создан
            if hasattr(self, 'updater'):
                self.updater.stop()

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