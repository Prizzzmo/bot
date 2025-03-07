
import time
import telegram
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class MessageManager:
    """Класс для управления сообщениями в чате"""
    
    def __init__(self, logger):
        self.logger = logger
        
    def save_message_id(self, update, context, message_id):
        """
        Сохраняет ID сообщения в список предыдущих сообщений.
        Улучшенная версия с проверкой дубликатов и валидацией ID.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
            message_id (int): ID сообщения для сохранения
        """
        if not context or not hasattr(context, 'user_data'):
            self.logger.warning("Попытка сохранить ID сообщения без контекста пользователя")
            return
            
        if not message_id or not isinstance(message_id, int):
            self.logger.warning(f"Попытка сохранить некорректный ID сообщения: {message_id}")
            return
            
        # Инициализация списка, если его нет
        if 'previous_messages' not in context.user_data:
            context.user_data['previous_messages'] = []
        
        # Проверка на дубликаты перед добавлением
        if message_id not in context.user_data['previous_messages']:
            context.user_data['previous_messages'].append(message_id)
            
        # Ограничиваем список последними сообщениями
        max_saved_messages = 50
        if len(context.user_data['previous_messages']) > max_saved_messages:
            # Усовершенствованный способ хранения - оставляем последние сообщения,
            # так как они с большей вероятностью будут успешно удалены
            context.user_data['previous_messages'] = context.user_data['previous_messages'][-max_saved_messages:]
    
    def clear_chat_history(self, update, context, preserve_message_id=None):
        """
        Очищает историю чата, удаляя все предыдущие сообщения бота.
        
        Функция выполняет полную очистку истории сообщений в чате, с возможностью
        сохранения одного конкретного сообщения (если указан его ID).
        Оптимизирована для работы с API Telegram с учетом ограничений по частоте запросов.

        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
            preserve_message_id (int, optional): ID сообщения, которое нужно сохранить
        """
        # Проверка обязательных параметров
        if not update or not update.effective_chat or not context:
            self.logger.warning("Вызов очистки чата с неполными параметрами")
            return
            
        try:
            # Получаем ID чата
            chat_id = update.effective_chat.id
            
            # Получаем ID активного сообщения (по умолчанию текущее сообщение или то, что нужно сохранить)
            active_message_id = preserve_message_id
            if not active_message_id:
                if update.message:
                    active_message_id = update.message.message_id
                elif update.callback_query and update.callback_query.message:
                    active_message_id = update.callback_query.message.message_id
            
            # Проверка на наличие данных пользователя
            if 'previous_messages' not in context.user_data:
                context.user_data['previous_messages'] = []
                return

            # Получаем и очищаем список сохраненных ID сообщений
            message_ids = context.user_data.get('previous_messages', [])
            if not message_ids:
                return

            # Удаляем дубликаты
            message_ids = list(set(message_ids))
            
            # Исключаем активное сообщение из списка удаления, если оно есть
            if active_message_id and active_message_id in message_ids:
                message_ids.remove(active_message_id)
                self.logger.debug(f"Активное сообщение {active_message_id} исключено из очистки")
            
            # Сортируем по убыванию (сначала новые сообщения)
            # Это важно, так как новые сообщения с большей вероятностью будут удалены успешно
            message_ids.sort(reverse=True)
            
            # Telegram имеет ограничения на частоту запросов (не более 30 в секунду)
            # Также учитываем, что старые сообщения (>48 часов) могут быть недоступны
            max_messages_to_delete = min(len(message_ids), 200)  # Увеличено с 100 до 200
            message_ids = message_ids[:max_messages_to_delete]
            
            # Словарь для отслеживания статуса удаления сообщений
            deletion_status = {msg_id: False for msg_id in message_ids}
            
            # Определяем типы ошибок для более точной обработки
            telegram_error_types = {
                'message to delete not found': 'already_deleted',
                'message can\'t be deleted': 'permission_denied',
                'message to edit not found': 'already_deleted',
                'message is not modified': 'not_modified',
                'message too long': 'message_too_long',
                'bot was blocked by the user': 'user_blocked_bot',
                'chat not found': 'chat_not_found',
                'forbidden': 'forbidden',
                'flood control': 'flood_control'
            }
            
            # Функция для классификации ошибок Telegram
            def classify_telegram_error(error_text):
                error_text = str(error_text).lower()
                for key, value in telegram_error_types.items():
                    if key in error_text:
                        return value
                return 'unknown_telegram_error'
            
            count_deleted = 0
            retry_count = 0
            failure_reasons = {}
            
            def delete_message_with_retry(msg_id, max_retries=2, delay=0.5):
                """Удаляет сообщение с повторными попытками в случае ошибок скорости"""
                nonlocal count_deleted, retry_count, failure_reasons
                
                # Повторная проверка, не является ли это активным сообщением
                if msg_id == active_message_id:
                    self.logger.debug(f"Пропуск удаления активного сообщения {msg_id}")
                    return False
                    
                for attempt in range(max_retries + 1):
                    try:
                        context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
                        count_deleted += 1
                        deletion_status[msg_id] = True
                        return True
                    except telegram.error.RetryAfter as ra:
                        # Ошибка скорости - ждем и пробуем снова
                        retry_count += 1
                        retry_seconds = min(ra.retry_after + 0.5, 3)  # Не ждем больше 3 секунд
                        self.logger.debug(f"Достигнут лимит скорости, ожидание {retry_seconds} сек перед повторной попыткой")
                        time.sleep(retry_seconds)
                        # Продолжаем цикл для следующей попытки
                    except telegram.error.TelegramError as te:
                        # Анализируем причину ошибки
                        error_type = classify_telegram_error(str(te))
                        
                        # Считаем различные типы ошибок
                        if error_type not in failure_reasons:
                            failure_reasons[error_type] = 0
                        failure_reasons[error_type] += 1
                        
                        # Некоторые ошибки не требуют повторных попыток
                        if error_type in ['already_deleted', 'permission_denied', 'not_modified']:
                            return False
                        
                        # Для других ошибок пробуем повторить с задержкой
                        if attempt < max_retries:
                            time.sleep(delay)
                        else:
                            return False
                    except Exception as e:
                        # Общие ошибки
                        self.logger.debug(f"Не удалось удалить сообщение {msg_id}: {str(e)}")
                        return False
                
                return False
            
            # Размер пакета для удаления (Telegram имеет ограничения на частоту запросов)
            batch_size = 5
            
            # Используем ThreadPoolExecutor вместо обычных потоков для лучшего контроля
            with ThreadPoolExecutor(max_workers=3) as executor:
                # Разбиваем сообщения на пакеты для избежания ограничений API
                for i in range(0, len(message_ids), batch_size):
                    batch = message_ids[i:i+batch_size]
                    
                    # Запускаем удаление для каждого сообщения в пакете
                    futures = {executor.submit(delete_message_with_retry, msg_id): msg_id for msg_id in batch}
                    
                    # Ждем выполнения всех задач в пакете с таймаутом
                    for future in as_completed(futures, timeout=5):
                        msg_id = futures[future]
                        try:
                            result = future.result()
                        except Exception as e:
                            self.logger.debug(f"Ошибка при удалении сообщения {msg_id}: {str(e)}")
                    
                    # Небольшая задержка между пакетами
                    if i + batch_size < len(message_ids):
                        time.sleep(0.5)
            
            # Очищаем список предыдущих сообщений полностью, оставляя только активное сообщение
            if active_message_id:
                context.user_data['previous_messages'] = [active_message_id]
            else:
                context.user_data['previous_messages'] = []
            
            # Логирование результатов с подробной информацией
            if count_deleted > 0 or failure_reasons:
                log_message = f"Полная очистка чата {chat_id}: удалено {count_deleted} из {len(message_ids)} сообщений, сохранено сообщение: {active_message_id}"
                if retry_count:
                    log_message += f", повторных попыток: {retry_count}"
                if failure_reasons:
                    log_message += f", причины ошибок: {failure_reasons}"
                self.logger.info(log_message)
                
        except Exception as e:
            self.logger.error(f"Критическая ошибка при полной очистке истории чата: {str(e)}")
    
    def clean_all_messages_except_active(self, update, context):
        """
        Удобная функция для полной очистки чата, оставляя только текущее активное сообщение.
        
        Args:
            update (telegram.Update): Объект обновления Telegram
            context (telegram.ext.CallbackContext): Контекст разговора
        """
        # Определяем ID активного сообщения
        active_message_id = None
        if update.message:
            active_message_id = update.message.message_id
        elif update.callback_query and update.callback_query.message:
            active_message_id = update.callback_query.message.message_id
        
        # Запускаем полную очистку с сохранением активного сообщения
        self.clear_chat_history(update, context, preserve_message_id=active_message_id)
