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

    def clean_all_messages_except_active(self, update, context):
        """
        Очищает все сохраненные сообщения пользователя, кроме активного,
        с использованием оптимизированной очереди запросов.
        
        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
        """
        try:
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            bot = context.bot
            
            # Получаем ID активного сообщения
            active_message_id = context.user_data.get('active_message_id')
            
            # Получаем список всех сохраненных сообщений
            message_ids = context.user_data.get('message_ids', [])
            
            # Защита от слишком частого удаления
            last_clean_time = context.user_data.get('last_clean_time', 0)
            current_time = time.time()
            
            # Ограничиваем очистку до 1 раза в 3 секунды
            if current_time - last_clean_time < 3:
                return
            
            # Сохраняем время последней очистки

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

            context.user_data['last_clean_time'] = current_time
            
            # Фильтруем список сообщений для удаления
            messages_to_remove = []
            with self.message_lock:
                for msg_id in message_ids:
                    # Не удаляем активное сообщение
                    if active_message_id and msg_id == active_message_id:
                        continue
                    messages_to_remove.append(msg_id)
                
                # Очищаем список сохраненных сообщений
                context.user_data['message_ids'] = []
                if active_message_id:
                    context.user_data['message_ids'] = [active_message_id]
            
            # Группируем удаление сообщений для оптимизации
            # Разбиваем на группы по 10 сообщений для предотвращения превышения лимитов API
            chunk_size = 10
            for i in range(0, len(messages_to_remove), chunk_size):
                chunk = messages_to_remove[i:i+chunk_size]
                
                # Добавляем все сообщения из группы в очередь запросов
                for msg_id in chunk:
                    self.delete_message_safe(bot, chat_id, msg_id)
                    
            self.logger.debug(f"Запланировано удаление {len(messages_to_remove)} сообщений для пользователя {user_id}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при очистке сообщений: {e}")
    
    def clear_chat_history(self, update, context):
        """
        Альтернативный метод для очистки истории чата
        
        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
        """
        # Просто делегируем вызов методу clean_all_messages_except_active
        self.clean_all_messages_except_active(update, context)

    def __del__(self):
        """Завершаем очередь запросов при удалении объекта"""
        if hasattr(self, 'request_queue'):
            self.request_queue.stop()