
import threading
import time
from src.telegram_queue import TelegramRequestQueue

class MessageManager:
    """Класс для управления сообщениями с оптимизированными запросами к Telegram API"""

    def __init__(self, logger):
        self.logger = logger
        self.active_messages = {}  # Кэш активных сообщений по user_id
        self.message_lock = threading.RLock()  # Блокировка для потокобезопасного доступа
        self.request_queue = TelegramRequestQueue(max_requests_per_second=25, logger=logger)

    def save_message_id(self, update, context, message_id):
        """
        Сохраняет ID сообщения с оптимизацией.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
            message_id (int): ID сообщения для сохранения
        """
        # Получаем user_id
        user_id = update.effective_user.id

        # Используем блокировку для потокобезопасной работы
        with self.message_lock:
            # Инициализируем message_ids, если отсутствует
            if not context.user_data.get('message_ids'):
                context.user_data['message_ids'] = []

            # Добавляем ID сообщения в список
            context.user_data['message_ids'].append(message_id)

            # Ограничиваем количество сохраненных ID до 50 для предотвращения утечек памяти
            if len(context.user_data['message_ids']) > 50:
                context.user_data['message_ids'] = context.user_data['message_ids'][-50:]

    def save_active_message_id(self, update, context, message_id):
        """
        Сохраняет ID активного сообщения с кэшированием.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
            message_id (int): ID активного сообщения
        """
        user_id = update.effective_user.id

        with self.message_lock:
            # Сохраняем в контексте пользователя
            context.user_data['active_message_id'] = message_id
            # Также кэшируем для быстрого доступа
            self.active_messages[user_id] = message_id

    def delete_message_safe(self, bot, chat_id, message_id):
        """
        Безопасное удаление сообщения через очередь запросов.
        
        Args:
            bot: Объект бота Telegram
            chat_id: ID чата
            message_id: ID сообщения для удаления
        """
        try:
            # Используем очередь запросов для удаления сообщения
            def delete_func():
                return bot.delete_message(chat_id=chat_id, message_id=message_id)
            
            self.request_queue.enqueue(delete_func)
        except Exception as e:
            # Игнорируем ошибки - часто сообщения уже удалены или недоступны
            pass

    def send_messages_batch(self, context, chat_id, messages, parse_mode='Markdown', 
                         disable_web_page_preview=True, interval=0.5):
        """
        Отправляет несколько сообщений с оптимальными задержками для избежания ограничений API.
        
        Args:
            context (telegram.ext.CallbackContext): Контекст разговора
            chat_id: ID чата для отправки
            messages: Список сообщений для отправки
            parse_mode: Режим форматирования (Markdown, HTML и т.д.)
            disable_web_page_preview: Отключить предпросмотр ссылок
            interval: Интервал между сообщениями в секундах
            
        Returns:
            list: Список ID отправленных сообщений
        """
        sent_message_ids = []
        
        for i, message in enumerate(messages):
            # Контроль размера сообщения
            if len(message) > 4000:
                # Разбиваем длинное сообщение на части по 4000 символов
                chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
                for chunk in chunks:
                    # Очередь запросов обеспечит паузы между отправками
                    def send_func():
                        return context.bot.send_message(
                            chat_id=chat_id,
                            text=chunk,
                            parse_mode=parse_mode,
                            disable_web_page_preview=disable_web_page_preview
                        )
                    
                    # Используем очередь запросов для отправки сообщения
                    sent_message = self.request_queue.enqueue(send_func)
                    if sent_message:
                        sent_message_ids.append(sent_message.message_id)
            else:
                # Отправляем обычное сообщение
                def send_func():
                    return context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode=parse_mode,
                        disable_web_page_preview=disable_web_page_preview
                    )
                
                # Используем очередь запросов для отправки сообщения
                sent_message = self.request_queue.enqueue(send_func)
                if sent_message:
                    sent_message_ids.append(sent_message.message_id)
        
        return sent_message_ids

    def clean_chat(self, bot, chat_id, user_id=None):
        """
        Оптимизированная функция для удаления истории чата с использованием метода delete_messages API Telegram.
        
        Args:
            bot: Объект бота Telegram
            chat_id: ID чата для очистки
            user_id: ID пользователя (опционально, если нужно логировать)
            
        Returns:
            bool: Успешность выполнения операции
        """
        try:
            user_str = f" пользователя {user_id}" if user_id else ""
            self.logger.info(f"Попытка удаления истории чата {chat_id}{user_str}")
            
            # Инициализируем переменную успеха
            success = False
            
            # Получаем данные пользователя и ID сообщений
            message_ids = []
            if user_id:
                try:
                    # Получаем данные пользователя из dispatcher
                    user_data = None
                    if hasattr(bot, '_dispatcher') and hasattr(bot._dispatcher, 'user_data'):
                        user_data = bot._dispatcher.user_data.get(user_id, {})
                    
                    # Если у нас есть доступ к данным пользователя, извлекаем ID сообщений
                    if user_data and 'message_ids' in user_data:
                        message_ids = user_data.get('message_ids', [])
                except Exception as e:
                    self.logger.warning(f"Ошибка при получении данных пользователя: {e}")
            
            # Отправляем уведомление пользователю
            notification = bot.send_message(
                chat_id=chat_id, 
                text=f"🧹 Начинаю очистку чата... Найдено {len(message_ids)} сообщений для удаления."
            )
            
            # Проверяем, есть ли сообщения для удаления
            if message_ids:
                self.logger.info(f"Попытка удалить {len(message_ids)} сообщений для чата {chat_id}")
                
                # Разбиваем сообщения на группы по 100 (максимальное количество для delete_messages)
                message_chunks = [message_ids[i:i+100] for i in range(0, len(message_ids), 100)]
                total_deleted = 0
                
                for chunk in message_chunks:
                    try:
                        # Используем метод delete_messages для пакетного удаления сообщений
                        def delete_messages_func(message_ids=chunk):
                            return bot._bot.delete_messages(chat_id=chat_id, message_ids=message_ids)
                        
                        result = self.request_queue.enqueue(delete_messages_func)
                        
                        if result:
                            total_deleted += len(chunk)
                            self.logger.info(f"Успешно удалено {len(chunk)} сообщений пакетом")
                        
                        # Небольшая пауза между пакетами запросов
                        import time
                        time.sleep(0.5)
                        
                    except Exception as e:
                        self.logger.warning(f"Ошибка при пакетном удалении сообщений: {e}")
                        
                        # Если пакетное удаление не сработало, пробуем удалять по одному
                        individual_deleted = 0
                        for msg_id in chunk:
                            try:
                                def delete_msg_func(msg_id=msg_id):
                                    return bot.delete_message(chat_id=chat_id, message_id=msg_id)
                                
                                result = self.request_queue.enqueue(delete_msg_func)
                                if result:
                                    individual_deleted += 1
                                    total_deleted += 1
                            except Exception:
                                pass
                        
                        self.logger.info(f"Удалено {individual_deleted} из {len(chunk)} сообщений индивидуально")
                
                # Очищаем список сохраненных сообщений
                if user_id and hasattr(bot, '_dispatcher') and hasattr(bot._dispatcher, 'user_data'):
                    user_data = bot._dispatcher.user_data.get(user_id, {})
                    if user_data and 'message_ids' in user_data:
                        user_data['message_ids'] = []
                
                # Проверяем результат удаления
                if total_deleted > 0:
                    success = True
                    self.logger.info(f"Всего удалено {total_deleted} из {len(message_ids)} сообщений")
                    
                    # Отправляем сообщение о результате
                    summary_text = f"✅ Очистка чата выполнена! Удалено {total_deleted} из {len(message_ids)} сообщений."
                    if total_deleted < len(message_ids):
                        summary_text += f"\n\nНекоторые сообщения ({len(message_ids) - total_deleted}) не могут быть удалены - возможно, они уже удалены или слишком старые."
                    
                    bot.send_message(chat_id=chat_id, text=summary_text)
            else:
                self.logger.info(f"Не найдено сообщений для удаления в чате {chat_id}")
                
                # Если нет сохраненных сообщений, пробуем альтернативные методы
                try:
                    bot.send_message(
                        chat_id=chat_id, 
                        text="ℹ️ Не найдено сохраненных сообщений для удаления. Выполняю альтернативную очистку..."
                    )
                    
                    # Попытка использовать системные команды очистки
                    commands = ["/clearcache", "/cleanchat", "/clear"]
                    for cmd in commands:
                        try:
                            sent_msg = bot.send_message(chat_id=chat_id, text=cmd)
                            import time
                            time.sleep(1)
                            def delete_cmd_func(msg_id=sent_msg.message_id):
                                return bot.delete_message(chat_id=chat_id, message_id=msg_id)
                            self.request_queue.enqueue(delete_cmd_func)
                        except Exception:
                            pass
                    
                    # Считаем как частичный успех
                    success = True
                    bot.send_message(
                        chat_id=chat_id,
                        text="🧹 Выполнена альтернативная очистка чата. Результат зависит от версии вашего клиента Telegram."
                    )
                except Exception as e2:
                    self.logger.warning(f"Ошибка при выполнении альтернативной очистки чата: {e2}")
            
            # Создаем inline-клавиатуру с кнопками
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [InlineKeyboardButton("🔄 Повторить очистку", callback_data="clear_chat_retry")],
                [InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение с кнопками
            bot.send_message(
                chat_id=chat_id,
                text=f"{'✅ Очистка чата выполнена!' if success else '⚠️ Полная очистка чата не удалась.'}\n\n"
                     f"Вы можете попробовать очистить чат снова или вернуться в меню.",
                reply_markup=reply_markup
            )
            
            return success
                
        except Exception as e:
            self.logger.error(f"Критическая ошибка при удалении истории чата {chat_id}: {e}")
            try:
                # Отправляем сообщение об ошибке
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                keyboard = [[InlineKeyboardButton("🔄 Повторить", callback_data="clear_chat_retry")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Произошла ошибка при очистке чата: {str(e)[:50]}...\nВы можете попробовать еще раз.",
                    reply_markup=reply_markup
                )
            except:
                pass
            return False
    
    # Алиас для совместимости со старым кодом
    delete_chat_history = clean_chat

    def __del__(self):
        """Завершаем очередь запросов при удалении объекта"""
        if hasattr(self, 'request_queue'):
            self.request_queue.stop()
