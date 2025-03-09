
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

def get_webapp_keyboard():
    """
    Creates an inline keyboard with a button to open the webapp
    """
    # Получаем URL для веб-приложения
    repl_id = os.environ.get('REPL_ID', '')
    repl_slug = os.environ.get('REPL_SLUG', '')
    repl_owner = os.environ.get('REPL_OWNER', '')
    
    # Формируем URL в зависимости от доступной информации
    if repl_slug and repl_owner:
        webapp_url = f"https://{repl_slug}.{repl_owner}.repl.co"
    else:
        # Fallback на использование REPL_ID, который всегда доступен
        webapp_url = f"https://{repl_id}.id.repl.co"
    
    keyboard = [
        [InlineKeyboardButton(
            text="Открыть карту истории России", 
            web_app=WebAppInfo(url=webapp_url)
        )]
    ]
    return InlineKeyboardMarkup(keyboard)
