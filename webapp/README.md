
# Веб-интерфейс для образовательного бота по истории России

Веб-интерфейс представляет собой административную панель для управления образовательным ботом по истории России. Панель обеспечивает мониторинг работы бота, просмотр статистики и управление контентом.

## Особенности

- **Мониторинг логов**: Просмотр и фильтрация логов бота по уровням важности (INFO, WARNING, ERROR)
- **Просмотр статистики**: Отображение активности пользователей, популярных тем и успешности тестирования
- **Управление контентом**: Редактирование существующих тем и добавление новых
- **Административный доступ**: Настройка прав доступа и управление администраторами
- **Интеграция с ботом**: Полная синхронизация веб-панели с Telegram-ботом

## Компоненты веб-интерфейса

1. **Серверная часть** (`server.py`):
   - Flask-приложение для обработки запросов
   - Интеграция с основными сервисами бота
   - Защита административного доступа

2. **Клиентская часть** (`index.html`, `app.js`, `styles.css`):
   - Интерактивный интерфейс для администраторов
   - Динамическое обновление данных
   - Адаптивный дизайн

3. **Интеграционный модуль** (`bot_integration.py`):
   - Связь веб-интерфейса с ядром бота
   - Передача команд и получение обратной связи

## Использование

1. Веб-интерфейс запускается автоматически вместе с ботом через скрипт `main.py`
2. Доступ к панели возможен по URL, который отображается при запуске
3. Для входа требуется авторизация с использованием административных учетных данных
4. После авторизации доступны все функции управления ботом

## Безопасность

- Все административные запросы требуют авторизации
- Поддерживается шифрование данных при передаче
- Ведется журнал административных действий
- Данные пользователей защищены в соответствии с принципами защиты личной информации

## Технические требования

- Современный веб-браузер с поддержкой JavaScript
- Подключение к интернету для доступа к панели
- Права администратора в системе бота

## Интеграция с основным ботом

Веб-интерфейс тесно интегрирован с основной системой бота и предоставляет актуальную информацию в режиме реального времени. Любые изменения, внесенные через панель, немедленно отражаются в работе бота.

---

*© 2025 Образовательный бот по истории России*
