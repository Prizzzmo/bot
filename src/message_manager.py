
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
        Новая оптимизированная функция для удаления сообщений в чате с использованием 
        нативных методов Telegram API.
        
        Args:
            bot: Объект бота Telegram
            chat_id: ID чата для очистки
            user_id: ID пользователя (опционально)
            
        Returns:
            bool: Успешность выполнения операции
        """
        try:
            # Логирование
            user_str = f" пользователя {user_id}" if user_id else ""
            self.logger.info(f"Начата очистка чата {chat_id}{user_str}")
            
            # Отправка уведомления о начале очистки
            status_message = bot.send_message(
                chat_id=chat_id,
                text="🧹 Начинаю очистку чата..."
            )
            
            # Получаем сохраненные ID сообщений пользователя
            message_ids = []
            if user_id and hasattr(bot, '_dispatcher') and hasattr(bot._dispatcher, 'user_data'):
                user_data = bot._dispatcher.user_data.get(user_id, {})
                message_ids = user_data.get('message_ids', [])
            
            # Обновляем статус с количеством найденных сообщений
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_message.message_id,
                text=f"🧹 Очистка чата в процессе...\nНайдено {len(message_ids)} сообщений для удаления."
            )
            
            # Если нет сохраненных сообщений, пробуем получить историю чата через API
            if not message_ids and hasattr(bot, '_bot'):
                try:
                    # Получаем историю чата (ограничиваем до 100 последних сообщений)
                    history = bot._bot.get_chat_history(chat_id=chat_id, limit=100)
                    if history:
                        # Получаем ID сообщений из истории
                        message_ids = [msg.message_id for msg in history]
                        self.logger.info(f"Получено {len(message_ids)} сообщений из истории чата")
                except Exception as e:
                    self.logger.warning(f"Не удалось получить историю чата: {e}")
            
            # Если все равно нет сообщений, сообщаем пользователю
            if not message_ids:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=status_message.message_id,
                    text="⚠️ Не найдено сообщений для удаления."
                )
                
                # Создаем кнопки для дальнейших действий
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                keyboard = [
                    [InlineKeyboardButton("🔙 Вернуться в меню", callback_data="back_to_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                bot.send_message(
                    chat_id=chat_id,
                    text="Возможно, сообщения уже были удалены или бот не имеет доступа к истории чата.",
                    reply_markup=reply_markup
                )
                return False
                
            # Группируем сообщения по 100 (максимум для метода delete_messages)
            message_chunks = [message_ids[i:i+100] for i in range(0, len(message_ids), 100)]
            total_deleted = 0
            
            # Удаляем сообщения пакетами
            for i, chunk in enumerate(message_chunks):
                try:
                    # Обновляем статус прогресса
                    progress = int((i / len(message_chunks)) * 100)
                    bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_message.message_id,
                        text=f"🧹 Очистка чата... {progress}%\nУдалено {total_deleted} из {len(message_ids)} сообщений."
                    )
                    
                    # Используем нативный метод API для пакетного удаления
                    def delete_batch():
                        if hasattr(bot, '_bot'):
                            return bot._bot.delete_messages(chat_id=chat_id, message_ids=chunk)
                        else:
                            # Резервный метод, если нет прямого доступа к API
                            success_count = 0
                            for msg_id in chunk:
                                if bot.delete_message(chat_id=chat_id, message_id=msg_id):
                                    success_count += 1
                            return success_count > 0
                            
                    result = self.request_queue.enqueue(delete_batch)
                    
                    if result:
                        total_deleted += len(chunk)
                        self.logger.info(f"Успешно удалено {len(chunk)} сообщений (пакет {i+1}/{len(message_chunks)})")
                    
                    # Небольшая пауза между пакетами для предотвращения блокировки API
                    time.sleep(0.3)
                    
                except Exception as e:
                    self.logger.warning(f"Ошибка при удалении пакета сообщений: {e}")
                    
                    # Если пакетное удаление не удалось, пробуем удалять по одному
                    for msg_id in chunk:
                        try:
                            def delete_single():
                                return bot.delete_message(chat_id=chat_id, message_id=msg_id)
                            
                            if self.request_queue.enqueue(delete_single):
                                total_deleted += 1
                        except Exception:
                            pass
            
            # Очищаем сохраненные ID сообщений пользователя
            if user_id and hasattr(bot, '_dispatcher') and hasattr(bot._dispatcher, 'user_data'):
                user_data = bot._dispatcher.user_data.get(user_id, {})
                if 'message_ids' in user_data:
                    user_data['message_ids'] = []
            
            # Проверяем результат и отправляем итоговое сообщение
            success = total_deleted > 0
            
            # Удаляем статусное сообщение
            try:
                bot.delete_message(chat_id=chat_id, message_id=status_message.message_id)
            except:
                pass
            
            # Создаем кнопки для дальнейших действий
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [InlineKeyboardButton("🔄 Повторить очистку", callback_data="clear_chat_retry")],
                [InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем итоговое сообщение
            result_text = f"✅ Очистка чата завершена!\nУдалено {total_deleted} из {len(message_ids)} сообщений."
            if total_deleted < len(message_ids):
                result_text += "\n\nНекоторые сообщения не удалось удалить - возможно, они слишком старые или у бота нет прав."
            
            bot.send_message(
                chat_id=chat_id,
                text=result_text,
                reply_markup=reply_markup
            )
            
            self.logger.info(f"Очистка чата {chat_id} завершена. Удалено {total_deleted} из {len(message_ids)} сообщений.")
            return success
            
        except Exception as e:
            self.logger.error(f"Критическая ошибка при очистке чата {chat_id}: {e}")
            
            # Отправляем сообщение об ошибке
            try:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                keyboard = [
                    [InlineKeyboardButton("🔄 Повторить", callback_data="clear_chat_retry")],
                    [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Произошла ошибка при очистке чата:\n{str(e)[:100]}\n\nВы можете попробовать еще раз.",
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
