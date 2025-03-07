import os
import json
import logging
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

class AdminPanel:
    """Класс для управления админ-панелью бота"""

    def __init__(self, logger, config):
        self.logger = logger
        self.config = config
        self.admins_file = 'admins.json' # Added for clarity and consistency
        self.admins = self._load_admins()

    def _load_admins(self):
        """Загружает список администраторов из файла с обработкой ошибок и кэшированием"""
        try:
            if not hasattr(self, '_admin_cache'):
                self._admin_cache = None
                self._admin_cache_time = 0

            # Используем кэш, если он актуален (не старше 5 минут)
            current_time = time.time()
            if self._admin_cache and current_time - self._admin_cache_time < 300:
                return self._admin_cache

            if os.path.exists(self.admins_file):
                with open(self.admins_file, 'r', encoding='utf-8') as f:
                    admin_data = json.load(f)
                    # Обновляем кэш
                    self._admin_cache = admin_data
                    self._admin_cache_time = current_time
                    return admin_data

            # Создаем структуру данных по умолчанию
            default_data = {"admin_ids": [], "super_admin_ids": []}
            self._admin_cache = default_data
            self._admin_cache_time = current_time
            return default_data
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке списка администраторов: {e}")
            return {"admin_ids": [], "super_admin_ids": []}

    def save_admins(self):
        """Сохраняет список администраторов в файл с защитой от повреждения"""
        try:
            # Используем атомарную операцию записи через временный файл
            temp_file = f"{self.admins_file}.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.admins, f, indent=4)

            # Заменяем основной файл только после успешной записи
            os.replace(temp_file, self.admins_file)

            # Обновляем кэш
            self._admin_cache = self.admins.copy()
            self._admin_cache_time = time.time()
            return True #Added return for consistency
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении списка администраторов: {e}")
            return False #Added return for consistency

    def is_admin(self, user_id):
        """Проверяет, является ли пользователь администратором"""
        return user_id in self.admins.get("admin_ids", []) or user_id in self.admins.get("super_admin_ids", [])

    def is_super_admin(self, user_id):
        """Проверяет, является ли пользователь супер-администратором"""
        return user_id in self.admins.get("super_admin_ids", [])

    def add_admin(self, user_id, by_user_id=None, is_super=False):
        """Добавляет нового администратора"""
        try:
            if is_super:
                if user_id not in self.admins.get("super_admin_ids", []):
                    self.admins.setdefault("super_admin_ids", []).append(user_id)
                    self.logger.info(f"Добавлен супер-админ: {user_id}, добавил: {by_user_id}")
            else:
                if user_id not in self.admins.get("admin_ids", []):
                    self.admins.setdefault("admin_ids", []).append(user_id)
                    self.logger.info(f"Добавлен админ: {user_id}, добавил: {by_user_id}")

            return self.save_admins()
        except Exception as e:
            self.logger.error(f"Ошибка при добавлении администратора: {e}")
            return False

    def remove_admin(self, user_id, by_user_id=None):
        """Удаляет администратора"""
        try:
            if user_id in self.admins.get("admin_ids", []):
                self.admins["admin_ids"].remove(user_id)
                self.logger.info(f"Удален админ: {user_id}, удалил: {by_user_id}")
                return self.save_admins()
            elif user_id in self.admins.get("super_admin_ids", []):
                self.admins["super_admin_ids"].remove(user_id)
                self.logger.info(f"Удален супер-админ: {user_id}, удалил: {by_user_id}")
                return self.save_admins()
            return False
        except Exception as e:
            self.logger.error(f"Ошибка при удалении администратора: {e}")
            return False

    def handle_admin_command(self, update: Update, context: CallbackContext):
        """Обрабатывает команду /admin"""
        user_id = update.effective_user.id

        if not self.is_admin(user_id):
            update.message.reply_text("У вас нет прав администратора.")
            self.logger.warning(f"Пользователь {user_id} попытался получить доступ к админ-панели без прав")
            return

        # Показываем админ-панель
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
            [InlineKeyboardButton("👥 Управление админами", callback_data='admin_manage')],
            [InlineKeyboardButton("📝 Просмотр логов", callback_data='admin_logs')],
            [InlineKeyboardButton("🔄 Перезапустить бота", callback_data='admin_restart')]
        ]

        # Добавляем специальные функции для супер-админа
        if self.is_super_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ Настройки бота", callback_data='admin_settings')])
            keyboard.append([InlineKeyboardButton("🔧 Техническое обслуживание", callback_data='admin_maintenance')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            f"👑 *Панель администратора TeleAdmin*\n\n"
            f"Добро пожаловать, {update.effective_user.first_name}!\n"
            f"Выберите действие в меню ниже:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        self.logger.info(f"Админ {user_id} открыл панель управления")

    def handle_admin_callback(self, update: Update, context: CallbackContext):
        """Обрабатывает нажатия на кнопки в админ-панели"""
        query = update.callback_query
        user_id = query.from_user.id

        if not self.is_admin(user_id):
            query.answer("У вас нет прав администратора.")
            self.logger.warning(f"Пользователь {user_id} попытался использовать функции админ-панели без прав")
            return

        query.answer()
        action = query.data

        if action == 'admin_stats':
            self._show_stats(query, context)
        elif action == 'admin_manage':
            self._show_admin_management(query, context)
        elif action == 'admin_logs':
            self._show_logs(query, context)
        elif action == 'admin_restart':
            self._restart_bot(query, context)
        elif action == 'admin_settings' and self.is_super_admin(user_id):
            self._show_settings(query, context)
        elif action == 'admin_maintenance' and self.is_super_admin(user_id):
            self._show_maintenance(query, context)
        elif action == 'admin_back':
            # Возврат в главное меню админ-панели
            self._back_to_admin_menu(query, context)
        elif action.startswith('admin_add_'):
            # Обработка добавления админа
            self._handle_add_admin(query, context, action)
        elif action.startswith('admin_remove_'):
            # Обработка удаления админа
            self._handle_remove_admin(query, context, action)

    def _show_stats(self, query, context):
        """Показывает статистику бота"""
        try:
            # Подсчет количества сообщений и пользователей
            user_count = self._count_users()
            message_count = self._count_messages()

            stats_text = (
                "📊 *Статистика бота*\n\n"
                f"👥 Уникальных пользователей: {user_count}\n"
                f"💬 Всего сообщений: {message_count}\n"
                f"⏱️ Время работы: {self._get_uptime()}\n\n"
                f"*Пользовательская активность за последние 24 часа:*\n"
                f"🔄 Запусков бота: {self._count_bot_starts()}\n"
                f"📝 Запросов тем: {self._count_topic_requests()}\n"
                f"✅ Пройдено тестов: {self._count_completed_tests()}\n"
            )

            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                stats_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            self.logger.info(f"Админ {query.from_user.id} просмотрел статистику")
        except Exception as e:
            self.logger.error(f"Ошибка при отображении статистики: {e}")
            query.edit_message_text(
                f"Ошибка при загрузке статистики: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]])
            )

    def _show_admin_management(self, query, context):
        """Показывает интерфейс управления администраторами"""
        try:
            admins = self.admins.get("admin_ids", [])
            super_admins = self.admins.get("super_admin_ids", [])

            admin_text = "👥 *Управление администраторами*\n\n"

            # Список супер-админов
            admin_text += "*Супер-администраторы:*\n"
            if super_admins:
                for i, admin_id in enumerate(super_admins, 1):
                    admin_text += f"{i}. ID: {admin_id}\n"
            else:
                admin_text += "Нет супер-администраторов\n"

            # Список обычных админов
            admin_text += "\n*Администраторы:*\n"
            if admins:
                for i, admin_id in enumerate(admins, 1):
                    admin_text += f"{i}. ID: {admin_id}\n"
            else:
                admin_text += "Нет администраторов\n"

            # Кнопки управления
            keyboard = [
                [InlineKeyboardButton("➕ Добавить админа", callback_data='admin_add_regular')],
                [InlineKeyboardButton("➕ Добавить супер-админа", callback_data='admin_add_super')],
                [InlineKeyboardButton("➖ Удалить админа", callback_data='admin_remove_admin')],
                [InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            query.edit_message_text(
                admin_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

            self.logger.info(f"Админ {query.from_user.id} открыл управление администраторами")
        except Exception as e:
            self.logger.error(f"Ошибка при отображении управления администраторами: {e}")
            query.edit_message_text(
                f"Ошибка при загрузке управления администраторами: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]])
            )

    def _show_logs(self, query, context):
        """Показывает последние записи логов"""
        try:
            log_content = self._get_last_logs(100)  # Получаем последние 100 строк логов

            # Разбиваем на части, если слишком длинное сообщение
            max_length = 4000
            log_parts = []

            current_part = "📝 *Последние записи логов*\n\n```"
            for log_line in log_content:
                if len(current_part) + len(log_line) + 4 > max_length:  # +4 для учета ```
                    current_part += "```"
                    log_parts.append(current_part)
                    current_part = "```\n" + log_line
                else:
                    current_part += log_line

            if current_part:
                current_part += "```"
                log_parts.append(current_part)

            # Отправляем первую часть с кнопкой назад
            query.edit_message_text(
                log_parts[0] if log_parts else "Логи отсутствуют",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]]),
                parse_mode='Markdown'
            )

            # Отправляем остальные части, если они есть
            for part in log_parts[1:]:
                context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=part,
                    parse_mode='Markdown'
                )

            self.logger.info(f"Админ {query.from_user.id} просмотрел логи")
        except Exception as e:
            self.logger.error(f"Ошибка при отображении логов: {e}")
            query.edit_message_text(
                f"Ошибка при загрузке логов: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]])
            )

    def _restart_bot(self, query, context):
        """Перезапуск бота"""
        user_id = query.from_user.id

        # Проверяем права доступа (нужны права админа)
        if not self.is_admin(user_id):
            query.answer("У вас нет прав для перезапуска бота")
            return

        query.edit_message_text(
            "🔄 *Перезапуск бота*\n\n"
            "Вы уверены, что хотите перезапустить бота? "
            "Это приведет к кратковременной недоступности сервиса.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Да", callback_data='admin_restart_confirm'),
                    InlineKeyboardButton("❌ Нет", callback_data='admin_back')
                ]
            ]),
            parse_mode='Markdown'
        )

    def _show_settings(self, query, context):
        """Показывает настройки бота (только для супер-админов)"""
        user_id = query.from_user.id

        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав супер-администратора")
            return

        # Получаем текущие настройки
        settings = self._get_bot_settings()

        settings_text = (
            "⚙️ *Настройки бота*\n\n"
            f"🔄 Автоматическое обновление тем: {'Включено' if settings.get('auto_update_topics', True) else 'Выключено'}\n"
            f"📊 Сбор статистики: {'Включено' if settings.get('collect_statistics', True) else 'Выключено'}\n"
            f"🔍 Режим разработчика: {'Включено' if settings.get('developer_mode', False) else 'Выключено'}\n"
            f"🔐 Приватный режим: {'Включено' if settings.get('private_mode', False) else 'Выключено'}\n"
        )

        keyboard = [
            [InlineKeyboardButton("🔄 Автоматическое обновление тем", callback_data='admin_toggle_auto_update')],
            [InlineKeyboardButton("📊 Сбор статистики", callback_data='admin_toggle_statistics')],
            [InlineKeyboardButton("🔍 Режим разработчика", callback_data='admin_toggle_dev_mode')],
            [InlineKeyboardButton("🔐 Приватный режим", callback_data='admin_toggle_private_mode')],
            [InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            settings_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        self.logger.info(f"Супер-админ {query.from_user.id} открыл настройки бота")

    def _show_maintenance(self, query, context):
        """Показывает меню технического обслуживания (только для супер-админов)"""
        user_id = query.from_user.id

        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав супер-администратора")
            return

        maintenance_text = (
            "🔧 *Техническое обслуживание*\n\n"
            "Выберите действие из списка ниже:"
        )

        keyboard = [
            [InlineKeyboardButton("🗑️ Очистить кэш", callback_data='admin_clear_cache')],
            [InlineKeyboardButton("💾 Резервное копирование", callback_data='admin_backup')],
            [InlineKeyboardButton("🔄 Обновить данные API", callback_data='admin_update_api')],
            [InlineKeyboardButton("🧹 Очистка логов", callback_data='admin_clean_logs')],
            [InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            maintenance_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        self.logger.info(f"Супер-админ {query.from_user.id} открыл меню технического обслуживания")

    def _back_to_admin_menu(self, query, context):
        """Возвращает пользователя в главное меню админ-панели"""
        user_id = query.from_user.id

        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data='admin_stats')],
            [InlineKeyboardButton("👥 Управление админами", callback_data='admin_manage')],
            [InlineKeyboardButton("📝 Просмотр логов", callback_data='admin_logs')],
            [InlineKeyboardButton("🔄 Перезапустить бота", callback_data='admin_restart')]
        ]

        # Добавляем специальные функции для супер-админа
        if self.is_super_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ Настройки бота", callback_data='admin_settings')])
            keyboard.append([InlineKeyboardButton("🔧 Техническое обслуживание", callback_data='admin_maintenance')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            f"👑 *Панель администратора TeleAdmin*\n\n"
            f"Добро пожаловать, {query.from_user.first_name}!\n"
            f"Выберите действие в меню ниже:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    def _handle_add_admin(self, query, context, action):
        """Обрабатывает добавление нового администратора"""
        user_id = query.from_user.id

        # Проверка прав доступа (нужны права супер-админа для добавления админов)
        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав для добавления администраторов")
            return

        # Определяем тип добавляемого админа
        is_super = action == 'admin_add_super'
        admin_type = "супер-администратора" if is_super else "администратора"

        query.edit_message_text(
            f"➕ *Добавление {admin_type}*\n\n"
            f"Для добавления нового {admin_type}, отправьте его Telegram ID в следующем сообщении.\n\n"
            f"Чтобы отменить, нажмите кнопку ниже.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Отмена", callback_data='admin_back')]]),
            parse_mode='Markdown'
        )

        # Сохраняем контекст для следующего сообщения
        context.user_data['waiting_for_admin_id'] = is_super

        self.logger.info(f"Админ {user_id} инициировал добавление нового {admin_type}")

    def _handle_remove_admin(self, query, context, action):
        """Обрабатывает удаление администратора"""
        user_id = query.from_user.id

        # Проверка прав доступа (нужны права супер-админа для удаления админов)
        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав для удаления администраторов")
            return

        # Формируем список админов для удаления
        admins = self.admins.get("admin_ids", [])
        super_admins = self.admins.get("super_admin_ids", [])

        if not admins and not super_admins:
            query.edit_message_text(
                "В системе нет администраторов для удаления",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]])
            )
            return

        # Создаем клавиатуру с кнопками для выбора админа для удаления
        keyboard = []

        # Добавляем супер-админов
        for admin_id in super_admins:
            if admin_id != user_id:  # Не даем удалить самого себя
                keyboard.append([InlineKeyboardButton(f"Супер-админ: {admin_id}", callback_data=f'admin_delete_{admin_id}')])

        # Добавляем обычных админов
        for admin_id in admins:
            keyboard.append([InlineKeyboardButton(f"Админ: {admin_id}", callback_data=f'admin_delete_{admin_id}')])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data='admin_back')])

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            "👥 *Удаление администратора*\n\n"
            "Выберите администратора для удаления из списка ниже:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        self.logger.info(f"Админ {user_id} открыл меню удаления администраторов")

    # Вспомогательные методы для работы с данными

    def _count_users(self):
        """Подсчитывает количество уникальных пользователей"""
        try:
            # Заглушка, нужно реализовать фактический подсчет из базы данных
            return 42  # Пример
        except Exception:
            return 0

    def _count_messages(self):
        """Подсчитывает общее количество сообщений"""
        try:
            # Заглушка, нужно реализовать фактический подсчет из базы данных
            return 1337  # Пример
        except Exception:
            return 0

    def _get_uptime(self):
        """Возвращает время работы бота"""
        try:
            # Заглушка, нужно реализовать фактический подсчет времени работы
            return "3 дня 7 часов"  # Пример
        except Exception:
            return "Неизвестно"

    def _count_bot_starts(self):
        """Подсчитывает количество запусков бота за последние 24 часа"""
        try:
            # Заглушка, нужно реализовать фактический подсчет из логов
            return 25  # Пример
        except Exception:
            return 0

    def _count_topic_requests(self):
        """Подсчитывает количество запросов тем за последние 24 часа"""
        try:
            # Заглушка, нужно реализовать фактический подсчет из логов
            return 73  # Пример
        except Exception:
            return 0

    def _count_completed_tests(self):
        """Подсчитывает количество пройденных тестов за последние 24 часа"""
        try:
            # Заглушка, нужно реализовать фактический подсчет из логов
            return 18  # Пример
        except Exception:
            return 0

    def _get_last_logs(self, lines=100):
        """Получает последние строки из файла логов"""
        try:
            log_files = []
            log_dir = "logs"

            # Проверяем, существует ли директория логов
            if os.path.exists(log_dir) and os.path.isdir(log_dir):
                # Получаем список файлов логов
                files = os.listdir(log_dir)
                log_files = [os.path.join(log_dir, f) for f in files if f.startswith("bot_log_")]

            # Если директории нет или нет файлов логов, проверяем в корневой директории
            if not log_files:
                files = [f for f in os.listdir() if f.startswith("bot_log_")]
                log_files = files

            # Сортируем файлы по дате изменения (новые в начале)
            log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

            if not log_files:
                return ["Файлы логов не найдены"]

            # Берем самый свежий файл логов
            latest_log = log_files[0]

            with open(latest_log, 'r', encoding='utf-8') as f:
                # Получаем последние lines строк
                return list(f)[-lines:]
        except Exception as e:
            self.logger.error(f"Ошибка при чтении файла логов: {e}")
            return [f"Ошибка при чтении логов: {e}"]

    def _get_bot_settings(self):
        """Получает текущие настройки бота"""
        try:
            if os.path.exists('bot_settings.json'):
                with open('bot_settings.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Возвращаем настройки по умолчанию
                return {
                    "auto_update_topics": True,
                    "collect_statistics": True,
                    "developer_mode": False,
                    "private_mode": False
                }
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке настроек бота: {e}")
            return {}

    def process_new_admin_id(self, update, context):
        """Обрабатывает ввод ID нового администратора"""
        user_id = update.effective_user.id

        # Проверяем, что пользователь является супер-админом
        if not self.is_super_admin(user_id):
            update.message.reply_text("У вас нет прав для добавления администраторов")
            return

        # Проверяем, ожидаем ли мы ID нового администратора
        if 'waiting_for_admin_id' not in context.user_data:
            update.message.reply_text("Ошибка: не инициирован процесс добавления администратора")
            return

        is_super = context.user_data.get('waiting_for_admin_id')
        admin_type = "супер-администратора" if is_super else "администратора"

        # Очищаем состояние ожидания
        del context.user_data['waiting_for_admin_id']

        # Парсим ID из сообщения
        try:
            new_admin_id = int(update.message.text.strip())
        except ValueError:
            update.message.reply_text(
                f"❌ Ошибка: ID администратора должен быть числом.\n"
                f"Попробуйте снова через меню администратора.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К админ-панели", callback_data='admin_back')]])
            )
            return

        # Проверяем, не существует ли уже такой админ
        if new_admin_id in self.admins.get("admin_ids", []) or new_admin_id in self.admins.get("super_admin_ids", []):
            update.message.reply_text(
                f"❌ Ошибка: пользователь с ID {new_admin_id} уже является администратором.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К админ-панели", callback_data='admin_back')]])
            )
            return

        # Добавляем нового админа
        success = self.add_admin(new_admin_id, by_user_id=user_id, is_super=is_super)

        if success:
            update.message.reply_text(
                f"✅ {admin_type.capitalize()} с ID {new_admin_id} успешно добавлен!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К админ-панели", callback_data='admin_back')]])
            )
            self.logger.info(f"Админ {user_id} добавил нового {admin_type} с ID {new_admin_id}")
        else:
            update.message.reply_text(
                f"❌ Ошибка при добавлении {admin_type}. Попробуйте снова позже.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К админ-панели", callback_data='admin_back')]])
            )

    def handle_delete_admin_callback(self, update, context, admin_id_to_delete):
        """Обрабатывает удаление администратора по callback"""
        query = update.callback_query
        user_id = query.from_user.id

        # Проверяем права доступа
        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав для удаления администраторов")
            return

        # Проверяем, не пытается ли админ удалить самого себя
        if int(admin_id_to_delete) == user_id:
            query.answer("Вы не можете удалить самого себя")
            return

        # Удаляем администратора
        success = self.remove_admin(int(admin_id_to_delete), by_user_id=user_id)

        if success:
            query.answer(f"Администратор с ID {admin_id_to_delete} успешно удален!")
            self.logger.info(f"Админ {user_id} удалил администратора с ID {admin_id_to_delete}")

            # Возвращаемся к списку администраторов
            self._show_admin_management(query, context)
        else:
            query.answer(f"Ошибка при удалении администратора с ID {admin_id_to_delete}")