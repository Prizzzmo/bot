
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
        """Очистка устаревших элементов кэша по TTL с оптимизированным управлением памятью"""
        current_time = datetime.now().timestamp()
        
        # Оптимизация: прямое удаление без создания промежуточного списка
        # и оптимизированный поиск кандидатов для удаления
        try:
            delete_count = 0
            for key in list(self.cache.keys()):
                data = self.cache[key]
                # Удаляем устаревшие ключи
                if current_time - data['created_at'] > data['ttl']:
                    del self.cache[key]
                    delete_count += 1
            
            # Очищаем кэш, если он слишком большой (>90% от max_size)
            # Улучшенный алгоритм для уменьшения частоты очистки
            cache_size = len(self.cache)
            if cache_size > self.max_size * 0.9:
                # Используем быстрый алгоритм - удаляем 30% наименее используемых записей
                # без полной сортировки кэша, используя алгоритм выбора k-го элемента
                access_times = [(k, v['last_accessed']) for k, v in self.cache.items()]
                
                # Определяем порог доступа для удаления (примерно 30% старых элементов)
                threshold_idx = int(cache_size * 0.3)
                if threshold_idx > 0:
                    # Находим пороговое значение времени доступа (быстрее полной сортировки)
                    threshold_time = sorted([t[1] for t in access_times])[threshold_idx]
                    
                    # Удаляем элементы с временем доступа ниже порогового значения
                    for k, access_time in access_times:
                        if access_time <= threshold_time:
                            if k in self.cache:  # Проверка на всякий случай
                                del self.cache[k]
                
                self.logger.debug(f"Произведена очистка кэша, осталось {len(self.cache)} элементов")
            
            if delete_count > 0:
                self.logger.debug(f"Удалено {delete_count} устаревших элементов из кэша")
        except Exception as e:
            self.logger.error(f"Ошибка при очистке кэша: {e}")

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
