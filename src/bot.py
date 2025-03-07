import threading
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackQueryHandler

from src.config import TOPIC, CHOOSE_TOPIC, TEST, ANSWER, CONVERSATION

class Bot:
    """Класс для управления Telegram ботом"""

    def __init__(self, config, logger, command_handlers):
        self.config = config
        self.logger = logger
        self.handlers = command_handlers
        self.updater = None

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
                    ]
                },
                fallbacks=[CommandHandler('start', self.handlers.start)],
                allow_reentry=True
            )

            # Добавляем обработчики
            dp.add_error_handler(self.handlers.error_handler)
            dp.add_handler(conv_handler)

            return True
        except Exception as e:
            self.logger.log_error(e, "Ошибка при настройке бота")
            return False

    def run(self):
        """Запускает бота и веб-сервер для логов"""
        self.logger.info("Запуск бота и веб-сервера логов...")

        # Запуск фонового процесса для веб-сервера
        threading.Thread(target=self.run_log_server, daemon=True).start()

        try:
            # Включаем сбор обновлений для реагирования на сообщения, запускаем бота
            # Установка более длинного таймаута и включение clean=True для обработки конфликтов
            self.updater.start_polling(timeout=30, clean=True, drop_pending_updates=True)
            self.logger.info("Бот успешно запущен")

            # Остаемся в режиме работы до получения Ctrl+C
            self.updater.idle()
        except Exception as e:
            self.logger.error(f"Ошибка запуска бота: {e}")
            # Попытка принудительного завершения updater если он был создан
            if hasattr(self, 'updater'):
                self.updater.stop()


class BotManager:
    """Класс для управления запуском бота и его жизненным циклом"""
    
    def __init__(self):
        self.logger = None
        
    def run(self):
        """Запускает основную функцию для инициализации и запуска бота"""
        from main import main
        main()