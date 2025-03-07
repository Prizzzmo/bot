import time
import threading

class MessageManager:
    """Класс для управления сообщениями и их историей в чате с оптимизацией производительности"""

    def __init__(self, logger):
        self.logger = logger
        self.active_messages = {}  # Кэш активных сообщений по user_id
        self.deletion_history = {}  # Кэш истории удалений для предотвращения повторных запросов
        self.message_lock = threading.RLock()  # Блокировка для потокобезопасного доступа

        # Запускаем периодическую очистку кэша истории удалений
        self.cleanup_timer = threading.Timer(3600, self.cleanup_deletion_history)
        self.cleanup_timer.daemon = True
        self.cleanup_timer.start()

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

    def clear_chat_history(self, update, context):
        """
        Удаляет сообщения из чата с оптимизацией и предотвращением повторных удалений.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
        """
        if 'message_ids' not in context.user_data:
            return

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        # Получаем ID сообщений для удаления с проверкой на дубликаты
        with self.message_lock:
            message_ids = context.user_data['message_ids']
            # Используем set для быстрого поиска и уникальности
            del_history_key = f"{user_id}_{chat_id}"

            if del_history_key not in self.deletion_history:
                self.deletion_history[del_history_key] = set()

            # Отфильтровываем сообщения, которые уже пытались удалить
            unique_ids = []
            for msg_id in message_ids:
                if msg_id not in self.deletion_history[del_history_key]:
                    unique_ids.append(msg_id)
                    self.deletion_history[del_history_key].add(msg_id)

            # Быстрая очистка списка после копирования
            context.user_data['message_ids'] = []

        # Вместо удаления всех сообщений сразу, группируем их по 5-10 штук
        # для снижения нагрузки на API Telegram
        batch_size = 8
        for i in range(0, len(unique_ids), batch_size):
            batch = unique_ids[i:i+batch_size]
            for msg_id in batch:
                try:
                    context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception:
                    # Игнорируем ошибки удаления для повышения производительности
                    pass

            # Небольшая пауза между удалением пакетов сообщений
            if i + batch_size < len(unique_ids):
                time.sleep(0.05)

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
        Удаляет все сообщения кроме активного с оптимизацией.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
        """
        if 'message_ids' not in context.user_data:
            return

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        # Получаем ID активного сообщения (проверяем сначала кэш для скорости)
        active_message_id = None
        with self.message_lock:
            active_message_id = self.active_messages.get(user_id) or context.user_data.get('active_message_id')

        # Если активного сообщения нет, просто очищаем все
        if not active_message_id:
            self.clear_chat_history(update, context)
            return

        # Получаем сообщения для удаления, исключая активное
        with self.message_lock:
            message_ids = [msg_id for msg_id in context.user_data['message_ids'] 
                         if msg_id != active_message_id]

            # Проверяем историю удалений
            del_history_key = f"{user_id}_{chat_id}"
            if del_history_key not in self.deletion_history:
                self.deletion_history[del_history_key] = set()

            # Отфильтровываем уже удаленные
            unique_ids = [msg_id for msg_id in message_ids 
                        if msg_id not in self.deletion_history[del_history_key]]

            # Добавляем в историю удалений
            for msg_id in unique_ids:
                self.deletion_history[del_history_key].add(msg_id)

            # Оставляем только активное сообщение в списке пользователя
            context.user_data['message_ids'] = [msg_id for msg_id in context.user_data['message_ids'] 
                                             if msg_id == active_message_id]

        # Группируем удаление так же, как в clear_chat_history
        batch_size = 8
        for i in range(0, len(unique_ids), batch_size):
            batch = unique_ids[i:i+batch_size]
            for msg_id in batch:
                try:
                    context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                except Exception:
                    # Игнорируем ошибки для повышения производительности
                    pass

            # Пауза между пакетами
            if i + batch_size < len(unique_ids):
                time.sleep(0.05)

    def cleanup_deletion_history(self):
        """Периодически очищает историю удалений для экономии памяти"""
        try:
            with self.message_lock:
                # Полностью очищаем историю удалений для экономии памяти
                self.deletion_history.clear()

            # Перезапускаем таймер
            self.cleanup_timer = threading.Timer(3600, self.cleanup_deletion_history)
            self.cleanup_timer.daemon = True
            self.cleanup_timer.start()
        except Exception as e:
            self.logger.error(f"Ошибка при очистке истории удалений: {e}")

    def __del__(self):
        """Завершаем таймер при удалении объекта"""
        if hasattr(self, 'cleanup_timer'):
            self.cleanup_timer.cancel()