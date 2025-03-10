
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

def get_webapp_keyboard():
    """
    Создает и возвращает клавиатуру с кнопкой для запуска веб-приложения карты истории.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой веб-приложения
    """
    # Создаем кнопку WebApp для карты
    map_button = InlineKeyboardButton(
        text="🗺️ Открыть интерактивную карту",
        web_app=WebAppInfo(url="https://history-map-webapp.replit.app")  # URL вашего веб-приложения
    )
    
    # Добавляем кнопку возврата в меню
    back_button = InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_menu")
    
    # Формируем клавиатуру с кнопками
    keyboard = [
        [map_button],
        [back_button]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_map_description():
    """
    Возвращает описание для карты истории России.
    
    Returns:
        str: Текстовое описание карты
    """
    return (
        "🗺️ *Интерактивная карта истории России*\n\n"
        "На этой карте отмечены ключевые исторические события России от древних времен до современности.\n\n"
        "• Нажмите на кнопку ниже, чтобы открыть интерактивную карту\n"
        "• Используйте кластеры маркеров для навигации\n"
        "• Нажимайте на маркеры, чтобы получить подробную информацию о событиях\n"
        "• Разные цвета маркеров обозначают разные категории событий\n\n"
        "Карта загружается автоматически. Изучайте историю России в интерактивном формате!"
    )
