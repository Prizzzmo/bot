
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

    def clean_chat(self, bot, chat_id):
        """
        Полностью очищает чат с использованием метода Telegram API deleteChat.
        
        Args:
            bot: Объект бота Telegram
            chat_id: ID чата для очистки
            
        Returns:
            bool: Успешность выполнения операции
        """
        try:
            self.logger.info(f"Попытка полной очистки чата {chat_id}")
            
            def delete_chat_func():
                return bot.delete_chat(chat_id=chat_id)
            
            result = self.request_queue.enqueue(delete_chat_func)
            
            if result:
                self.logger.info(f"Чат {chat_id} успешно очищен")
                return True
            else:
                self.logger.warning(f"Не удалось очистить чат {chat_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка при очистке чата {chat_id}: {e}")
            return False
    
    def delete_chat_history(self, bot, chat_id, user_id=None):
        """
        Улучшенная функция для удаления истории чата с использованием нескольких методов.
        Пытается использовать разные подходы для максимальной совместимости.
        
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
            
            # Метод 1: Удаление сохраненных сообщений через данные пользователя в диспетчере
            if user_id:
                try:
                    # Получаем данные пользователя из dispatcher
                    user_data = None
                    if hasattr(bot, '_dispatcher') and hasattr(bot._dispatcher, 'user_data'):
                        user_data = bot._dispatcher.user_data.get(user_id, {})
                    
                    # Если у нас есть доступ к данным пользователя, извлекаем ID сообщений
                    message_ids = []
                    if user_data and 'message_ids' in user_data:
                        message_ids = user_data.get('message_ids', [])
                    
                    # Отправляем уведомление пользователю
                    notification = bot.send_message(
                        chat_id=chat_id, 
                        text=f"🧹 Начинаю очистку чата... Будет удалено до {len(message_ids)} сообщений."
                    )
                    
                    # Если у нас есть ID сообщений, удаляем их по одному
                    if message_ids:
                        self.logger.info(f"Попытка удалить {len(message_ids)} сохраненных сообщений для пользователя {user_id}")
                        deleted_count = 0
                        errors_count = 0
                        
                        # Проходим по ID сообщений и удаляем каждое
                        for msg_id in message_ids:
                            try:
                                def delete_msg_func(msg_id=msg_id):
                                    return bot.delete_message(chat_id=chat_id, message_id=msg_id)
                                
                                result = self.request_queue.enqueue(delete_msg_func)
                                if result:
                                    deleted_count += 1
                                    # Добавляем небольшую задержку каждые 5 сообщений, чтобы избежать ограничений API
                                    if deleted_count % 5 == 0:
                                        import time
                                        time.sleep(0.3)
                            except Exception as msg_err:
                                errors_count += 1
                                # Логируем детали ошибки только каждые 10-е сообщение
                                if errors_count % 10 == 0:
                                    self.logger.debug(f"Ошибка при удалении сообщения {msg_id}: {msg_err}")
                        
                        # Очищаем список сохраненных сообщений
                        if user_data and 'message_ids' in user_data:
                            user_data['message_ids'] = []
                        
                        # Отмечаем успех, если хотя бы некоторые сообщения были удалены
                        if deleted_count > 0:
                            success = True
                            self.logger.info(f"Удалено {deleted_count} из {len(message_ids)} сообщений, ошибок: {errors_count}")
                            
                            # Отправляем сообщение о результате
                            summary_text = f"✅ Очистка чата выполнена! Удалено {deleted_count} из {len(message_ids)} сообщений."
                            if errors_count > 0:
                                summary_text += f"\n\nНекоторые сообщения ({errors_count}) не могут быть удалены - возможно, они уже удалены или слишком старые."
                            
                            # Отправляем итоговое сообщение
                            bot.send_message(chat_id=chat_id, text=summary_text)
                    else:
                        self.logger.info(f"Не найдено сохраненных сообщений для пользователя {user_id}")
                        # Отправляем сообщение, что сохраненных сообщений не найдено
                        bot.send_message(
                            chat_id=chat_id, 
                            text="ℹ️ Не найдено сохраненных сообщений для удаления. Попробуйте альтернативные методы очистки."
                        )
                except Exception as e1:
                    self.logger.warning(f"Ошибка при удалении сохраненных сообщений: {e1}")
            
            # Метод 2: Отправка нескольких команд очистки чата (если метод 1 не сработал полностью)
            if not success:
                try:
                    # Отправляем уведомление пользователю
                    bot.send_message(
                        chat_id=chat_id, 
                        text="🧹 Выполняю альтернативную очистку чата..."
                    )
                    
                    # Попытка отправить системные команды для очистки (работает в некоторых клиентах)
                    commands = ["/clearcache", "/cleanchat", "/clear"]
                    for cmd in commands:
                        try:
                            sent_msg = bot.send_message(chat_id=chat_id, text=cmd)
                            # Ждем секунду для применения команды
                            import time
                            time.sleep(1)
                            # Удаляем отправленную команду
                            def delete_cmd_func(msg_id=sent_msg.message_id):
                                return bot.delete_message(chat_id=chat_id, message_id=msg_id)
                            self.request_queue.enqueue(delete_cmd_func)
                        except Exception:
                            pass
                    
                    # Отправляем сообщение о попытке очистки
                    bot.send_message(
                        chat_id=chat_id,
                        text="🧹 Выполнена альтернативная очистка чата. Результат зависит от версии вашего клиента Telegram."
                    )
                    
                    # Считаем как частичный успех
                    success = True
                except Exception as e2:
                    self.logger.warning(f"Ошибка при выполнении альтернативной очистки чата: {e2}")
            
            # Метод 3: Предложение пользователю альтернативные варианты
            # Создаем inline-клавиатуру с кнопкой повторной попытки
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

    def __del__(self):
        """Завершаем очередь запросов при удалении объекта"""
        if hasattr(self, 'request_queue'):
            self.request_queue.stop()
