
import os
import json
import logging
import time
import threading
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, ContextTypes
import datetime
import sys
import signal
import psutil

class AdminPanel:
    """Класс для управления админ-панелью бота"""

    def __init__(self, logger, config, analytics=None, api_client=None, topic_service=None):
        self.logger = logger
        self.config = config
        self.admins_file = 'admins.json'
        self.admins = self._load_admins()
        self.analytics = analytics
        self.api_client = api_client
        self.topic_service = topic_service
        self.start_time = time.time()
        
        # Проверяем наличие файла настроек бота
        if not os.path.exists('bot_settings.json'):
            self._create_default_settings()

    def _create_default_settings(self):
        """Создает файл настроек по умолчанию"""
        default_settings = {
            "auto_update_topics": True,
            "collect_statistics": True,
            "developer_mode": False,
            "private_mode": False,
            "log_level": "INFO",
            "max_messages_per_user": 100,
            "notification_enabled": True
        }
        
        try:
            with open('bot_settings.json', 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, indent=4)
            self.logger.info("Создан файл настроек по умолчанию")
        except Exception as e:
            self.logger.error(f"Ошибка при создании файла настроек: {e}")

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
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении списка администраторов: {e}")
            return False

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
        elif action == 'admin_restart_confirm':
            self._restart_bot_confirm(query, context)
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
        elif action == 'admin_clear_cache':
            # Очистка кэша
            self._clear_cache(query, context)
        elif action == 'admin_backup':
            # Резервное копирование
            self._create_backup(query, context)
        elif action == 'admin_update_api':
            # Обновление данных API
            self._update_api_data(query, context)
        elif action == 'admin_clean_logs':
            # Очистка логов
            self._clean_logs(query, context)
        elif action.startswith('admin_toggle_'):
            # Переключение настроек
            self._toggle_setting(query, context, action.replace('admin_toggle_', ''))
        elif action == 'admin_system_info':
            # Информация о системе
            self._show_system_info(query, context)
        elif action == 'admin_user_stats':
            # Статистика пользователей
            self._show_user_stats(query, context)

    def _show_stats(self, query, context):
        """Показывает статистику бота"""
        try:
            # Получаем статистику
            user_count = self._count_users()
            message_count = self._count_messages()
            uptime = self._get_uptime()
            bot_starts = self._count_bot_starts()
            topic_requests = self._count_topic_requests()
            completed_tests = self._count_completed_tests()

            # Получаем данные по популярным темам, если сервис темы доступен
            popular_topics = "Нет данных"
            if self.topic_service:
                try:
                    topics = self.topic_service.get_popular_topics(5)
                    if topics:
                        popular_topics = "\n".join([f"{i+1}. {topic}" for i, topic in enumerate(topics)])
                except Exception as e:
                    self.logger.error(f"Ошибка при получении популярных тем: {e}")
                    popular_topics = f"Ошибка: {str(e)}"

            # Формируем текст статистики
            stats_text = (
                "📊 *Статистика бота*\n\n"
                f"👥 Уникальных пользователей: {user_count}\n"
                f"💬 Всего сообщений: {message_count}\n"
                f"⏱️ Время работы: {uptime}\n\n"
                f"*Пользовательская активность за последние 24 часа:*\n"
                f"🔄 Запусков бота: {bot_starts}\n"
                f"📝 Запросов тем: {topic_requests}\n"
                f"✅ Пройдено тестов: {completed_tests}\n\n"
                f"*Популярные темы:*\n{popular_topics}"
            )

            # Создаем клавиатуру с дополнительными опциями
            keyboard = [
                [InlineKeyboardButton("📈 Подробная статистика пользователей", callback_data='admin_user_stats')],
                [InlineKeyboardButton("💻 Информация о системе", callback_data='admin_system_info')],
                [InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]
            ]
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

    def _show_system_info(self, query, context):
        """Показывает информацию о системе"""
        try:
            # Получаем информацию о системе
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Получаем список процессов Python
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent']):
                if 'python' in proc.info['name'].lower():
                    python_processes.append(proc)
            
            # Сортируем по использованию памяти
            python_processes.sort(key=lambda x: x.info['memory_percent'], reverse=True)
            
            # Формируем строку с информацией о процессах
            processes_info = ""
            for i, proc in enumerate(python_processes[:5], 1):
                try:
                    mem_usage = proc.memory_info().rss / (1024 * 1024)
                    processes_info += f"{i}. PID: {proc.info['pid']}, Память: {mem_usage:.2f} МБ\n"
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    processes_info += f"{i}. Процесс недоступен\n"
            
            if not processes_info:
                processes_info = "Нет активных Python процессов"
            
            # Формируем текст с информацией о системе
            system_text = (
                "💻 *Информация о системе*\n\n"
                f"*Процессор:*\n"
                f"Загрузка CPU: {cpu_percent}%\n\n"
                f"*Память:*\n"
                f"Всего: {mem.total / (1024 * 1024 * 1024):.2f} ГБ\n"
                f"Используется: {mem.used / (1024 * 1024 * 1024):.2f} ГБ ({mem.percent}%)\n"
                f"Свободно: {mem.free / (1024 * 1024 * 1024):.2f} ГБ\n\n"
                f"*Диск:*\n"
                f"Всего: {disk.total / (1024 * 1024 * 1024):.2f} ГБ\n"
                f"Используется: {disk.used / (1024 * 1024 * 1024):.2f} ГБ ({disk.percent}%)\n"
                f"Свободно: {disk.free / (1024 * 1024 * 1024):.2f} ГБ\n\n"
                f"*Python процессы (топ 5):*\n{processes_info}"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 К статистике", callback_data='admin_stats')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                system_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            self.logger.info(f"Админ {query.from_user.id} просмотрел информацию о системе")
        except Exception as e:
            self.logger.error(f"Ошибка при отображении информации о системе: {e}")
            query.edit_message_text(
                f"Ошибка при загрузке информации о системе: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К статистике", callback_data='admin_stats')]])
            )

    def _show_user_stats(self, query, context):
        """Показывает подробную статистику пользователей"""
        try:
            # Получаем статистику из Analytics, если доступно
            if self.analytics:
                try:
                    # Статистика активных пользователей по дням недели
                    daily_users = self.analytics.get_active_users_by_day()
                    
                    # Статистика по времени суток
                    hourly_users = self.analytics.get_active_users_by_hour()
                    
                    # Успеваемость пользователей в тестах
                    test_stats = self.analytics.get_test_completion_stats()
                    
                    # Формируем строки для статистики
                    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                    days_stats = "\n".join([f"{days[i]}: {count} пользователей" for i, count in enumerate(daily_users)])
                    
                    # Формируем строки для часов (группируем по 4 часа)
                    hours_grouped = [
                        sum(hourly_users[0:6]),  # 0-6
                        sum(hourly_users[6:12]),  # 6-12
                        sum(hourly_users[12:18]),  # 12-18
                        sum(hourly_users[18:24])   # 18-24
                    ]
                    hours_stats = (
                        f"00:00-06:00: {hours_grouped[0]} пользователей\n"
                        f"06:00-12:00: {hours_grouped[1]} пользователей\n"
                        f"12:00-18:00: {hours_grouped[2]} пользователей\n"
                        f"18:00-00:00: {hours_grouped[3]} пользователей"
                    )
                    
                    # Статистика тестов
                    test_stats_text = (
                        f"Средний балл: {test_stats.get('avg_score', 0):.1f}%\n"
                        f"Пройдено тестов: {test_stats.get('completed_tests', 0)}\n"
                        f"Не завершено: {test_stats.get('abandoned_tests', 0)}"
                    )
                    
                except Exception as e:
                    self.logger.error(f"Ошибка при получении данных аналитики: {e}")
                    days_stats = "Нет данных"
                    hours_stats = "Нет данных"
                    test_stats_text = "Нет данных"
            else:
                days_stats = "Аналитика недоступна"
                hours_stats = "Аналитика недоступна"
                test_stats_text = "Аналитика недоступна"
            
            # Формируем текст с подробной статистикой
            stats_text = (
                "📈 *Подробная статистика пользователей*\n\n"
                f"*Активность по дням недели:*\n{days_stats}\n\n"
                f"*Активность по времени суток:*\n{hours_stats}\n\n"
                f"*Статистика тестов:*\n{test_stats_text}"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 К статистике", callback_data='admin_stats')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            query.edit_message_text(
                stats_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            self.logger.info(f"Админ {query.from_user.id} просмотрел подробную статистику пользователей")
        except Exception as e:
            self.logger.error(f"Ошибка при отображении подробной статистики пользователей: {e}")
            query.edit_message_text(
                f"Ошибка при загрузке подробной статистики: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К статистике", callback_data='admin_stats')]])
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

            # Добавляем кнопки для управления логами
            keyboard = [
                [InlineKeyboardButton("📉 Логи ошибок", callback_data='admin_logs_errors')],
                [InlineKeyboardButton("🧹 Очистить логи", callback_data='admin_clean_logs')],
                [InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Отправляем первую часть с кнопками
            query.edit_message_text(
                log_parts[0] if log_parts else "Логи отсутствуют",
                reply_markup=reply_markup,
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

    def _restart_bot_confirm(self, query, context):
        """Подтверждение перезапуска бота"""
        user_id = query.from_user.id

        if not self.is_admin(user_id):
            query.answer("У вас нет прав для перезапуска бота")
            return

        try:
            # Сообщаем о начале перезапуска
            query.edit_message_text(
                "🔄 *Перезапуск бота*\n\n"
                "Бот будет перезапущен через 5 секунд...\n"
                "Пожалуйста, подождите.",
                parse_mode='Markdown'
            )
            
            # Логируем действие
            self.logger.warning(f"Бот перезапускается администратором {user_id}")
            
            # Запускаем функцию перезапуска в отдельном потоке
            restart_thread = threading.Thread(target=self._perform_restart)
            restart_thread.daemon = True
            restart_thread.start()
            
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при перезапуске бота: {e}")
            query.edit_message_text(
                f"❌ Ошибка при перезапуске бота: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]])
            )
            return False

    def _perform_restart(self):
        """Выполняет фактический перезапуск бота"""
        try:
            # Ждем 5 секунд перед перезапуском
            time.sleep(5)
            
            # Создаем файл-индикатор для restart.sh скрипта
            with open("bot.restart", "w") as f:
                f.write(f"Restart triggered at {datetime.datetime.now()}")
            
            # Завершаем текущий процесс - скрипт перезапуска должен поднять бота снова
            os.kill(os.getpid(), signal.SIGTERM)
        except Exception as e:
            self.logger.error(f"Не удалось перезапустить бота: {e}")

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
            f"🔄 Автоматическое обновление тем: {'✅ Включено' if settings.get('auto_update_topics', True) else '❌ Выключено'}\n"
            f"📊 Сбор статистики: {'✅ Включено' if settings.get('collect_statistics', True) else '❌ Выключено'}\n"
            f"🔍 Режим разработчика: {'✅ Включено' if settings.get('developer_mode', False) else '❌ Выключено'}\n"
            f"🔐 Приватный режим: {'✅ Включено' if settings.get('private_mode', False) else '❌ Выключено'}\n"
            f"🔔 Уведомления: {'✅ Включены' if settings.get('notification_enabled', True) else '❌ Выключены'}\n"
            f"📝 Уровень логирования: {settings.get('log_level', 'INFO')}\n"
            f"👤 Макс. сообщений на пользователя: {settings.get('max_messages_per_user', 100)}"
        )

        keyboard = [
            [InlineKeyboardButton("🔄 Автоматическое обновление тем", callback_data='admin_toggle_auto_update')],
            [InlineKeyboardButton("📊 Сбор статистики", callback_data='admin_toggle_statistics')],
            [InlineKeyboardButton("🔍 Режим разработчика", callback_data='admin_toggle_dev_mode')],
            [InlineKeyboardButton("🔐 Приватный режим", callback_data='admin_toggle_private_mode')],
            [InlineKeyboardButton("🔔 Уведомления", callback_data='admin_toggle_notifications')],
            [InlineKeyboardButton("🔙 Назад", callback_data='admin_back')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            settings_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

        self.logger.info(f"Супер-админ {query.from_user.id} открыл настройки бота")

    def _toggle_setting(self, query, context, setting_key):
        """Переключает настройку бота"""
        user_id = query.from_user.id

        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав супер-администратора")
            return

        # Преобразуем ключ настройки в формат из файла настроек
        setting_map = {
            'auto_update': 'auto_update_topics',
            'statistics': 'collect_statistics',
            'dev_mode': 'developer_mode',
            'private_mode': 'private_mode',
            'notifications': 'notification_enabled'
        }
        
        setting_name = setting_map.get(setting_key)
        if not setting_name:
            query.answer(f"Неизвестная настройка: {setting_key}")
            return
        
        try:
            # Получаем текущие настройки
            settings = self._get_bot_settings()
            
            # Инвертируем значение настройки
            current_value = settings.get(setting_name, False)
            settings[setting_name] = not current_value
            
            # Сохраняем обновленные настройки
            self._save_bot_settings(settings)
            
            # Отображаем сообщение об успешном изменении
            new_value = "включена" if settings[setting_name] else "выключена"
            query.answer(f"Настройка {setting_name} {new_value}")
            
            # Обновляем экран настроек
            self._show_settings(query, context)
            
            self.logger.info(f"Супер-админ {user_id} изменил настройку {setting_name} на {settings[setting_name]}")
        except Exception as e:
            self.logger.error(f"Ошибка при изменении настройки {setting_key}: {e}")
            query.answer(f"Ошибка: {e}")

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

    def _clear_cache(self, query, context):
        """Очищает кэш API и другие временные данные"""
        user_id = query.from_user.id

        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав супер-администратора")
            return

        try:
            # Очищаем кэш API, если клиент доступен
            api_cache_cleared = False
            if self.api_client and hasattr(self.api_client, 'clear_cache'):
                self.api_client.clear_cache()
                api_cache_cleared = True
                self.logger.info(f"Админ {user_id} очистил кэш API")
            
            # Очищаем кэш тем, если сервис доступен
            topic_cache_cleared = False
            if self.topic_service and hasattr(self.topic_service, 'clear_cache'):
                self.topic_service.clear_cache()
                topic_cache_cleared = True
                self.logger.info(f"Админ {user_id} очистил кэш тем")

            # Проверяем файл кэша API
            api_cache_file = 'api_cache.json'
            if os.path.exists(api_cache_file):
                try:
                    os.remove(api_cache_file)
                    api_cache_file_removed = True
                    self.logger.info(f"Админ {user_id} удалил файл кэша API")
                except Exception as e:
                    api_cache_file_removed = False
                    self.logger.error(f"Ошибка при удалении файла кэша API: {e}")
            else:
                api_cache_file_removed = None

            # Формируем сообщение о результате
            result_text = "🗑️ *Очистка кэша*\n\n"
            
            if api_cache_cleared:
                result_text += "✅ Кэш API успешно очищен\n"
            else:
                result_text += "⚠️ API клиент недоступен или не поддерживает очистку кэша\n"
                
            if topic_cache_cleared:
                result_text += "✅ Кэш тем успешно очищен\n"
            else:
                result_text += "⚠️ Сервис тем недоступен или не поддерживает очистку кэша\n"
                
            if api_cache_file_removed is True:
                result_text += "✅ Файл кэша API успешно удален\n"
            elif api_cache_file_removed is False:
                result_text += "❌ Ошибка при удалении файла кэша API\n"
            elif api_cache_file_removed is None:
                result_text += "ℹ️ Файл кэша API не найден\n"
                
            # Отображаем результат
            query.edit_message_text(
                result_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_maintenance')]]),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при очистке кэша: {e}")
            query.edit_message_text(
                f"❌ Ошибка при очистке кэша: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_maintenance')]]),
                parse_mode='Markdown'
            )

    def _create_backup(self, query, context):
        """Создает резервную копию данных бота"""
        user_id = query.from_user.id

        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав супер-администратора")
            return

        try:
            # Сообщаем о начале создания резервной копии
            query.edit_message_text(
                "💾 *Создание резервной копии*\n\n"
                "Подождите, идет создание резервной копии данных...",
                parse_mode='Markdown'
            )
            
            # Текущее время для имени файла
            timestamp = int(time.time())
            backup_dir = "backups"
            
            # Создаем директорию для резервных копий, если она не существует
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            # Список файлов для резервного копирования
            files_to_backup = [
                'user_states.json',
                'historical_events.json',
                'admins.json',
                'bot_settings.json',
                'api_cache.json'
            ]
            
            # Копируем каждый файл в директорию резервных копий
            backup_files = []
            for file_name in files_to_backup:
                if os.path.exists(file_name):
                    backup_file_name = f"{file_name.split('.')[0]}_backup_{timestamp}.json"
                    backup_path = os.path.join(backup_dir, backup_file_name)
                    try:
                        import shutil
                        shutil.copy2(file_name, backup_path)
                        backup_files.append((file_name, backup_path))
                        self.logger.info(f"Создана резервная копия файла {file_name}")
                    except Exception as e:
                        self.logger.error(f"Ошибка при копировании файла {file_name}: {e}")
            
            # Также создаем общую резервную копию
            data_backup_path = os.path.join(backup_dir, f"data_backup_v{len(backup_files)}_{timestamp}")
            try:
                import zipfile
                with zipfile.ZipFile(data_backup_path + '.zip', 'w') as zipf:
                    for file_name in files_to_backup:
                        if os.path.exists(file_name):
                            zipf.write(file_name)
                    # Добавляем лог в архив
                    log_files = self._get_log_files()
                    if log_files:
                        zipf.write(log_files[0])
                self.logger.info(f"Создана общая резервная копия данных: {data_backup_path}.zip")
                backup_files.append(("Все данные", data_backup_path + '.zip'))
            except Exception as e:
                self.logger.error(f"Ошибка при создании общей резервной копии: {e}")
            
            # Формируем сообщение о результате
            result_text = "💾 *Резервное копирование завершено*\n\n"
            
            if backup_files:
                result_text += "Созданы следующие резервные копии:\n\n"
                for original, backup in backup_files:
                    result_text += f"• {original} → {os.path.basename(backup)}\n"
            else:
                result_text += "⚠️ Не удалось создать ни одной резервной копии."
            
            # Отображаем результат
            query.edit_message_text(
                result_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_maintenance')]]),
                parse_mode='Markdown'
            )
            
            self.logger.info(f"Админ {user_id} создал резервную копию данных")
        except Exception as e:
            self.logger.error(f"Ошибка при создании резервной копии: {e}")
            query.edit_message_text(
                f"❌ Ошибка при создании резервной копии: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_maintenance')]]),
                parse_mode='Markdown'
            )

    def _update_api_data(self, query, context):
        """Обновляет данные API (принудительно обновляет кэшированные данные)"""
        user_id = query.from_user.id

        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав супер-администратора")
            return

        try:
            # Сообщаем о начале обновления
            query.edit_message_text(
                "🔄 *Обновление данных API*\n\n"
                "Подождите, идет обновление данных...",
                parse_mode='Markdown'
            )
            
            # Обновляем данные API, если клиент доступен
            api_updated = False
            if self.api_client and hasattr(self.api_client, 'refresh_data'):
                self.api_client.refresh_data()
                api_updated = True
                self.logger.info(f"Админ {user_id} обновил данные API")
            
            # Обновляем темы, если сервис доступен
            topics_updated = False
            if self.topic_service and hasattr(self.topic_service, 'refresh_topics'):
                self.topic_service.refresh_topics()
                topics_updated = True
                self.logger.info(f"Админ {user_id} обновил темы")
            
            # Формируем сообщение о результате
            result_text = "🔄 *Обновление данных*\n\n"
            
            if api_updated:
                result_text += "✅ Данные API успешно обновлены\n"
            else:
                result_text += "⚠️ API клиент недоступен или не поддерживает обновление данных\n"
                
            if topics_updated:
                result_text += "✅ Темы успешно обновлены\n"
            else:
                result_text += "⚠️ Сервис тем недоступен или не поддерживает обновление\n"
            
            # Отображаем результат
            query.edit_message_text(
                result_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_maintenance')]]),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при обновлении данных API: {e}")
            query.edit_message_text(
                f"❌ Ошибка при обновлении данных API: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_maintenance')]]),
                parse_mode='Markdown'
            )

    def _clean_logs(self, query, context):
        """Очищает старые лог-файлы"""
        user_id = query.from_user.id

        if not self.is_super_admin(user_id):
            query.answer("У вас нет прав супер-администратора")
            return

        try:
            # Сообщаем о начале очистки
            query.edit_message_text(
                "🧹 *Очистка логов*\n\n"
                "Подождите, идет очистка старых лог-файлов...",
                parse_mode='Markdown'
            )
            
            # Получаем все лог-файлы
            log_files = self._get_log_files()
            
            # Оставляем только файлы старше 7 дней (кроме текущего)
            import datetime
            current_date = datetime.datetime.now().date()
            files_to_delete = []
            current_log = None
            
            for log_file in log_files:
                try:
                    # Извлекаем дату из имени файла
                    file_name = os.path.basename(log_file)
                    if file_name == "bot.log":
                        current_log = log_file
                        continue
                    
                    if file_name.startswith("bot_log_") and len(file_name) > 12:
                        date_str = file_name[8:16]  # Формат YYYYMMDD
                        file_date = datetime.datetime.strptime(date_str, "%Y%m%d").date()
                        
                        # Если файл старше 7 дней, добавляем в список на удаление
                        if (current_date - file_date).days > 7:
                            files_to_delete.append(log_file)
                except Exception as e:
                    self.logger.error(f"Ошибка при обработке даты файла лога {log_file}: {e}")
            
            # Удаляем старые лог-файлы
            deleted_count = 0
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    self.logger.error(f"Ошибка при удалении лог-файла {file_path}: {e}")
            
            # Очищаем текущий лог, если он слишком большой (более 10 МБ)
            current_log_truncated = False
            if current_log and os.path.exists(current_log):
                file_size = os.path.getsize(current_log)
                if file_size > 10 * 1024 * 1024:  # 10 МБ
                    try:
                        # Создаем резервную копию перед очисткой
                        backup_path = f"{current_log}.bak"
                        import shutil
                        shutil.copy2(current_log, backup_path)
                        
                        # Очищаем файл, оставляя последние 1000 строк
                        with open(current_log, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        with open(current_log, 'w', encoding='utf-8') as f:
                            f.writelines(lines[-1000:])
                            
                        current_log_truncated = True
                        self.logger.info(f"Текущий лог-файл усечен (оставлено последние 1000 строк)")
                    except Exception as e:
                        self.logger.error(f"Ошибка при усечении текущего лог-файла: {e}")
            
            # Формируем сообщение о результате
            result_text = "🧹 *Очистка логов завершена*\n\n"
            
            if deleted_count > 0:
                result_text += f"✅ Удалено {deleted_count} старых лог-файлов\n"
            else:
                result_text += "ℹ️ Не найдено старых лог-файлов для удаления\n"
                
            if current_log_truncated:
                result_text += "✅ Текущий лог-файл был усечен из-за большого размера\n"
            
            # Отображаем результат
            query.edit_message_text(
                result_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_maintenance')]]),
                parse_mode='Markdown'
            )
            
            self.logger.info(f"Админ {user_id} очистил старые лог-файлы")
        except Exception as e:
            self.logger.error(f"Ошибка при очистке логов: {e}")
            query.edit_message_text(
                f"❌ Ошибка при очистке логов: {e}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data='admin_maintenance')]]),
                parse_mode='Markdown'
            )

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
            # Попытка получить данные из Analytics
            if self.analytics and hasattr(self.analytics, 'get_unique_users_count'):
                return self.analytics.get_unique_users_count()
            
            # Запасной вариант - чтение из user_states.json
            if os.path.exists('user_states.json'):
                with open('user_states.json', 'r', encoding='utf-8') as f:
                    user_states = json.load(f)
                    return len(user_states)
            
            return 0
        except Exception as e:
            self.logger.error(f"Ошибка при подсчёте пользователей: {e}")
            return 0

    def _count_messages(self):
        """Подсчитывает общее количество сообщений"""
        try:
            # Попытка получить данные из Analytics
            if self.analytics and hasattr(self.analytics, 'get_total_messages_count'):
                return self.analytics.get_total_messages_count()
            
            # Заглушка
            return 0
        except Exception as e:
            self.logger.error(f"Ошибка при подсчёте сообщений: {e}")
            return 0

    def _get_uptime(self):
        """Возвращает время работы бота"""
        try:
            uptime_seconds = time.time() - self.start_time
            
            # Преобразуем в читаемый формат
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            if days > 0:
                return f"{days} дн. {hours} ч. {minutes} мин."
            elif hours > 0:
                return f"{hours} ч. {minutes} мин."
            else:
                return f"{minutes} мин."
        except Exception as e:
            self.logger.error(f"Ошибка при расчёте времени работы: {e}")
            return "Неизвестно"

    def _count_bot_starts(self):
        """Подсчитывает количество запусков бота за последние 24 часа"""
        try:
            # Попытка получить данные из Analytics
            if self.analytics and hasattr(self.analytics, 'get_bot_starts_count'):
                return self.analytics.get_bot_starts_count(hours=24)
            
            # Запасной вариант - чтение из логов
            log_content = self._get_last_logs(1000)
            count = 0
            current_time = time.time()
            
            for line in log_content:
                if " запустил бота" in line:
                    try:
                        # Извлекаем время из лога
                        log_time_str = line.split(" - ")[0]
                        log_time = time.mktime(time.strptime(log_time_str, "%Y-%m-%d %H:%M:%S"))
                        
                        # Если событие произошло за последние 24 часа
                        if current_time - log_time < 86400:
                            count += 1
                    except Exception:
                        pass
            
            return count
        except Exception as e:
            self.logger.error(f"Ошибка при подсчёте запусков бота: {e}")
            return 0

    def _count_topic_requests(self):
        """Подсчитывает количество запросов тем за последние 24 часа"""
        try:
            # Попытка получить данные из Analytics
            if self.analytics and hasattr(self.analytics, 'get_topic_requests_count'):
                return self.analytics.get_topic_requests_count(hours=24)
            
            # Запасной вариант - чтение из логов
            log_content = self._get_last_logs(1000)
            count = 0
            current_time = time.time()
            
            for line in log_content:
                if " выбрал тему: " in line or " ввел свою тему: " in line:
                    try:
                        # Извлекаем время из лога
                        log_time_str = line.split(" - ")[0]
                        log_time = time.mktime(time.strptime(log_time_str, "%Y-%m-%d %H:%M:%S"))
                        
                        # Если событие произошло за последние 24 часа
                        if current_time - log_time < 86400:
                            count += 1
                    except Exception:
                        pass
            
            return count
        except Exception as e:
            self.logger.error(f"Ошибка при подсчёте запросов тем: {e}")
            return 0

    def _count_completed_tests(self):
        """Подсчитывает количество пройденных тестов за последние 24 часа"""
        try:
            # Попытка получить данные из Analytics
            if self.analytics and hasattr(self.analytics, 'get_completed_tests_count'):
                return self.analytics.get_completed_tests_count(hours=24)
            
            # Запасной вариант - чтение из логов
            log_content = self._get_last_logs(1000)
            count = 0
            current_time = time.time()
            
            for line in log_content:
                if " завершил тест с результатом " in line:
                    try:
                        # Извлекаем время из лога
                        log_time_str = line.split(" - ")[0]
                        log_time = time.mktime(time.strptime(log_time_str, "%Y-%m-%d %H:%M:%S"))
                        
                        # Если событие произошло за последние 24 часа
                        if current_time - log_time < 86400:
                            count += 1
                    except Exception:
                        pass
            
            return count
        except Exception as e:
            self.logger.error(f"Ошибка при подсчёте пройденных тестов: {e}")
            return 0

    def _get_log_files(self):
        """Получает список всех файлов логов"""
        log_files = []
        
        # Проверяем директорию логов
        log_dir = "logs"
        if os.path.exists(log_dir) and os.path.isdir(log_dir):
            for file_name in os.listdir(log_dir):
                if file_name.startswith("bot_log_") or file_name == "bot.log":
                    log_files.append(os.path.join(log_dir, file_name))
        
        # Проверяем корневую директорию
        for file_name in os.listdir("."):
            if file_name.startswith("bot_log_") or file_name == "bot.log":
                log_files.append(file_name)
        
        # Сортируем по времени изменения (новые сначала)
        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        return log_files

    def _get_last_logs(self, lines=100):
        """Получает последние строки из файла логов"""
        try:
            log_files = self._get_log_files()

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
                    "private_mode": False,
                    "notification_enabled": True,
                    "log_level": "INFO",
                    "max_messages_per_user": 100
                }
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке настроек бота: {e}")
            return {}

    def _save_bot_settings(self, settings):
        """Сохраняет настройки бота в файл"""
        try:
            # Сохраняем настройки через временный файл
            temp_file = "bot_settings.json.tmp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
            
            # Атомарно заменяем оригинальный файл
            os.replace(temp_file, "bot_settings.json")
            
            self.logger.info("Настройки бота успешно сохранены")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении настроек бота: {e}")
            return False

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
