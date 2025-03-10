import os
from dotenv import load_dotenv
import json

# Загружаем переменные окружения из файла .env
load_dotenv()

# Константы для состояний ConversationHandler
TOPIC, CHOOSE_TOPIC, TEST, ANSWER, CONVERSATION, MAP, ANALYTICS, ADMIN = range(8)

# Словарь с описаниями ошибок для расширенного логирования
ERROR_DESCRIPTIONS = {
    'ConnectionError': 'Ошибка подключения к внешнему API. Проверьте интернет-соединение.',
    'Timeout': 'Превышено время ожидания ответа от внешнего API.',
    'JSONDecodeError': 'Ошибка при разборе JSON ответа от API.',
    'HTTPError': 'Ошибка HTTP при запросе к внешнему API.',
    'TelegramError': 'Ошибка при взаимодействии с Telegram API.',
    'KeyboardInterrupt': 'Бот был остановлен вручную.',
    'ApiError': 'Ошибка при взаимодействии с внешним API.',
    "TelegramError": "Ошибка Telegram API",
    "Unauthorized": "Неверный токен бота",
    "BadRequest": "Неверный запрос к Telegram API",
    "TimedOut": "Превышено время ожидания ответа от Telegram API",
    "NetworkError": "Проблемы с сетью",
    "ChatMigrated": "Чат был перенесен",
    "RetryAfter": "Превышен лимит запросов, ожидание",
    "InvalidToken": "Неверный токен бота",
    "Conflict": "Конфликт запросов getUpdates. Проверьте, что запущен только один экземпляр бота"
}

class Config:
    """Класс для работы с конфигурацией приложения"""

    def __init__(self):
        """
        Инициализация конфигурации с загрузкой параметров
        из переменных окружения и .env файла
        """
        load_dotenv()  # Загружаем переменные из .env файла

        # Базовая конфигурация
        self.telegram_token = os.getenv('TELEGRAM_TOKEN', '')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY', '')
        self.allow_subscribers = os.getenv('ALLOW_SUBSCRIBERS', 'true').lower() == 'true'
        self.admin_config_file = os.getenv('ADMIN_CONFIG_FILE', 'admins.json')
        self.log_level = os.getenv('LOG_LEVEL', 'warning').upper()

        # Конфигурация для распределенного кэширования
        self.use_distributed_cache = os.getenv('USE_DISTRIBUTED_CACHE', 'false').lower() == 'true'
        self.redis_url = os.getenv('REDIS_URL', '')

        # Конфигурация для мониторинга производительности
        self.enable_performance_monitoring = os.getenv('ENABLE_PERFORMANCE_MONITORING', 'true').lower() == 'true'
        self.metrics_file = os.getenv('METRICS_FILE', 'performance_metrics.json')

    def validate(self) -> bool:
        """Проверяет наличие всех необходимых параметров в конфигурации"""
        return self.telegram_token and os.path.exists(self.admin_config_file)

    def set_task_queue(self, task_queue):
        """Устанавливает очередь задач"""
        self.task_queue = task_queue

    def get_task_queue(self):
        """Возвращает очередь задач"""
        return getattr(self, 'task_queue', None)