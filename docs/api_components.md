
# API компоненты

Этот документ описывает основные компоненты API, используемые в проекте образовательного бота по истории России.

## Содержание

1. [Обзор](#обзор)
2. [Gemini API Client](#gemini-api-client)
3. [API Cache](#api-cache)
4. [Ротация API-ключей](#ротация-api-ключей)
5. [Структура запросов](#структура-запросов)
6. [Обработка ошибок](#обработка-ошибок)
7. [Оптимизация использования API](#оптимизация-использования-api)
8. [Лимиты и ограничения](#лимиты-и-ограничения)

## Обзор

Образовательный бот по истории России использует Google Gemini API для генерации образовательного контента, ответов на вопросы пользователей и создания тестов. Взаимодействие с API осуществляется через специализированный клиент, обеспечивающий эффективное и безопасное использование внешних сервисов.

## Gemini API Client

### Основной API-клиент

Класс `APIClient` (`src/api_client.py`) является основным интерфейсом для взаимодействия с Gemini API:

```python
class APIClient:
    def __init__(self, api_key=None, logger=None, cache=None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.logger = logger or logging.getLogger(__name__)
        self.cache = cache
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-2.0-flash"
```

### Основные методы

1. **call_api(prompt, temperature=0.7, max_tokens=1024, key_index=0)**
   
   Базовый метод для вызова Gemini API с настройкой параметров генерации.
   
   ```python
   def call_api(self, prompt, temperature=0.7, max_tokens=1024, key_index=0):
       # Получение API-ключа по индексу из ротации
       api_key = get_key_by_index(key_index)
       
       # Формирование URL запроса
       url = f"{self.base_url}/{self.model}:generateContent?key={api_key}"
       
       # Формирование тела запроса
       payload = {
           "contents": [{"parts": [{"text": prompt}]}],
           "generationConfig": {
               "temperature": temperature,
               "maxOutputTokens": max_tokens,
               "topP": 0.95,
               "topK": 40
           }
       }
       
       # Отправка запроса и обработка ответа
       response = requests.post(url, json=payload)
       
       # Проверка статуса ответа
       if response.status_code != 200:
           self.logger.error(f"API error: {response.status_code}, {response.text}")
           return None
           
       # Парсинг и возврат ответа
       return self._parse_response(response.json())
   ```

2. **ask_grok(question, temperature=0.3, max_tokens=2048)**
   
   Упрощенный метод для получения ответа на вопрос пользователя.
   
   ```python
   def ask_grok(self, question, temperature=0.3, max_tokens=2048):
       # Проверка кэша
       if self.cache:
           cached_response = self.cache.get_cached(question)
           if cached_response:
               self.logger.info("Using cached response")
               return cached_response
               
       # Формирование промпта
       prompt = f"Вопрос: {question}\n\nОтвет:"
       
       # Вызов API с ротацией ключей и повторами при ошибках
       for key_index in range(len(GEMINI_API_KEYS)):
           response = self.call_api(prompt, temperature, max_tokens, key_index)
           if response:
               # Кэширование успешного ответа
               if self.cache:
                   self.cache.cache_response(question, response)
               return response
               
       # Возврат сообщения об ошибке при исчерпании всех попыток
       return "Извините, не удалось получить ответ. Пожалуйста, попробуйте позже."
   ```

3. **get_historical_info(topic, temperature=0.2, max_tokens=4096)**
   
   Метод для получения информации по исторической теме.
   
   ```python
   def get_historical_info(self, topic, temperature=0.2, max_tokens=4096):
       # Проверка кэша
       cache_key = f"historical_info_{topic}"
       if self.cache:
           cached_info = self.cache.get_cached(cache_key)
           if cached_info:
               return cached_info
               
       # Предварительная валидация темы
       if not self.validate_historical_topic(topic):
           return "Запрошенная тема не относится к истории России."
           
       # Формирование структурированного промпта
       prompt = f"""
       Предоставь подробную информацию по теме из истории России: "{topic}".
       
       Структурируй ответ по следующим разделам:
       1. Общая информация и контекст
       2. Ключевые события и даты
       3. Исторические личности
       4. Значение и последствия
       5. Интересные факты
       
       Структурируй информацию четко, используй маркированные списки, выделяй важные даты и имена.
       """
       
       # Вызов API с ротацией ключей
       for key_index in range(len(GEMINI_API_KEYS)):
           info = self.call_api(prompt, temperature, max_tokens, key_index)
           if info:
               # Кэширование результата
               if self.cache:
                   self.cache.cache_response(cache_key, info)
               return info
               
       return "Извините, не удалось получить информацию по запрошенной теме."
   ```

4. **generate_historical_test(topic, difficulty='medium', questions_count=5)**
   
   Метод для генерации теста по исторической теме.
   
   ```python
   def generate_historical_test(self, topic, difficulty='medium', questions_count=5):
       # Формирование кэш-ключа с учетом параметров
       cache_key = f"test_{topic}_{difficulty}_{questions_count}"
       if self.cache:
           cached_test = self.cache.get_cached(cache_key)
           if cached_test:
               return cached_test
               
       # Настройка параметров в зависимости от сложности
       if difficulty == 'easy':
           temperature = 0.3
       elif difficulty == 'hard':
           temperature = 0.5
       else:  # medium
           temperature = 0.4
           
       # Формирование промпта для генерации теста
       prompt = f"""
       Создай тест по теме из истории России: "{topic}".
       
       Правила:
       1. Тест должен состоять из {questions_count} вопросов с вариантами ответов
       2. Сложность: {difficulty}
       3. Для каждого вопроса нужно предоставить 4 варианта ответа
       4. Только один вариант должен быть правильным
       5. Формат каждого вопроса:
          Q: [текст вопроса]
          A) [вариант A]
          B) [вариант B]
          C) [вариант C]
          D) [вариант D]
          Correct: [буква правильного варианта]
          Explanation: [объяснение правильного ответа]
       """
       
       # Вызов API с повышенным лимитом токенов
       max_tokens = questions_count * 500  # Расчет необходимого количества токенов
       
       # Ротация ключей
       for key_index in range(len(GEMINI_API_KEYS)):
           test = self.call_api(prompt, temperature, max_tokens, key_index)
           if test:
               # Кэширование с длительным TTL
               if self.cache:
                   self.cache.cache_response(cache_key, test, ttl=86400)  # 24 часа
               return test
               
       return "Извините, не удалось сгенерировать тест по запрошенной теме."
   ```

5. **validate_historical_topic(topic)**
   
   Метод для проверки, относится ли тема к истории России.
   
   ```python
   def validate_historical_topic(self, topic):
       # Формирование промпта для валидации
       prompt = f"""
       Определи, относится ли тема "{topic}" к истории России.
       Ответь только "да" или "нет".
       """
       
       # Вызов API с низкой температурой для детерминированного ответа
       for key_index in range(len(GEMINI_API_KEYS)):
           response = self.call_api(prompt, temperature=0.1, max_tokens=10, key_index=key_index)
           if response:
               # Проверка ответа
               response = response.lower().strip()
               return "да" in response
               
       # По умолчанию считаем тему релевантной
       return True
   ```

## API Cache

`APICache` (`src/api_cache.py`) - класс для кэширования запросов к API с возможностью настройки TTL (Time-To-Live):

```python
class APICache:
    def __init__(self, cache_file='api_cache.json', max_size=1000, ttl=3600):
        self.cache_file = cache_file
        self.max_size = max_size
        self.default_ttl = ttl
        self.cache = {}
        self.load_cache()
        
    def load_cache(self):
        # Загрузка кэша из файла
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Фильтрация записей с истекшим TTL
                current_time = time.time()
                self.cache = {
                    k: v for k, v in data.items() 
                    if 'expiry' not in v or v['expiry'] > current_time
                }
            except Exception as e:
                print(f"Error loading cache: {e}")
                self.cache = {}
                
    def save_cache(self):
        # Сохранение кэша в файл
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")
            
    def get_cached(self, key):
        # Получение ответа из кэша
        key_hash = hashlib.md5(key.encode()).hexdigest()
        if key_hash in self.cache:
            # Проверка срока действия кэша
            entry = self.cache[key_hash]
            if 'expiry' not in entry or entry['expiry'] > time.time():
                return entry['response']
            else:
                # Удаление устаревшей записи
                del self.cache[key_hash]
        return None
        
    def cache_response(self, key, response, ttl=None):
        # Сохранение ответа в кэш
        key_hash = hashlib.md5(key.encode()).hexdigest()
        
        # Установка срока действия
        expiry = time.time() + (ttl if ttl is not None else self.default_ttl)
        
        self.cache[key_hash] = {
            'response': response,
            'expiry': expiry,
            'timestamp': time.time()
        }
        
        # Проверка размера кэша и при необходимости удаление старых записей
        if len(self.cache) > self.max_size:
            self._trim_cache()
            
        # Асинхронное сохранение кэша
        threading.Thread(target=self.save_cache, daemon=True).start()
        
    def _trim_cache(self):
        # Удаление старых записей при превышении максимального размера
        items = sorted(self.cache.items(), key=lambda x: x[1]['timestamp'])
        to_remove = len(self.cache) - self.max_size
        
        if to_remove > 0:
            for i in range(to_remove):
                key, _ = items[i]
                del self.cache[key]
                
    def clear_cache(self):
        # Полная очистка кэша
        self.cache = {}
        self.save_cache()
```

## Ротация API-ключей

Система ротации API-ключей реализована в `gemini_api_keys.py`:

```python
# Список API ключей для модели gemini-2.0-flash
GEMINI_API_KEYS = [
    "API_KEY_1",
    "API_KEY_2",
    "API_KEY_3"
]

def get_key_by_index(index=0):
    """
    Возвращает API-ключ по индексу, с проверкой границ массива.
    
    Args:
        index (int): Индекс ключа в списке
        
    Returns:
        str: API-ключ
    """
    if index < 0 or index >= len(GEMINI_API_KEYS):
        return GEMINI_API_KEYS[0]
    return GEMINI_API_KEYS[index]

def get_keys_count():
    """
    Возвращает количество доступных API-ключей.
    
    Returns:
        int: Количество ключей
    """
    return len(GEMINI_API_KEYS)
```

## Структура запросов

### Образец запроса к Gemini API

```json
{
  "contents": [
    {
      "parts": [
        {
          "text": "Предоставь информацию о Петровских реформах в России."
        }
      ]
    }
  ],
  "generationConfig": {
    "temperature": 0.2,
    "maxOutputTokens": 4096,
    "topP": 0.95,
    "topK": 40
  }
}
```

### Параметры запроса

- **temperature**: Контролирует случайность генерации (0.0-1.0)
- **maxOutputTokens**: Максимальное количество токенов в ответе
- **topP**: Вероятностный порог для выбора следующего токена
- **topK**: Количество наиболее вероятных токенов для выбора

## Обработка ошибок

Система обработки ошибок при взаимодействии с API включает:

1. **Повторные попытки**: При временных ошибках API запрос повторяется с экспоненциальной задержкой.

2. **Ротация ключей**: При превышении квоты для одного ключа система автоматически переключается на следующий.

3. **Логирование ошибок**: Все проблемы с API записываются в лог-файл с контекстом.

4. **Fallback-механизмы**: При недоступности API система использует кэшированные ответы или заранее подготовленные шаблоны.

## Оптимизация использования API

### Стратегии оптимизации

1. **Кэширование**: Сохранение часто запрашиваемой информации для уменьшения количества запросов.

2. **Ротация ключей**: Распределение нагрузки между несколькими API-ключами.

3. **Оптимизация промптов**: Структурирование запросов для получения более точных и коротких ответов.

4. **Предварительная валидация**: Проверка релевантности запросов перед отправкой в API.

5. **Асинхронная предзагрузка**: Подготовка ответов на популярные запросы в фоновом режиме.

## Лимиты и ограничения

### Gemini API лимиты

- **Количество запросов в минуту**: 60 запросов/мин на ключ
- **Токены в запросе**: До 30,720 токенов в одном запросе
- **Токены в ответе**: До 8,192 токенов в ответе для gemini-2.0-flash
- **Дневная квота**: 1,800,000 токенов на ключ в сутки

### Обходные стратегии

1. **Ротация ключей**: Использование нескольких API-ключей для распределения нагрузки.

2. **Управление размером запросов**: Разделение больших запросов на несколько меньших.

3. **Динамическое управление частотой**: Автоматическое регулирование частоты запросов в зависимости от нагрузки.

4. **Приоритезация запросов**: Обработка критически важных запросов в первую очередь.
