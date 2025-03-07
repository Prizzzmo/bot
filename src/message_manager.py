
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
        Сверхбыстрая функция для удаления сообщений чата.
        
        Args:
            bot: Объект бота Telegram
            chat_id: ID чата для очистки
            user_id: ID пользователя (опционально)
            
        Returns:
            bool: Успешность выполнения операции
        """
        try:
            # Быстрый сбор ID сообщений для удаления
            message_ids = set()
            
            # Получаем сохраненные ID из контекста пользователя (если доступны)
            if user_id and hasattr(bot, 'dispatcher'):
                user_data = bot.dispatcher.user_data.get(user_id, {})
                saved_ids = user_data.get('message_ids', [])
                message_ids.update([msg_id for msg_id in saved_ids if isinstance(msg_id, int)])
            
            # Получаем текущее положение в чате
            try:
                # Использование минимального текста для уменьшения времени отправки
                temp_message = bot.send_message(chat_id=chat_id, text="·")
                current_id = temp_message.message_id
                
                # Собираем только предыдущие ID для удаления (с увеличенным диапазоном)
                # Увеличиваем диапазон до 200 для лучшего покрытия
                message_ids.update(range(max(1, current_id - 200), current_id))
                
                # Удаляем временное сообщение
                bot.delete_message(chat_id=chat_id, message_id=current_id)
            except:
                pass
            
            # Преобразуем в отсортированный список для оптимального удаления
            message_ids = sorted(list(message_ids))
            if not message_ids:
                return False
                
            # Проверяем поддержку пакетного удаления (telegram-bot-api v6+)
            use_bulk_delete = hasattr(bot, 'delete_messages')
            
            # Оптимальный размер пакета для массового удаления
            batch_size = 100
            message_chunks = [message_ids[i:i+batch_size] for i in range(0, len(message_ids), batch_size)]
            
            total_deleted = 0
            
            # Быстрое пакетное удаление
            for chunk in message_chunks:
                if use_bulk_delete:
                    try:
                        bot.delete_messages(chat_id=chat_id, message_ids=chunk)
                        total_deleted += len(chunk)
                        continue  # Переходим к следующему пакету, если удаление прошло успешно
                    except:
                        pass
                
                # Одиночное удаление (быстрее через прямое API, чем через очередь)
                for msg_id in chunk:
                    try:
                        bot.delete_message(chat_id=chat_id, message_id=msg_id)
                        total_deleted += 1
                    except:
                        pass
            
            # Очищаем кэш ID сообщений пользователя
            if user_id and hasattr(bot, 'dispatcher'):
                try:
                    user_data = bot.dispatcher.user_data.get(user_id, {})
                    user_data['message_ids'] = []
                except:
                    pass
            
            # Отправляем минимальное сообщение о результате без дополнительных действий
            bot.send_message(
                chat_id=chat_id,
                text=f"✅ Удалено {total_deleted} сообщений."
            )
            
            return total_deleted > 0
        
        except Exception as e:
            self.logger.error(f"Ошибка очистки чата: {e}")
            return False
    
    # Алиас для обратной совместимости
    delete_chat_history = clean_chat

    def __del__(self):
        """Завершаем очередь запросов при удалении объекта"""
        if hasattr(self, 'request_queue'):
            self.request_queue.stop()
