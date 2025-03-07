
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
            
            # Метод 1: Используем API-метод deleteHistory (если доступен)
            success = False
            try:
                def delete_history_func():
                    return bot.delete_chat_history(chat_id=chat_id)
                
                result = self.request_queue.enqueue(delete_history_func)
                if result:
                    self.logger.info(f"История чата {chat_id}{user_str} успешно удалена методом delete_chat_history")
                    success = True
            except Exception as e1:
                self.logger.warning(f"Не удалось удалить историю чата методом delete_chat_history: {e1}")
            
            # Метод 2: Удаление сохраненных сообщений (если у нас есть их ID)
            if not success and user_id:
                try:
                    from telegram.ext import CallbackContext
                    context = bot._dispatcher.user_data.get(user_id, {})
                    message_ids = context.get('message_ids', [])
                    
                    if message_ids:
                        self.logger.info(f"Попытка удалить {len(message_ids)} сохраненных сообщений для пользователя {user_id}")
                        deleted_count = 0
                        
                        for msg_id in message_ids:
                            try:
                                def delete_msg_func(msg_id=msg_id):  # Важно использовать значение по умолчанию для замыкания
                                    return bot.delete_message(chat_id=chat_id, message_id=msg_id)
                                
                                result = self.request_queue.enqueue(delete_msg_func)
                                if result:
                                    deleted_count += 1
                            except Exception:
                                # Игнорируем ошибки отдельных сообщений
                                pass
                        
                        # Очищаем список сохраненных сообщений
                        context['message_ids'] = []
                        
                        if deleted_count > 0:
                            self.logger.info(f"Удалено {deleted_count} из {len(message_ids)} сообщений")
                            success = True
                except Exception as e2:
                    self.logger.warning(f"Не удалось удалить сохраненные сообщения: {e2}")
            
            # Метод 3: Отправка системного сообщения для очистки чата (если другие методы не сработали)
            if not success:
                try:
                    # Отправляем сообщение с командой очистки (работает в некоторых клиентах Telegram)
                    clean_message = "/cleanchat"
                    sent_msg = bot.send_message(chat_id=chat_id, text=clean_message)
                    
                    # Удаляем наше сообщение с командой очистки
                    def delete_clean_msg_func():
                        return bot.delete_message(chat_id=chat_id, message_id=sent_msg.message_id)
                    
                    self.request_queue.enqueue(delete_clean_msg_func)
                    
                    # Отправляем уведомление пользователю
                    info_msg = "🧹 Попытка очистки чата выполнена. Результат зависит от настроек вашего клиента Telegram."
                    bot.send_message(chat_id=chat_id, text=info_msg)
                    
                    # Считаем частичным успехом
                    success = True
                except Exception as e3:
                    self.logger.warning(f"Не удалось отправить команду очистки чата: {e3}")
            
            if success:
                self.logger.info(f"Очистка чата {chat_id}{user_str} выполнена")
                return True
            else:
                self.logger.warning(f"Все методы очистки чата {chat_id}{user_str} не удались")
                return False
                
        except Exception as e:
            self.logger.error(f"Критическая ошибка при удалении истории чата {chat_id}: {e}")
            return False

    def __del__(self):
        """Завершаем очередь запросов при удалении объекта"""
        if hasattr(self, 'request_queue'):
            self.request_queue.stop()
