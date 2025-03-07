import time
import telegram
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from telegram.ext import CallbackContext
from telegram import Update
from telegram.error import BadRequest

class MessageManager:
    """Класс для управления сообщениями и их удалением"""

    def __init__(self, logger):
        self.logger = logger
        self.message_lock = threading.Lock()

    def save_message_id(self, update, context, message_id):
        """Сохраняет ID сообщения в context.user_data"""
        if not update or not context:
            return

        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            return

        with self.message_lock:
            if 'message_ids' not in context.user_data:
                context.user_data['message_ids'] = []

            context.user_data['message_ids'].append(message_id)

    def clear_chat_history(self, update, context):
        """Удаляет предыдущие сообщения бота"""
        if not update or not context:
            return 0

        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            return 0

        # Получаем ID сообщений для удаления из user_data
        message_ids = []
        with self.message_lock:
            if 'message_ids' in context.user_data:
                message_ids = context.user_data['message_ids']
                context.user_data['message_ids'] = []

        if not message_ids:
            return 0

        # Удаляем сообщения параллельно для ускорения
        deleted_count = 0

        # Используем ThreadPoolExecutor для параллельного удаления
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for msg_id in message_ids:
                futures.append(
                    executor.submit(
                        self._delete_message_safe, 
                        context.bot, 
                        update.effective_chat.id, 
                        msg_id
                    )
                )

            # Собираем результаты
            for future in as_completed(futures):
                if future.result():
                    deleted_count += 1

        self.logger.info(f"Удалено {deleted_count} из {len(message_ids)} сообщений для пользователя {user_id}")
        return deleted_count

    def _delete_message_safe(self, bot, chat_id, message_id):
        """Безопасное удаление сообщения с обработкой ошибок"""
        try:
            bot.delete_message(chat_id=chat_id, message_id=message_id)
            return True
        except BadRequest as e:
            # Игнорируем ошибки для старых сообщений, которые нельзя удалить
            if "Message to delete not found" in str(e) or "Message can't be deleted" in str(e):
                return False
            self.logger.warning(f"Ошибка при удалении сообщения {message_id}: {e}")
            return False
        except Exception as e:
            self.logger.warning(f"Непредвиденная ошибка при удалении сообщения {message_id}: {e}")
            return False

    def clean_all_messages_except_active(self, update, context):
        """Удаляет все сообщения, кроме активного"""
        if update.callback_query:
            active_message_id = update.callback_query.message.message_id
        elif update.message:
            active_message_id = update.message.message_id
        else:
            active_message_id = None

        user_id = update.effective_user.id if update.effective_user else None
        if not user_id:
            return 0

        # Получаем ID сообщений для удаления
        message_ids = []
        with self.message_lock:
            if 'message_ids' in context.user_data:
                message_ids = [msg_id for msg_id in context.user_data['message_ids'] if msg_id != active_message_id]
                context.user_data['message_ids'] = [msg_id for msg_id in context.user_data['message_ids'] if msg_id == active_message_id]

        if not message_ids:
            return 0

        deleted_count = 0
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for msg_id in message_ids:
                futures.append(
                    executor.submit(
                        self._delete_message_safe, 
                        context.bot, 
                        update.effective_chat.id, 
                        msg_id
                    )
                )

            # Собираем результаты
            for future in as_completed(futures):
                if future.result():
                    deleted_count += 1

        return deleted_count