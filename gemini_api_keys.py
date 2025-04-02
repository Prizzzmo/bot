
"""
Файл с API ключами для доступа к Google Gemini API.
Используется для ротации ключей и управления доступом к API.
"""

# Список API ключей для модели gemini-2.0-flash
GEMINI_API_KEYS = [
    "AIzaSyDR2MuMWLBzRPiDPg7O8sZuke77CWmzI1U",
    "AIzaSyCvJVQnn7jAEpynQ5mToQUtYWbu_X7TUkU",
    "AIzaSyDR2MuMWLBzRPiDPg7O8sZuke77CWmzI1U"
]

def get_random_key():
    """
    Возвращает случайный API ключ из списка доступных ключей.
    
    Returns:
        str: API ключ для использования с Gemini API
    """
    import random
    return random.choice(GEMINI_API_KEYS)

def get_key_by_index(index=0):
    """
    Возвращает API ключ по индексу.
    
    Args:
        index (int): Индекс ключа в списке
        
    Returns:
        str: API ключ для использования с Gemini API
    """
    # Проверяем, что индекс находится в диапазоне
    if index < 0 or index >= len(GEMINI_API_KEYS):
        return get_random_key()
    return GEMINI_API_KEYS[index]
