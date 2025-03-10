
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

def get_webapp_keyboard():
    """
    Создает и возвращает клавиатуру с кнопкой для запуска веб-приложения карты истории.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой веб-приложения
    """
    # Определяем прямую ссылку на карту в Telegram
    telegram_map_url = "http://t.me/teach_hisbot/hismap"
    
    # Создаем кнопку с URL
    map_button = InlineKeyboardButton(
        text="🗺️ Открыть интерактивную карту",
        url=telegram_map_url
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
        "Карта содержит более 8600 исторических событий с древнейших времен до наших дней. "
        "Вы можете:\n"
        "• Фильтровать события по категориям\n"
        "• Просматривать события по временным периодам\n"
        "• Изучать подробности каждого события\n\n"
        "Нажмите на кнопку ниже, чтобы открыть интерактивную карту:"
    )
