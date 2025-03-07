
import time
import telegram
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

class MessageManager:
    """Класс для управления сообщениями в чате"""

    def __init__(self, logger):
        self.logger = logger
        self._deletion_lock = threading.Lock()

    def save_message_id(self, update, context, message_id):
        """
        Сохраняет ID сообщения в список предыдущих сообщений.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
            message_id (int): ID сообщения для сохранения
        """
        if not context or not hasattr(context, 'user_data'):
            self.logger.warning("Отсутствует контекст пользователя")
            return

        if not isinstance(message_id, int):
            self.logger.warning(f"Некорректный ID сообщения: {message_id}")
            return

        # Инициализация списка, если его нет
        if 'previous_messages' not in context.user_data:
            context.user_data['previous_messages'] = []

        # Добавляем только уникальные ID
        if message_id not in context.user_data['previous_messages']:
            context.user_data['previous_messages'].append(message_id)

        # Хранить не больше 100 последних сообщений
        max_saved_messages = 100
        if len(context.user_data['previous_messages']) > max_saved_messages:
            context.user_data['previous_messages'] = context.user_data['previous_messages'][-max_saved_messages:]

    def clear_chat_history(self, update, context, preserve_message_id=None):
        """
        Полностью переработанная функция для очистки истории чата.
        Использует более надежный подход и агрессивную очистку сообщений.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
            preserve_message_id (int, optional): ID сообщения, которое нужно сохранить
        """
        # Базовые проверки
        if not update or not update.effective_chat or not context:
            self.logger.warning("Недостаточно данных для очистки чата")
            return

        # Используем блокировку для предотвращения конкурентных операций удаления
        with self._deletion_lock:
            try:
                chat_id = update.effective_chat.id
                
                # Получаем ID активного сообщения, которое нужно сохранить
                active_message_id = preserve_message_id
                if not active_message_id:
                    if update.message:
                        active_message_id = update.message.message_id
                    elif update.callback_query and update.callback_query.message:
                        active_message_id = update.callback_query.message.message_id

                # Получаем список сохраненных сообщений
                if 'previous_messages' not in context.user_data:
                    context.user_data['previous_messages'] = []
                
                # Получаем все сохраненные ID сообщений и удаляем дубликаты
                message_ids = list(set(context.user_data.get('previous_messages', [])))
                
                # Если нет сообщений для удаления, выходим
                if not message_ids:
                    return

                # Исключаем текущее активное сообщение из удаления
                if active_message_id and active_message_id in message_ids:
                    message_ids.remove(active_message_id)
                
                # Сортируем сообщения от новых к старым для повышения вероятности успешного удаления
                message_ids.sort(reverse=True)
                
                # Логи для отладки
                self.logger.debug(f"Сообщения для удаления в чате {chat_id}: {len(message_ids)} сообщений")
                
                # Счетчики для отслеживания результатов
                successful = 0
                failed = 0
                error_types = {}
                
                # Функция для удаления одного сообщения
                def delete_single_message(msg_id):
                    nonlocal successful, failed
                    try:
                        result = context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                        if result:
                            successful += 1
                        return True
                    except telegram.error.TelegramError as e:
                        # Анализируем ошибку для более полной отладки
                        error_text = str(e).lower()
                        error_category = "unknown"
                        
                        if "message to delete not found" in error_text:
                            error_category = "not_found"
                        elif "message can't be deleted" in error_text:
                            error_category = "cannot_delete"
                        elif "forbidden" in error_text:
                            error_category = "forbidden"
                        elif "too many requests" in error_text or "flood" in error_text:
                            error_category = "rate_limit"
                            # При ограничении частоты запросов делаем паузу
                            time.sleep(1)
                        
                        # Подсчитываем типы ошибок для анализа
                        if error_category not in error_types:
                            error_types[error_category] = 0
                        error_types[error_category] += 1
                        
                        failed += 1
                        return False
                    except Exception as e:
                        self.logger.error(f"Неожиданная ошибка при удалении сообщения {msg_id}: {e}")
                        failed += 1
                        return False
                
                # Разбиваем удаление на пакеты для снижения нагрузки на API
                batch_size = 5  # Уменьшаем размер пакета для надежности
                for i in range(0, len(message_ids), batch_size):
                    batch = message_ids[i:i+batch_size]
                    
                    # Используем многопоточность для одновременного удаления нескольких сообщений
                    with ThreadPoolExecutor(max_workers=3) as executor:  # Уменьшаем число рабочих потоков
                        # Запускаем задачи удаления
                        futures = [executor.submit(delete_single_message, msg_id) for msg_id in batch]
                        
                        # Ожидаем завершения всех задач с таймаутом
                        for future in as_completed(futures, timeout=3):
                            try:
                                future.result()
                            except Exception as e:
                                self.logger.error(f"Ошибка при обработке результата удаления: {e}")
                    
                    # Добавляем паузу между пакетами, чтобы избежать ограничений API
                    time.sleep(0.5)
                
                # Обновляем список сохраненных сообщений
                # Сохраняем только активное сообщение, если оно есть
                if active_message_id:
                    context.user_data['previous_messages'] = [active_message_id]
                else:
                    context.user_data['previous_messages'] = []
                
                # Логируем результаты операции
                self.logger.info(
                    f"Очистка чата {chat_id}: удалено {successful}, не удалось {failed}, "
                    f"типы ошибок: {error_types}"
                )
                
            except Exception as e:
                self.logger.error(f"Критическая ошибка при очистке чата: {str(e)}")
                # В случае ошибки очищаем список сообщений принудительно
                context.user_data['previous_messages'] = []
                if 'active_message_id' and active_message_id:
                    context.user_data['previous_messages'] = [active_message_id]

    def clean_all_messages_except_active(self, update, context):
        """
        Удаляет все сообщения, кроме активного.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
        """
        active_message_id = None

        if update.message:
            active_message_id = update.message.message_id
        elif update.callback_query and update.callback_query.message:
            active_message_id = update.callback_query.message.message_id

        self.clear_chat_history(update, context, preserve_message_id=active_message_id)
