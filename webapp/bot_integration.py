
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

def get_webapp_keyboard():
    """
    Creates an inline keyboard with a button to open the webapp
    """
    keyboard = [
        [InlineKeyboardButton(
            text="Открыть карту истории России", 
            web_app=WebAppInfo(url="https://REPL_ID.id.repl.co/")  # Replace with your actual Repl URL when deployed
        )]
    ]
    return InlineKeyboardMarkup(keyboard)

# Example of how to use this in a bot handler:
"""
@dp.message_handler(commands=['map', 'карта'])
async def cmd_open_map(message: types.Message):
    await message.answer(
        "Нажмите на кнопку ниже, чтобы открыть интерактивную карту исторических событий России:",
        reply_markup=get_webapp_keyboard()
    )
"""
