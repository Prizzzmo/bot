
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
        Улучшенная функция для удаления сообщений чата.
        
        Args:
            bot: Объект бота Telegram
            chat_id: ID чата для очистки
            user_id: ID пользователя (опционально)
            
        Returns:
            bool: Успешность выполнения операции
        """
        try:
            # Логирование начала операции
            self.logger.info(f"Начата очистка чата {chat_id} (пользователь {user_id})")
            
            # Отправляем начальное сообщение напрямую через API для надежности
            status_message = None
            try:
                status_message = bot.send_message(
                    chat_id=chat_id,
                    text="🧹 Начинаю очистку чата..."
                )
            except Exception as e:
                self.logger.error(f"Ошибка при отправке начального сообщения: {e}")
            
            # Собираем ID сообщений для удаления
            message_ids = []
            
            # 1. Получаем историю сообщений напрямую из контекста пользователя
            try:
                if user_id and hasattr(bot, 'dispatcher'):
                    user_data = bot.dispatcher.user_data.get(user_id, {})
                    saved_ids = user_data.get('message_ids', [])
                    if saved_ids:
                        message_ids.extend([msg_id for msg_id in saved_ids if isinstance(msg_id, int)])
                        self.logger.info(f"Получено {len(saved_ids)} сохраненных ID сообщений пользователя")
            except Exception as e:
                self.logger.error(f"Ошибка при получении сохраненных ID сообщений: {e}")
                
            # 2. Получаем ID текущего сообщения и последних сообщений пользователя
            try:
                # Из текущего обновления - гарантированно существующие сообщения
                if status_message and status_message.message_id:
                    current_id = status_message.message_id
                    # Добавляем диапазон сообщений вокруг текущего (10 до и 10 после)
                    for i in range(current_id - 10, current_id + 10):
                        if i > 0 and i not in message_ids:
                            message_ids.append(i)
            except Exception as e:
                self.logger.error(f"Ошибка при получении текущих ID сообщений: {e}")
                
            # Удаляем дубликаты и сортируем
            message_ids = sorted(list(set(message_ids)))
            
            # Обновляем статус
            if status_message:
                try:
                    bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_message.message_id,
                        text=f"🧹 Подготовка к очистке...\nНайдено {len(message_ids)} сообщений."
                    )
                except Exception as e:
                    self.logger.error(f"Ошибка при обновлении статуса: {e}")
            
            # Если нет сообщений для удаления, генерируем диапазон последних сообщений
            if not message_ids:
                self.logger.info("Нет сохраненных ID, создаем диапазон последних сообщений")
                # Создаем диапазон ID для удаления: пробуем удалить последние 50 сообщений
                if status_message and status_message.message_id:
                    for i in range(status_message.message_id - 50, status_message.message_id + 10):
                        if i > 0:
                            message_ids.append(i)
                else:
                    # Если не получили ID статусного сообщения, используем произвольный диапазон
                    # Большинство ботов начинает с ID сообщений от 1 до 1000
                    start_id = 1
                    end_id = 1000
                    message_ids = list(range(start_id, end_id + 1))
                    
                self.logger.info(f"Создан диапазон из {len(message_ids)} сообщений для удаления")
            
            # Сообщаем о начале удаления
            total_messages = len(message_ids)
            if status_message:
                try:
                    bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_message.message_id,
                        text=f"🧹 Начинаю удаление {total_messages} сообщений..."
                    )
                except:
                    pass
            
            # Группируем сообщения по 100
            message_chunks = [message_ids[i:i+20] for i in range(0, len(message_ids), 20)]
            total_deleted = 0
            failed_ids = []
            
            # Удаляем сообщения пакетами
            for i, chunk in enumerate(message_chunks):
                try:
                    # Обновляем статус
                    if status_message and i % 5 == 0:  # Обновляем каждый 5-й раз для снижения нагрузки
                        progress = int((i / len(message_chunks)) * 100)
                        try:
                            bot.edit_message_text(
                                chat_id=chat_id,
                                message_id=status_message.message_id,
                                text=f"🧹 Очистка чата... {progress}%\nУдалено {total_deleted} из {total_messages} сообщений."
                            )
                        except:
                            pass
                    
                    # Перебираем сообщения в текущем пакете и пытаемся удалить каждое
                    for msg_id in chunk:
                        # Синхронное удаление каждого сообщения для максимальной надежности
                        try:
                            result = bot.delete_message(chat_id=chat_id, message_id=msg_id)
                            total_deleted += 1
                        except Exception as e:
                            # Если не получилось синхронно, добавляем в очередь
                            def delete_single():
                                try:
                                    return bot.delete_message(chat_id=chat_id, message_id=msg_id)
                                except:
                                    return False
                            
                            result = self.request_queue.enqueue(delete_single)
                            if result:
                                total_deleted += 1
                            else:
                                failed_ids.append(msg_id)
                        
                        # Небольшая пауза для избежания ограничений API
                        time.sleep(0.05)
                except Exception as e:
                    self.logger.warning(f"Ошибка при обработке пакета сообщений: {e}")
            
            # Очищаем сохраненные ID сообщений пользователя
            try:
                if user_id and hasattr(bot, 'dispatcher'):
                    user_data = bot.dispatcher.user_data.get(user_id, {})
                    if 'message_ids' in user_data:
                        user_data['message_ids'] = []
                        self.logger.info(f"Очищены сохраненные ID сообщений пользователя {user_id}")
            except Exception as e:
                self.logger.error(f"Ошибка при очистке сохраненных ID: {e}")
            
            # Удаляем статусное сообщение
            if status_message:
                try:
                    bot.delete_message(chat_id=chat_id, message_id=status_message.message_id)
                except:
                    pass
            
            # Отправляем итоговое сообщение
            keyboard = [
                [InlineKeyboardButton("🔄 Повторить очистку", callback_data="clear_chat_retry")],
                [InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            result_text = f"✅ Удаление завершено!\nУдалено {total_deleted} из {total_messages} сообщений."
            if total_deleted < total_messages:
                result_text += "\n\n⚠️ Некоторые сообщения не удалось удалить (возможно, они слишком старые или уже удалены)."
            
            bot.send_message(
                chat_id=chat_id,
                text=result_text,
                reply_markup=reply_markup
            )
            
            self.logger.info(f"Очистка чата {chat_id} завершена. Удалено {total_deleted} из {total_messages} сообщений.")
            return total_deleted > 0
            
        except Exception as e:
            self.logger.error(f"Критическая ошибка при очистке чата {chat_id}: {e}")
            
            # Отправляем сообщение об ошибке
            try:
                keyboard = [
                    [InlineKeyboardButton("🔄 Повторить", callback_data="clear_chat_retry")],
                    [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Ошибка при очистке чата: {str(e)[:100]}\n\nПопробуйте еще раз.",
                    reply_markup=reply_markup
                )
            except:
                pass
            
            return False
    
    # Алиас для обратной совместимости
    delete_chat_history = clean_chat

    def __del__(self):
        """Завершаем очередь запросов при удалении объекта"""
        if hasattr(self, 'request_queue'):
            self.request_queue.stop()
