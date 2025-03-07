
import threading
import time
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
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
        Высокооптимизированная функция для быстрого удаления сообщений чата без визуализации.
        
        Args:
            bot: Объект бота Telegram
            chat_id: ID чата для очистки
            user_id: ID пользователя (опционально)
            
        Returns:
            bool: Успешность выполнения операции
        """
        try:
            # Логирование начала операции
            self.logger.info(f"Начата очистка чата {chat_id}")
            
            # Сбор ID сообщений для удаления (с параллельной обработкой)
            message_ids = set()  # Используем set для автоматического удаления дубликатов
            
            # 1. Быстрое получение сохраненных ID сообщений из контекста пользователя
            if user_id and hasattr(bot, 'dispatcher'):
                try:
                    user_data = bot.dispatcher.user_data.get(user_id, {})
                    saved_ids = user_data.get('message_ids', [])
                    if saved_ids:
                        message_ids.update([msg_id for msg_id in saved_ids if isinstance(msg_id, int)])
                except Exception:
                    pass  # Игнорируем ошибки для ускорения процесса
            
            # 2. Быстрое получение диапазона последних сообщений
            try:
                # Отправляем временное сообщение для определения текущего ID (с минимальным контентом)
                temp_message = bot.send_message(chat_id=chat_id, text=".")
                
                if temp_message and temp_message.message_id:
                    current_id = temp_message.message_id
                    # Диапазон сообщений для удаления (только предыдущие)
                    message_ids.update(range(max(1, current_id - 100), current_id))
                    # Сразу удаляем временное сообщение
                    bot.delete_message(chat_id=chat_id, message_id=current_id)
            except Exception:
                pass  # Игнорируем ошибки для ускорения процесса
            
            # Конвертируем в список и сортируем для оптимального удаления
            message_ids = sorted(list(message_ids))
            
            # Если список пуст, быстро завершаем
            if not message_ids:
                return False
            
            # Оптимизация: увеличиваем размер пакетов для более быстрого удаления
            # и используем более эффективную параллельную обработку
            message_chunks = [message_ids[i:i+100] for i in range(0, len(message_ids), 100)]
            total_deleted = 0
            
            # Пытаемся использовать наиболее эффективный метод удаления
            bot_has_bulk_delete = hasattr(bot, 'delete_messages')
            
            # Параллельные потоки для удаления сообщений
            deletion_threads = []
            
            def delete_chunk(chunk):
                nonlocal total_deleted
                deleted_count = 0
                
                # Пробуем массовое удаление, если API поддерживает
                if bot_has_bulk_delete:
                    try:
                        result = bot.delete_messages(chat_id=chat_id, message_ids=chunk)
                        if result:
                            deleted_count = len(chunk)
                            return deleted_count
                    except Exception:
                        pass
                
                # Обычное удаление по одному, но с использованием очереди запросов
                for msg_id in chunk:
                    try:
                        result = self.delete_message_safe(bot, chat_id, msg_id)
                        if result:
                            deleted_count += 1
                    except Exception:
                        pass
                
                return deleted_count
            
            # Запускаем удаление в основном потоке для избежания проблем с многопоточностью в Telegram API
            for chunk in message_chunks:
                total_deleted += delete_chunk(chunk)
            
            # Очищаем сохраненные ID сообщений пользователя
            if user_id and hasattr(bot, 'dispatcher'):
                try:
                    user_data = bot.dispatcher.user_data.get(user_id, {})
                    if 'message_ids' in user_data:
                        user_data['message_ids'] = []
                except Exception:
                    pass
            
            # Минимальное сообщение о результате
            keyboard = [
                [InlineKeyboardButton("🔄 Повторить", callback_data="clear_chat_retry"),
                 InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Используем очередь запросов для отправки итогового сообщения
            def send_result_message():
                return bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ Удалено {total_deleted} сообщений.",
                    reply_markup=reply_markup
                )
            
            self.request_queue.enqueue(send_result_message)
            return total_deleted > 0
            
        except Exception as e:
            self.logger.error(f"Ошибка при очистке чата: {e}")
            
            # Простое сообщение об ошибке через очередь запросов
            keyboard = [[InlineKeyboardButton("🔄 Повторить", callback_data="clear_chat_retry")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            def send_error_message():
                return bot.send_message(
                    chat_id=chat_id,
                    text="❌ Ошибка при очистке чата.",
                    reply_markup=reply_markup
                )
            
            self.request_queue.enqueue(send_error_message)
            return False
    
    # Алиас для обратной совместимости
    delete_chat_history = clean_chat

    def __del__(self):
        """Завершаем очередь запросов при удалении объекта"""
        if hasattr(self, 'request_queue'):
            self.request_queue.stop()
