"""Менеджер состояний для управления пользовательскими диалогами"""

import json
import os
import time
import threading
from typing import Dict, Any, Optional, List

from src.interfaces import IStateManager, ILogger
from src.base_service import BaseService

class StateManager(BaseService):
    """
    Имплементация интерфейса менеджера состояний.
    Обеспечивает хранение и управление состояниями пользовательских диалогов.
    """

    def __init__(self, logger: ILogger, state_file: str = 'user_states.json', auto_save: bool = True, save_interval: int = 300):
        """
        Инициализация менеджера состояний.

        Args:
            logger (ILogger): Логгер для записи информации
            state_file (str): Путь к файлу для хранения состояний
            auto_save (bool): Автоматически сохранять состояния с интервалом
            save_interval (int): Интервал автосохранения в секундах
        """
        super().__init__(logger)
        self.state_file = state_file
        self.auto_save = auto_save
        self.save_interval = save_interval
        self.states: Dict[int, Dict[str, Any]] = {}
        self.lock = threading.RLock()  # Для потокобезопасности
        self.last_save_time = 0

        # Загружаем состояния из файла
        self._load_states()

        # Запускаем автосохранение, если оно включено
        if self.auto_save:
            self._start_auto_save()

    def _do_initialize(self) -> bool:
        """
        Выполняет фактическую инициализацию сервиса.

        Returns:
            bool: True если инициализация прошла успешно, иначе False
        """
        try:
            return True
        except Exception as e:
            self._logger.error(f"Ошибка при инициализации StateManager: {e}")
            return False


    def get_user_state(self, user_id: int) -> Dict[str, Any]:
        """
        Получение текущего состояния пользователя.

        Args:
            user_id (int): ID пользователя

        Returns:
            Dict[str, Any]: Состояние пользователя
        """
        with self.lock:
            # Если состояние для пользователя не существует, создаем его
            if str(user_id) not in self.states:
                self.states[str(user_id)] = {
                    "current_state": None,
                    "conversation_history": [],
                    "last_interaction": int(time.time()),
                    "context": {}
                }

            # Обновляем время последнего взаимодействия
            self.states[str(user_id)]["last_interaction"] = int(time.time())

            return self.states[str(user_id)]

    def set_user_state(self, user_id: int, state_data: Dict[str, Any]) -> None:
        """
        Установка состояния пользователя.

        Args:
            user_id (int): ID пользователя
            state_data (Dict[str, Any]): Новое состояние пользователя
        """
        with self.lock:
            self.states[str(user_id)] = state_data
            self.states[str(user_id)]["last_interaction"] = int(time.time())

            # Сохраняем состояния, если прошло достаточно времени с последнего сохранения
            current_time = time.time()
            if current_time - self.last_save_time > self.save_interval:
                self._save_states()
                self.last_save_time = current_time

    def update_user_state(self, user_id: int, updates: Dict[str, Any]) -> None:
        """
        Обновление состояния пользователя.

        Args:
            user_id (int): ID пользователя
            updates (Dict[str, Any]): Обновления состояния
        """
        with self.lock:
            # Получаем текущее состояние
            user_state = self.get_user_state(user_id)

            # Обновляем состояние
            for key, value in updates.items():
                if key == "conversation_history" and "conversation_history" in user_state:
                    # Для истории диалога добавляем новую запись
                    user_state["conversation_history"].append(value)

                    # Ограничиваем размер истории диалога
                    max_history = 20  # Максимальное количество сообщений в истории
                    if len(user_state["conversation_history"]) > max_history:
                        user_state["conversation_history"] = user_state["conversation_history"][-max_history:]
                else:
                    # Для остальных полей просто обновляем значение
                    user_state[key] = value

            # Обновляем время последнего взаимодействия
            user_state["last_interaction"] = int(time.time())

            # Сохраняем обновленное состояние
            self.states[str(user_id)] = user_state

            # Сохраняем состояния, если прошло достаточно времени с последнего сохранения
            current_time = time.time()
            if current_time - self.last_save_time > self.save_interval:
                self._save_states()
                self.last_save_time = current_time

    def clear_user_state(self, user_id: int) -> None:
        """
        Очистка состояния пользователя.

        Args:
            user_id (int): ID пользователя
        """
        with self.lock:
            # Удаляем состояние пользователя
            if str(user_id) in self.states:
                del self.states[str(user_id)]

                # Сохраняем состояния
                self._save_states()

    def has_active_conversation(self, user_id: int) -> bool:
        """
        Проверка наличия активного диалога.

        Args:
            user_id (int): ID пользователя

        Returns:
            bool: True если у пользователя есть активный диалог, False в противном случае
        """
        with self.lock:
            user_state = self.get_user_state(user_id)
            return user_state.get("current_state") is not None

    def get_active_users(self, time_threshold: int = 3600) -> List[int]:
        """
        Получение списка активных пользователей.

        Args:
            time_threshold (int): Временной порог в секундах (по умолчанию 1 час)

        Returns:
            List[int]: Список ID активных пользователей
        """
        with self.lock:
            current_time = int(time.time())
            active_users = []

            for user_id, state in self.states.items():
                last_interaction = state.get("last_interaction", 0)
                if current_time - last_interaction <= time_threshold:
                    try:
                        active_users.append(int(user_id))
                    except ValueError:
                        pass

            return active_users

    def _load_states(self) -> None:
        """Загружает состояния из файла"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.states = json.load(f)
                self._logger.info(f"Загружены состояния для {len(self.states)} пользователей")
            else:
                self.states = {}
        except Exception as e:
            self._logger.error(f"Ошибка при загрузке состояний: {e}")
            self.states = {}

    def _save_states(self) -> None:
        """Сохраняет состояния в файл"""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.states, f, ensure_ascii=False, indent=2)
            self.last_save_time = time.time()
            self._logger.debug(f"Сохранены состояния для {len(self.states)} пользователей")
        except Exception as e:
            self._logger.error(f"Ошибка при сохранении состояний: {e}")

    def _start_auto_save(self) -> None:
        """Запускает фоновый поток для автоматического сохранения состояний"""
        def auto_save_job():
            while True:
                time.sleep(self.save_interval)
                try:
                    with self.lock:
                        self._save_states()
                except Exception as e:
                    self._logger.error(f"Ошибка в фоновом сохранении состояний: {e}")

        # Запускаем поток как демон, чтобы он автоматически завершался с основным потоком
        auto_save_thread = threading.Thread(target=auto_save_job, daemon=True)
        auto_save_thread.start()

    def cleanup_inactive_users(self, time_threshold: int = 86400 * 7) -> int:
        """
        Очищает состояния неактивных пользователей.

        Args:
            time_threshold (int): Временной порог в секундах (по умолчанию 7 дней)

        Returns:
            int: Количество удаленных состояний
        """
        with self.lock:
            current_time = int(time.time())
            inactive_users = []

            for user_id, state in self.states.items():
                last_interaction = state.get("last_interaction", 0)
                if current_time - last_interaction > time_threshold:
                    inactive_users.append(user_id)

            # Удаляем состояния неактивных пользователей
            for user_id in inactive_users:
                del self.states[user_id]

            # Сохраняем состояния
            if inactive_users:
                self._save_states()

            return len(inactive_users)