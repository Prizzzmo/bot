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
        Гарантированно удаляет все сообщения из истории чата.

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
            chat_id = update.effective_chat.id
            # Инициализация списка сообщений, если его нет
            if 'previous_messages' not in context.user_data:
                context.user_data['previous_messages'] = []
                return

            # Копируем список, чтобы не изменять его во время перебора
            message_ids = context.user_data['previous_messages'].copy()

            # Если список пуст, ничего не делаем
            if not message_ids:
                return

            # Исключаем сообщение, которое нужно сохранить
            if preserve_message_id and preserve_message_id in message_ids:
                message_ids.remove(preserve_message_id)

            # Счетчики для статистики
            total = len(message_ids)
            deleted = 0
            failed = 0
            error_types = {}

            # Функция для удаления одного сообщения с обработкой ошибок
            def delete_single_message(msg_id):
                nonlocal deleted, failed

                try:
                    context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                    deleted += 1
                    return True
                except telegram.error.BadRequest as e:
                    # Классифицируем ошибки для лучшего логирования
                    error_message = str(e).lower()
                    error_category = "unknown"

                    if "message to delete not found" in error_message:
                        error_category = "not_found"
                    elif "message can't be deleted" in error_message:
                        error_category = "cannot_delete"
                    elif "message is too old" in error_message:
                        error_category = "too_old"

                    self.logger.debug(f"Не удалось удалить сообщение {msg_id}: {error_category}")

                    # Подсчитываем типы ошибок
                    if error_category not in error_types:
                        error_types[error_category] = 0
                    error_types[error_category] += 1

                    failed += 1
                    return False
                except Exception as e:
                    self.logger.error(f"Неожиданная ошибка при удалении сообщения {msg_id}: {e}")
                    failed += 1
                    return False

            # Разбиваем удаление на небольшие пакеты для снижения нагрузки на API
            batch_size = 3  # Очень маленький размер пакета для надежности
            for i in range(0, len(message_ids), batch_size):
                batch = message_ids[i:i+batch_size]

                # Удаляем каждое сообщение последовательно для максимальной надежности
                for msg_id in batch:
                    delete_single_message(msg_id)
                    # Добавляем небольшую паузу между каждым удалением
                    time.sleep(0.2)

                # Пауза между пакетами для предотвращения ограничения API
                time.sleep(0.5)

            # Обновляем список сохраненных сообщений
            # Сохраняем только активное сообщение (если оно есть)
            if preserve_message_id:
                context.user_data['previous_messages'] = [preserve_message_id]
            else:
                context.user_data['previous_messages'] = []

            # Логируем результаты очистки
            self.logger.info(f"Очистка чата: удалено {deleted}/{total} сообщений, ошибок: {failed}")
            if error_types:
                self.logger.info(f"Типы ошибок при удалении: {error_types}")

    def clean_all_messages_except_active(self, update, context):
        """
        Очищает все сообщения в чате, кроме активного.
        Используется перед отправкой новых сообщений.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
        """
        # Определяем активное сообщение
        active_message_id = None

        if update.callback_query and update.callback_query.message:
            active_message_id = update.callback_query.message.message_id

        # Вызываем основную функцию очистки с сохранением активного сообщения
        self.clear_chat_history(update, context, preserve_message_id=active_message_id)

    def clear_all(self, update, context):
        """
        Принудительная полная очистка всех сообщений без исключений.
        Используется по команде /clear_all

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
        """
        # Проверяем, что обновление содержит необходимые данные
        if not update or not update.effective_chat or not context:
            self.logger.warning("Недостаточно данных для полной очистки чата")
            return

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id if update.effective_user else "Неизвестный"

        self.logger.info(f"Запрос полной очистки чата от пользователя {user_id}")

        try:
            # Очищаем список предыдущих сообщений перед удалением
            if 'previous_messages' in context.user_data:
                num_messages = len(context.user_data['previous_messages'])
                context.user_data['previous_messages'] = []

                # Уведомляем о результате (если это не команда из обработчика)
                if update.message:
                    update.message.reply_text(f"✅ Очистка завершена. Удалено {num_messages} сообщений из истории.")
            else:
                # Если список не был инициализирован
                if update.message:
                    update.message.reply_text("✅ История сообщений уже пуста.")
        except Exception as e:
            self.logger.error(f"Ошибка при полной очистке чата: {e}")
            if update.message:
                update.message.reply_text(f"❌ Ошибка при очистке чата: {e}")

        with self._deletion_lock:
            try:
                chat_id = update.effective_chat.id

                active_message_id = None
                # Используем параметр preserve_message_id, если он передан
                if 'preserve_message_id' in locals() or 'preserve_message_id' in globals():
                    active_message_id = preserve_message_id
                if not active_message_id:
                    if update.message:
                        active_message_id = update.message.message_id
                    elif update.callback_query and update.callback_query.message:
                        active_message_id = update.callback_query.message.message_id

                # Убедимся, что у нас есть список предыдущих сообщений
                if 'previous_messages' not in context.user_data:
                    context.user_data['previous_messages'] = []

                # Удалим дубликаты и создадим новый список
                message_ids = list(set(context.user_data.get('previous_messages', [])))

                # Добавляем 5000 предшествующих возможных ID сообщений для агрессивной очистки
                # Это покроет сообщения, которые могли быть пропущены при отслеживании
                if active_message_id and active_message_id > 5000:
                    for i in range(active_message_id - 5000, active_message_id):
                        if i not in message_ids and i != active_message_id:
                            message_ids.append(i)

                # Если нет сообщений для удаления, выходим
                if not message_ids:
                    return

                # Исключаем активное сообщение из списка удаления
                if active_message_id and active_message_id in message_ids:
                    message_ids.remove(active_message_id)

                # Сортируем сообщения от новых к старым для более эффективного удаления
                message_ids.sort(reverse=True)

                # Логирование для отладки
                self.logger.debug(f"Пытаемся удалить {len(message_ids)} сообщений в чате {chat_id}")

                # Счетчики успеха и ошибок
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
                        # Категоризируем ошибки для лучшей диагностики
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
                            # При ограничении частоты делаем задержку
                            time.sleep(1)

                        # Подсчитываем типы ошибок
                        if error_category not in error_types:
                            error_types[error_category] = 0
                        error_types[error_category] += 1

                        failed += 1
                        return False
                    except Exception as e:
                        self.logger.error(f"Неожиданная ошибка при удалении сообщения {msg_id}: {e}")
                        failed += 1
                        return False

                # Разбиваем удаление на небольшие пакеты для снижения нагрузки на API
                batch_size = 3  # Очень маленький размер пакета для надежности
                for i in range(0, len(message_ids), batch_size):
                    batch = message_ids[i:i+batch_size]

                    # Удаляем каждое сообщение последовательно для максимальной надежности
                    for msg_id in batch:
                        delete_single_message(msg_id)
                        # Добавляем небольшую паузу между каждым удалением
                        time.sleep(0.2)

                    # Пауза между пакетами для предотвращения ограничения API
                    time.sleep(0.5)

                # Обновляем список сохраненных сообщений
                # Сохраняем только активное сообщение (если оно есть)
                context.user_data['previous_messages'] = []
                if active_message_id:
                    context.user_data['previous_messages'] = [active_message_id]

                # Логируем результаты
                self.logger.info(
                    f"Очистка чата {chat_id}: удалено {successful}, не удалось {failed}, "
                    f"типы ошибок: {error_types}"
                )

            except Exception as e:
                self.logger.error(f"Критическая ошибка при очистке чата: {str(e)}")
                # В случае ошибки очищаем список сообщений принудительно
                context.user_data['previous_messages'] = []
                if active_message_id:
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

        # Очищаем сообщения
        self.clear_chat_history(update, context, preserve_message_id=active_message_id)

        # Вторая попытка очистки для максимальной надежности
        time.sleep(0.5)
        self.clear_chat_history(update, context, preserve_message_id=active_message_id)
        
    def clear_chat_client_side(self, update, context):
        """
        Очищает чат на стороне клиента с помощью API Telegram.
        Отправляет команду /clearcache, которая очищает локальный кэш истории в клиенте Telegram.
        
        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
            
        Returns:
            bool: True если команда была отправлена успешно, False в противном случае
        """
        if not update or not context or not update.effective_chat:
            self.logger.warning("Недостаточно данных для очистки чата на стороне клиента")
            return False
            
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id if update.effective_user else "Неизвестный"
        
        try:
            # Отправляем специальную команду для очистки кэша истории сообщений
            message = context.bot.send_message(chat_id=chat_id, text="/clearcache")
            
            # Логирование успешной отправки команды
            self.logger.info(f"Отправлена команда очистки кэша для пользователя {user_id}")
            
            # После отправки команды очистки можно удалить сообщение с командой
            time.sleep(0.5)
            try:
                context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
            except Exception as e:
                self.logger.debug(f"Не удалось удалить сообщение с командой очистки: {e}")
                
            # Можно отправить подтверждение очистки
            context.bot.send_message(chat_id=chat_id, text="🧹 История чата очищена на стороне клиента")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при очистке чата на стороне клиента: {e}")
            return False