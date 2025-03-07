
import json
import os
from datetime import datetime
import hashlib

class APICache:
    """
    Оптимизированный класс для кэширования ответов API.
    Поддерживает сохранение и загрузку кэша из файла.
    Добавлена оптимизация по времени жизни кэша и сохранению на диск.
    """
    def __init__(self, logger, max_size=100, cache_file='api_cache.json', save_interval=20):
        self.cache = {}
        self.max_size = max_size
        self.cache_file = cache_file
        self.save_interval = save_interval  # Интервал автоматического сохранения кэша
        self.operation_count = 0  # Счетчик операций для периодического сохранения
        self.logger = logger
        self.load_cache()

    def get(self, key):
        """Получить значение из кэша по ключу с обновлением времени доступа"""
        if key in self.cache:
            # Обновляем время последнего доступа
            self.cache[key]['last_accessed'] = datetime.now().timestamp()
            return self.cache[key]['value']
        return None

    def set(self, key, value, ttl=86400):  # ttl по умолчанию 24 часа
        """Добавить значение в кэш с оптимизированной стратегией вытеснения"""
        # Если кэш переполнен, удаляем наименее востребованные элементы
        if len(self.cache) >= self.max_size:
            # Используем более эффективный алгоритм сортировки
            items_to_remove = sorted(
                [(k, v['last_accessed']) for k, v in self.cache.items()],
                key=lambda x: x[1]
            )[:int(self.max_size * 0.2)]  # Удаляем 20% старых элементов

            for key_to_remove, _ in items_to_remove:
                del self.cache[key_to_remove]

        timestamp = datetime.now().timestamp()
        # Добавляем новый элемент с временной меткой и TTL
        self.cache[key] = {
            'value': value,
            'last_accessed': timestamp,
            'created_at': timestamp,
            'ttl': ttl
        }

        # Инкрементируем счетчик операций
        self.operation_count += 1

        # Периодически сохраняем кэш и очищаем устаревшие записи
        if self.operation_count >= self.save_interval:
            self.cleanup_expired()
            self.save_cache()
            self.operation_count = 0

    def cleanup_expired(self):
        """Очистка устаревших элементов кэша по TTL"""
        current_time = datetime.now().timestamp()
        keys_to_remove = []

        for key, data in self.cache.items():
            if current_time - data['created_at'] > data['ttl']:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.cache[key]

        if keys_to_remove:
            self.logger.info(f"Удалено {len(keys_to_remove)} устаревших элементов из кэша")

    def load_cache(self):
        """Загружает кэш из файла, если он существует, с оптимизацией"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    loaded_cache = json.load(f)
                    # Добавляем проверку TTL при загрузке
                    current_time = datetime.now().timestamp()
                    for k, v in loaded_cache.items():
                        if 'created_at' in v and 'ttl' in v:
                            if current_time - v['created_at'] <= v['ttl']:
                                self.cache[k] = v
                        else:
                            # Для обратной совместимости
                            self.cache[k] = {
                                'value': v.get('value', v),
                                'last_accessed': v.get('last_accessed', current_time),
                                'created_at': v.get('created_at', current_time),
                                'ttl': v.get('ttl', 86400)
                            }

                    self.logger.info(f"Кэш загружен из {self.cache_file}, {len(self.cache)} записей")
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке кэша: {e}")
            self.cache = {}

    def save_cache(self):
        """Сохраняет кэш в файл с оптимизацией"""
        try:
            # Используем временный файл для безопасной записи
            temp_file = f"{self.cache_file}.temp"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False)

            # Переименовываем временный файл для атомарной операции
            os.replace(temp_file, self.cache_file)
            self.logger.info(f"Кэш сохранен в {self.cache_file}, {len(self.cache)} записей")
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении кэша: {e}")

    def clear(self):
        """Очистить кэш"""
        self.cache.clear()
        self.save_cache()
        
    def generate_key(self, prompt, max_tokens=1024, temp=0.7):
        """Генерирует ключ для кэша на основе параметров запроса"""
        cache_key = hashlib.md5(f"{prompt}_{max_tokens}_{temp}".encode()).hexdigest()
        return cache_key
