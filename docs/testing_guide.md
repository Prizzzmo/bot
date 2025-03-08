
# Руководство по тестированию

## Обзор

Этот документ описывает систему тестирования проекта исторического бота, включая автоматические тесты, методы тестирования и рекомендации по добавлению новых тестов.

## Структура тестов

Все тесты находятся в директории `tests/`. Структура тестов соответствует структуре исходного кода в директории `src/`:

```
tests/
├── __init__.py
├── test_api_cache.py
├── test_api_client.py
├── test_conversation_service.py
├── test_data_migration.py
├── test_logger.py
├── test_topic_service.py
├── test_topic_service_extended.py
├── test_ui_manager.py
└── ...
```

## Запуск тестов

### Запуск всех тестов

```bash
python -m unittest discover tests
```

### Запуск конкретного теста

```bash
python -m unittest tests.test_api_client
```

### Запуск конкретного тестового метода

```bash
python -m unittest tests.test_api_client.TestAPIClient.test_call_api
```

## Инструменты для тестирования

Проект использует следующие инструменты для тестирования:

1. **unittest** - стандартная библиотека тестирования Python
2. **unittest.mock** - для создания моков и имитации поведения зависимостей
3. **patch** - для патчинга методов и объектов во время тестирования

## Типы тестов

### 1. Модульные тесты

Тестируют отдельные компоненты системы в изоляции от остальных:

- `test_api_client.py` - тесты для API клиента
- `test_logger.py` - тесты для системы логирования
- `test_api_cache.py` - тесты для кэша API запросов
- и т.д.

### 2. Интеграционные тесты

Тестируют взаимодействие между компонентами:

- Взаимодействие между службами и обработчиками
- Взаимодействие между API клиентом и кэшем
- Взаимодействие между UIManger и обработчиками

### 3. Функциональные тесты

Тестируют полную функциональность бота с эмуляцией пользовательских сценариев.

## Добавление новых тестов

### 1. Создание нового тестового файла

```python
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Add path to project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.your_module import YourClass

class TestYourClass(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        # Инициализация объектов перед каждым тестом
        self.mock_dependency = MagicMock()
        self.your_object = YourClass(self.mock_dependency)
    
    def tearDown(self):
        """Clean up after tests"""
        # Очистка после теста
        pass
    
    def test_your_method(self):
        """Test description"""
        # Настройка тестовых данных
        test_data = "test"
        
        # Настройка поведения моков
        self.mock_dependency.some_method.return_value = "expected_result"
        
        # Вызов тестируемого метода
        result = self.your_object.your_method(test_data)
        
        # Проверка результата
        self.assertEqual(result, "expected_result")
        
        # Проверка взаимодействия с зависимостями
        self.mock_dependency.some_method.assert_called_once_with(test_data)

if __name__ == '__main__':
    unittest.main()
```

### 2. Рекомендации по созданию качественных тестов

1. **Изолируйте тесты**: Каждый тест должен проверять только одну функцию или компонент
2. **Используйте моки**: Имитируйте внешние зависимости для изоляции тестируемого кода
3. **Имена тестов**: Используйте говорящие имена тестовых методов (`test_should_return_success_when_...`)
4. **Документируйте тесты**: Добавляйте docstrings с описанием того, что тестирует метод
5. **Покрывайте граничные случаи**: Тестируйте нормальное поведение и граничные случаи
6. **Избегайте зависимости от внешних ресурсов**: Используйте моки для API, базы данных и т.д.

## Мокирование внешних API

### Мокирование Telegram API

```python
@patch('telegram.Bot')
@patch('telegram.Update')
def test_telegram_handler(self, mock_update, mock_bot):
    # Настройка мока для телеграм-обновления
    mock_update.effective_chat.id = 123456
    mock_update.message.text = "Test message"
    
    # Настройка мока для телеграм-бота
    mock_bot.send_message.return_value = MagicMock()
    
    # Вызов тестируемого обработчика
    handler = YourHandler(mock_bot)
    handler.handle_message(mock_update)
    
    # Проверка взаимодействия с ботом
    mock_bot.send_message.assert_called_once_with(
        chat_id=123456,
        text=mock.ANY
    )
```

### Мокирование Gemini API

```python
@patch('src.api_client.genai')
def test_gemini_api_call(self, mock_genai):
    # Настройка мока для ответа API
    mock_response = MagicMock()
    mock_response.text = "Test response"
    
    # Настройка мока для модели
    mock_model = MagicMock()
    mock_model.generate_content.return_value = mock_response
    
    # Настройка мока для модуля genai
    mock_genai.GenerativeModel.return_value = mock_model
    
    # Создание API клиента с моками
    api_client = APIClient("fake_api_key", self.mock_cache, self.mock_logger)
    
    # Вызов тестируемого метода
    result = api_client.call_api("Test prompt")
    
    # Проверка результата
    self.assertEqual(result["text"], "Test response")
    
    # Проверка вызова API
    mock_model.generate_content.assert_called_once()
```

## Тестирование асинхронного кода

```python
@patch('asyncio.get_event_loop')
async def test_async_method(self, mock_get_event_loop):
    # Настройка мока для event loop
    mock_loop = MagicMock()
    mock_get_event_loop.return_value = mock_loop
    
    # Создание футуры с результатом
    future = asyncio.Future()
    future.set_result("async result")
    
    # Настройка мока для запуска in_executor
    mock_loop.run_in_executor.return_value = future
    
    # Вызов тестируемого асинхронного метода
    result = await self.your_object.async_method()
    
    # Проверка результата
    self.assertEqual(result, "async result")
```

## Покрытие кода тестами

Для анализа покрытия кода тестами рекомендуется использовать инструмент `coverage`:

```bash
# Установка coverage
pip install coverage

# Запуск тестов с coverage
coverage run -m unittest discover tests

# Генерация отчета
coverage report -m

# Генерация HTML-отчета
coverage html
```

HTML-отчет будет сохранен в директории `htmlcov/` и предоставит подробную информацию о покрытии кода тестами.

## Постоянная интеграция (CI)

Для настройки постоянной интеграции можно использовать GitHub Actions:

```yaml
# .github/workflows/tests.yml
name: Tests

on:
  push:
    branches: [ main, dev ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install coverage
    - name: Run tests
      run: |
        coverage run -m unittest discover tests
    - name: Generate coverage report
      run: |
        coverage report -m
        coverage xml
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v1
```
