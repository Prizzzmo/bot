
class StateManager:
    """Класс для управления состояниями приложения"""
    
    def __init__(self):
        self.states = {}
        
    def get_user_state(self, user_id):
        """Получает текущее состояние пользователя"""
        return self.states.get(user_id, None)
        
    def set_user_state(self, user_id, state):
        """Устанавливает состояние пользователя"""
        self.states[user_id] = state
        
    def clear_user_state(self, user_id):
        """Очищает состояние пользователя"""
        if user_id in self.states:
            del self.states[user_id]
