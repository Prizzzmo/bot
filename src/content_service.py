"""Сервис для работы с историческим контентом"""

import json
import os
import time
from typing import Dict, Any, Optional, List, Callable

from src.interfaces import IContentProvider, ILogger

class ContentService(IContentProvider):
    """
    Имплементация интерфейса поставщика контента.
    Обеспечивает доступ к историческому контенту через API и локальные данные.
    """

    def __init__(self, api_client, logger: ILogger, events_file: str = 'historical_events.json'):
        """
        Инициализация сервиса контента.

        Args:
            api_client: Клиент для работы с внешним API
            logger (ILogger): Логгер для записи информации
            events_file (str): Путь к файлу с историческими событиями
        """
        self.api_client = api_client
        self.logger = logger
        self.events_file = events_file
        self.events_data = self._load_events_data()

        # Стандартный набор исторических тем
        self.default_topics = [
            "Киевская Русь",
            "Монгольское нашествие на Русь",
            "Образование Московского государства",
            "Смутное время",
            "Петр I и его реформы",
            "Отечественная война 1812 года",
            "Отмена крепостного права",
            "Октябрьская революция 1917 года",
            "Великая Отечественная война",
            "Распад СССР"
        ]

    def _load_events_data(self) -> Dict[str, Any]:
        """
        Загружает данные о исторических событиях из файла.

        Returns:
            Dict[str, Any]: Данные о исторических событиях
        """
        try:
            if os.path.exists(self.events_file):
                with open(self.events_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Создаем базовую структуру, если файл не существует
                events_data = {
                    "events": [],
                    "categories": [],
                    "periods": []
                }

                # Сохраняем структуру в файл
                with open(self.events_file, 'w', encoding='utf-8') as f:
                    json.dump(events_data, f, ensure_ascii=False, indent=2)

                return events_data

        except Exception as e:
            self.logger.error(f"Ошибка при загрузке данных о исторических событиях: {e}")
            return {
                "events": [],
                "categories": [],
                "periods": []
            }

    def validate_topic(self, topic: str) -> bool:
        """
        Проверяет является ли тема исторической.

        Args:
            topic (str): Тема для проверки

        Returns:
            bool: True если тема историческая, False в противном случае
        """
        # Проверяем, есть ли тема в списке стандартных исторических тем
        if any(default_topic.lower() in topic.lower() for default_topic in self.default_topics):
            return True

        # Проверяем, есть ли тема в загруженных событиях
        if self.events_data and "events" in self.events_data:
            for event in self.events_data["events"]:
                if "name" in event and event["name"].lower() in topic.lower():
                    return True

        # Если не нашли совпадений, используем API для проверки
        return self.api_client.validate_historical_topic(topic)


    def get_default_topics(self) -> List[str]:
        """
        Получение стандартного набора исторических тем.

        Returns:
            List[str]: Список стандартных исторических тем
        """
        return self.default_topics

    def get_historical_events(self, category: Optional[str] = None, timeframe: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Получение списка исторических событий с возможностью фильтрации.

        Args:
            category (str, optional): Категория для фильтрации
            timeframe (tuple, optional): Временной диапазон для фильтрации (год_начала, год_конца)

        Returns:
            List[Dict[str, Any]]: Список исторических событий
        """
        try:
            if not self.events_data or "events" not in self.events_data:
                return []

            events = self.events_data["events"]

            # Применяем фильтры, если они указаны
            if category:
                events = [event for event in events if "category" in event and event["category"] == category]

            if timeframe:
                start_year, end_year = timeframe
                events = [
                    event for event in events 
                    if "year" in event and start_year <= event["year"] <= end_year
                ]

            return events

        except Exception as e:
            self.logger.error(f"Ошибка при получении исторических событий: {e}")
            return []

    def _get_local_topic_info(self, topic: str) -> Optional[Dict[str, Any]]:
        """
        Поиск информации о теме в локальных данных.

        Args:
            topic (str): Историческая тема

        Returns:
            Dict[str, Any] or None: Информация о теме или None, если не найдена
        """
        if not self.events_data or "events" not in self.events_data:
            return None

        # Нормализуем тему для сравнения
        normalized_topic = topic.lower()

        # Ищем событие с похожим названием
        for event in self.events_data["events"]:
            if "name" in event and event["name"].lower() in normalized_topic:
                if "description" in event:
                    return {
                        "status": "success",
                        "topic": topic,
                        "content": event["description"],
                        "source": "local_database"
                    }

        return None

    def _save_topic_info(self, topic: str, content: str) -> None:
        """
        Сохраняет информацию о теме в локальные данные.

        Args:
            topic (str): Историческая тема
            content (str): Информация о теме
        """
        try:
            if not self.events_data:
                self.events_data = {"events": [], "categories": [], "periods": []}

            # Проверяем, есть ли уже информация об этой теме
            for event in self.events_data["events"]:
                if "name" in event and event["name"].lower() == topic.lower():
                    # Обновляем существующую информацию
                    event["description"] = content
                    event["updated_at"] = int(time.time())

                    # Сохраняем обновленные данные
                    with open(self.events_file, 'w', encoding='utf-8') as f:
                        json.dump(self.events_data, f, ensure_ascii=False, indent=2)

                    return

            # Если информации нет, добавляем новую запись
            new_event = {
                "name": topic,
                "description": content,
                "created_at": int(time.time()),
                "updated_at": int(time.time())
            }

            self.events_data["events"].append(new_event)

            # Сохраняем обновленные данные
            with open(self.events_file, 'w', encoding='utf-8') as f:
                json.dump(self.events_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"Ошибка при сохранении информации о теме '{topic}': {e}")
            
    def get_topic_info(self, topic: str, update_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Получение информации по исторической теме.

        Args:
            topic (str): Историческая тема
            update_callback (Optional[Callable]): Функция обратного вызова для обновления статуса

        Returns:
            Dict[str, Any]: Информация о теме
        """
        try:
            # Сначала ищем в локальных данных
            local_info = self._get_local_topic_info(topic)
            if local_info:
                self.logger.info(f"Найдена локальная информация по теме '{topic}'")
                return local_info

            # Если в локальных данных нет, запрашиваем через API
            self.logger.info(f"Запрос информации по теме '{topic}' через API")
            
            if update_callback:
                update_callback("Получение информации...")
                
            api_response = self.api_client.get_historical_info(topic)
            
            if api_response and "content" in api_response and api_response["status"] == "success":
                # Сохраняем полученную информацию локально
                self._save_topic_info(topic, api_response["content"])
                return api_response
            else:
                self.logger.warning(f"Не удалось получить информацию по теме '{topic}' через API")
                return {
                    "status": "error",
                    "topic": topic,
                    "error": "Не удалось получить информацию по данной исторической теме"
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка при получении информации по теме '{topic}': {e}")
            return {
                "status": "error",
                "topic": topic,
                "error": f"Произошла ошибка: {str(e)}"
            }
            
    def generate_test(self, topic: str) -> Dict[str, Any]:
        """
        Генерация теста по исторической теме.

        Args:
            topic (str): Историческая тема

        Returns:
            Dict[str, Any]: Тест с вопросами и ответами
        """
        try:
            self.logger.info(f"Генерация теста по теме '{topic}'")
            
            # Проверяем, является ли тема исторической
            if not self.validate_topic(topic):
                self.logger.warning(f"Попытка генерации теста для неисторической темы '{topic}'")
                return {
                    "status": "error",
                    "topic": topic,
                    "error": "Указанная тема не является исторической"
                }
            
            # Получаем тест через API
            test_response = self.api_client.generate_historical_test(topic)
            
            if test_response and "questions" in test_response and test_response["status"] == "success":
                self.logger.info(f"Успешно сгенерирован тест по теме '{topic}' ({len(test_response['questions'])} вопросов)")
                return test_response
            else:
                self.logger.warning(f"Не удалось сгенерировать тест по теме '{topic}'")
                return {
                    "status": "error",
                    "topic": topic,
                    "error": "Не удалось сгенерировать тест по данной теме"
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка при генерации теста по теме '{topic}': {e}")
            return {
                "status": "error",
                "topic": topic,
                "error": f"Произошла ошибка: {str(e)}"
            }