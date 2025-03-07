import threading
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, Filters

from src.config import TOPIC, CHOOSE_TOPIC, TEST, ANSWER, CONVERSATION

class Bot:
    """Класс для управления Telegram ботом"""

    def __init__(self, config, logger, command_handlers):
        self.config = config
        self.logger = logger
        self.handlers = command_handlers
        self.updater = None
        
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
                    ]
                },
                fallbacks=[CommandHandler('start', self.handlers.start)],
                allow_reentry=True
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
        """Запускает бота и веб-сервер для логов"""
        self.logger.info("Запуск бота и веб-сервера логов...")

        # Запуск фонового процесса для веб-сервера
        threading.Thread(target=self.run_log_server, daemon=True).start()

        try:
            # Включаем сбор обновлений для реагирования на сообщения, запускаем бота
            # Установка более длинного таймаута для обработки конфликтов
            # Используем drop_pending_updates=True (не используем clean=True, так как они взаимоисключающие)
            self.updater.start_polling(timeout=30, drop_pending_updates=True)
            self.logger.info("Бот успешно запущен")

            # Остаемся в режиме работы до получения Ctrl+C
            self.updater.idle()
        except Exception as e:
            self.logger.error(f"Ошибка запуска бота: {e}")
            # Попытка принудительного завершения updater если он был создан
            if hasattr(self, 'updater'):
                self.updater.stop()
                
    def run_log_server(self):
        """Запускает простой веб-сервер для отображения логов"""
        try:
            import http.server
            import socketserver
            import threading
            import os
            
            # Определяем путь к директории с логами
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                
            # Устанавливаем порт и handler
            PORT = 8080
            Handler = http.server.SimpleHTTPRequestHandler
            
            # Настраиваем и запускаем сервер
            self.logger.info(f"Запуск веб-сервера логов на порту {PORT}")
            httpd = socketserver.TCPServer(("0.0.0.0", PORT), Handler)
            
            # Запускаем сервер
            try:
                httpd.serve_forever()
            except Exception as e:
                self.logger.error(f"Ошибка в веб-сервере: {e}")
        except Exception as e:
            self.logger.error(f"Ошибка при запуске веб-сервера логов: {e}")


class BotManager:
    """Класс для управления запуском бота и его жизненным циклом"""
    
    def __init__(self):
        self.logger = None
        
    def run(self):
        """Запускает основную функцию для инициализации и запуска бота"""
        from main import main
        main()