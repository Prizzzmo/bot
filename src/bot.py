
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
        """Запуск бота"""
        try:
            self.logger.info("Бот успешно запущен")
            self.updater.start_polling(timeout=30, read_latency=2.0, drop_pending_updates=True)
            self.updater.idle()
        except Exception as e:
            self.logger.log_error(e, "Критическая ошибка при запуске бота")
            self.logger.critical(f"Бот не был запущен из-за критической ошибки: {e}")
