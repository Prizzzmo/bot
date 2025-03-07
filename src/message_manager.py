import threading
import time

class MessageManager:
    """Класс для управления сообщениями"""

    def __init__(self, logger):
        self.logger = logger
        self.active_messages = {}  # Кэш активных сообщений по user_id
        self.message_lock = threading.RLock()  # Блокировка для потокобезопасного доступа

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

    def clean_all_messages_except_active(self, update, context):
        """
        Очищает все сохраненные сообщения пользователя, кроме активного.
        
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
            
            # Удаляем сообщения
            for msg_id in messages_to_remove:
                try:
                    bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception as e:
                    # Просто игнорируем ошибки при удалении сообщений
                    pass
                    
            self.logger.debug(f"Очищено {len(messages_to_remove)} сообщений для пользователя {user_id}")
            
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
        """Завершаем таймер при удалении объекта"""
        pass #No timer to cancel