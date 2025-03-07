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
        Оптимизированная функция для очистки истории чата.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
            preserve_message_id (int, optional): ID сообщения, которое нужно сохранить
        """
        # Базовые проверки
        if not update or not update.effective_chat or not context:
            self.logger.warning("Недостаточно данных для очистки чата")
            return

        # Используем блокировку, чтобы предотвратить одновременные операции удаления
        with self._deletion_lock:
            try:
                chat_id = update.effective_chat.id

                # Определяем активное сообщение, которое нужно сохранить
                active_message_id = preserve_message_id
                if not active_message_id:
                    if update.message:
                        active_message_id = update.message.message_id
                    elif update.callback_query and update.callback_query.message:
                        active_message_id = update.callback_query.message.message_id

                # Получаем список сохраненных сообщений
                if 'previous_messages' not in context.user_data:
                    context.user_data['previous_messages'] = []
                    return

                message_ids = list(set(context.user_data.get('previous_messages', [])))

                if not message_ids:
                    return

                # Исключаем активное сообщение из удаления
                if active_message_id and active_message_id in message_ids:
                    message_ids.remove(active_message_id)

                # Сортировка: сначала новые сообщения, они с большей вероятностью будут удалены успешно
                message_ids.sort(reverse=True)

                # Ограничиваем количество удаляемых сообщений
                max_deletions = min(len(message_ids), 150)
                message_ids = message_ids[:max_deletions]

                deleted_count = 0
                failed_count = 0
                error_counts = {}

                # Оптимизированное удаление сообщений с использованием ThreadPoolExecutor
                def delete_message(msg_id):
                    nonlocal deleted_count, failed_count

                    try:
                        context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                        deleted_count += 1
                        return True
                    except telegram.error.TelegramError as e:
                        # Классифицируем ошибку
                        error_text = str(e).lower()
                        error_type = "unknown"

                        if "message to delete not found" in error_text:
                            error_type = "not_found"
                        elif "message can't be deleted" in error_text:
                            error_type = "cannot_delete"
                        elif "forbidden" in error_text:
                            error_type = "forbidden"
                        elif "flood" in error_text:
                            error_type = "flood_control"
                            # При ошибке флуд-контроля, делаем паузу
                            time.sleep(1)

                        # Считаем типы ошибок
                        if error_type not in error_counts:
                            error_counts[error_type] = 0
                        error_counts[error_type] += 1

                        failed_count += 1
                        return False
                    except Exception as e:
                        failed_count += 1
                        return False

                # Удаляем сообщения пакетами, чтобы не превысить лимиты API
                batch_size = 10
                for i in range(0, len(message_ids), batch_size):
                    batch = message_ids[i:i+batch_size]

                    with ThreadPoolExecutor(max_workers=5) as executor:
                        futures = [executor.submit(delete_message, msg_id) for msg_id in batch]

                        # Ждем завершения пакета с таймаутом
                        for future in as_completed(futures, timeout=5):
                            try:
                                future.result()
                            except Exception as e:
                                self.logger.debug(f"Ошибка при удалении сообщения: {e}")

                    # Небольшая пауза между пакетами
                    if i + batch_size < len(message_ids):
                        time.sleep(0.3)

                # Обновляем список сообщений
                if active_message_id:
                    context.user_data['previous_messages'] = [active_message_id]
                else:
                    context.user_data['previous_messages'] = []

                # Логируем результаты
                if deleted_count > 0 or failed_count > 0:
                    self.logger.info(
                        f"Очистка чата {chat_id}: удалено {deleted_count}, не удалось {failed_count}, "
                        f"ошибки: {error_counts}, сохранено: {active_message_id}"
                    )

            except Exception as e:
                self.logger.error(f"Критическая ошибка при очистке чата: {str(e)}")

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