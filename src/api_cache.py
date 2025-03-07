import json
import os
import time
import threading

class APICache:
    """Класс для кэширования запросов и ответов API"""

    def __init__(self, logger, max_size=200, save_interval=10):
        self.logger = logger
        self.cache = {}
        self.max_size = max_size
        self.save_interval = save_interval  # минуты
        self.cache_file = "api_cache.json"
        self.lock = threading.Lock()

        # Загружаем кэш из файла если он есть
        self._load_cache()

        # Запускаем периодическое сохранение кэша в отдельном потоке
        self._start_save_thread()

    def get(self, key):
        """Получает значение из кэша по ключу"""
        with self.lock:
            if key in self.cache:
                value = self.cache[key]["value"]
                self.logger.info(f"Кэш-хит для ключа: {key[:50]}...")
                return value
        self.logger.info(f"Кэш-мисс для ключа: {key[:50]}...")
        return None

    def set(self, key, value):
        """Устанавливает значение в кэш по ключу"""
        with self.lock:
            # Если кэш переполнен, удаляем самый старый элемент
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
                del self.cache[oldest_key]
                self.logger.info(f"Кэш переполнен, удален ключ: {oldest_key[:50]}...")

            # Добавляем новое значение в кэш
            self.cache[key] = {
                "value": value,
                "timestamp": time.time()
            }

            self.logger.info(f"Добавлен в кэш ключ: {key[:50]}...")

    def _load_cache(self):
        """Загружает кэш из файла"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cache = data
                    self.logger.info(f"Кэш загружен из файла, {len(self.cache)} записей")
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке кэша: {e}")
            # Если файл поврежден, начинаем с пустого кэша
            self.cache = {}

    def _save_cache(self):
        """Сохраняет кэш в файл"""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Кэш сохранен в файл, {len(self.cache)} записей")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении кэша: {e}")

    def _start_save_thread(self):
        """Запускает поток для периодического сохранения кэша"""
        def save_periodically():
            while True:
                time.sleep(self.save_interval * 60)  # Конвертируем минуты в секунды
                with self.lock:
                    self._save_cache()

        thread = threading.Thread(target=save_periodically, daemon=True)
        thread.start()
        self.logger.info(f"Запущен поток периодического сохранения кэша (интервал: {self.save_interval} мин)")