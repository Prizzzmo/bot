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
        """Настройка бота и диспетчера"""
        try:
            # Инициализируем бота и диспетчер с оптимизированными настройками
            # Используем 8 рабочих потоков для более эффективной параллельной обработки сообщений
            self.updater = Updater(
                self.config.telegram_token, 
                use_context=True, 
                workers=8,
                request_kwargs={'read_timeout': 6, 'connect_timeout': 7}  # Уменьшаем таймауты для более быстрого обнаружения проблем
            )
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

            # Добавляем обработчик для команды очистки чата
            dp.add_handler(CommandHandler('clear', self.handlers.clear_chat_command))
            
            # Добавляем обработчик только для латинской команды карты
            # Кириллические команды не поддерживаются Telegram API
            dp.add_handler(CommandHandler('map', self.handlers.map_command))
            
            # Добавляем обработчик текстовых сообщений, который будет проверять текст "/карта"
            dp.add_handler(MessageHandler(Filters.regex(r'^/карта$'), self.handlers.map_command))

            # Добавляем обработчик для обработки callback запросов администратора
            dp.add_handler(CallbackQueryHandler(self.handlers.admin_callback, pattern='^admin_'))

            # Добавляем контекстные данные для бота
            self.updater.dispatcher.bot_data['api_client'] = self.api_client
            self.updater.dispatcher.bot_data['analytics'] = self.analytics
            self.updater.dispatcher.bot_data['text_cache_service'] = self.text_cache_service

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
                
            # Оптимизированные настройки для более эффективного сбора обновлений
            # Уменьшен таймаут для более быстрого обнаружения ошибок
            # Явное указание типов обновлений для обработки
            self.logger.info("Запуск start_polling...")
            try:
                self.updater.start_polling(
                    timeout=10,  # Увеличиваем таймаут для более стабильной работы
                    drop_pending_updates=True,  # Пропуск накопившихся обновлений
                    allowed_updates=['message', 'callback_query', 'chat_member', 'chosen_inline_result'],  # Только необходимые типы обновлений
                    poll_interval=0.5  # Увеличиваем интервал опроса для снижения нагрузки
                )
                self.logger.info("Бот успешно запущен")
                self.logger.info(f"Dispatcher running: {self.updater.dispatcher.running}")
            except Exception as e:
                self.logger.error(f"Ошибка при запуске polling: {e}")
                return

            # Вместо собственной реализации используем встроенный метод idle
            # который более надежно обрабатывает сигналы и блокировку
            try:
                self.logger.info("Входим в режим idle...")
                self.updater.idle()
            except Exception as e:
                self.logger.error(f"Ошибка в idle режиме: {e}")
                
            # Если idle вернул управление, значит бот завершает работу
            self.logger.info("Бот завершил работу")
        except Exception as e:
            self.logger.log_error(e, {"context": "bot.run()"})
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