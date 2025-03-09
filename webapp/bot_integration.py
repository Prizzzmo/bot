
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

def get_webapp_keyboard():
    """
    Creates an inline keyboard with a button to open the webapp
    """
    # Пытаемся определить URL для веб-приложения несколькими способами
    # Приоритет отдается явно указанному URL в переменных окружения
    webapp_url = os.environ.get('WEBAPP_URL', '')
    
    # Если URL не задан в переменных окружения, строим его из данных о развертывании
    if not webapp_url:
        deployment_id = os.environ.get('REPL_DEPLOYMENT_ID', '')
        repl_id = os.environ.get('REPL_ID', '')
        repl_slug = os.environ.get('REPL_SLUG', '')
        repl_owner = os.environ.get('REPL_OWNER', '')
        
        # Проверяем, есть ли информация о развертывании (deployment)
        if deployment_id:
            webapp_url = f"https://{deployment_id}.deployment.repl.co"
        # Если нет информации о развертывании, используем данные о repl
        elif repl_slug and repl_owner:
            webapp_url = f"https://{repl_slug}.{repl_owner}.repl.co"
        # Если другие данные недоступны, используем REPL_ID
        elif repl_id:
            webapp_url = f"https://{repl_id}.id.repl.co"
        # Если совсем ничего не доступно, используем захардкоженный URL
        else:
            webapp_url = "https://workspace.never.repl.co"
    
    # Логирование URL для отладки
    print(f"Сформирован URL для веб-приложения: {webapp_url}")
    
    keyboard = [
        [InlineKeyboardButton(
            text="Открыть карту истории России", 
            web_app=WebAppInfo(url=webapp_url)
        )]
    ]
    return InlineKeyboardMarkup(keyboard)
