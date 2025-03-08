
"""
Сервис миграции данных. 

Обеспечивает:
- Миграцию схемы данных при обновлении структуры
- Версионирование структур данных
- Проверку целостности данных
"""

import os
import json
import time
import shutil
from typing import Dict, Any, List, Optional
import logging

from src.interfaces import ILogger
from src.base_service import BaseService

class DataMigration(BaseService):
    """
    Сервис для миграции данных между различными версиями приложения.
    
    Обеспечивает:
    - Отслеживание версий схемы данных
    - Автоматическую миграцию данных при обновлении
    - Резервное копирование перед миграцией
    """
    
    def __init__(self, logger: ILogger, data_dir: str = '.'):
        """
        Инициализация сервиса миграции данных.
        
        Args:
            logger (ILogger): Логгер для записи информации
            data_dir (str): Директория с данными для миграции
        """
        super().__init__(logger)
        self.data_dir = data_dir
        self.migrations = []
        self.version_file = os.path.join(data_dir, 'data_version.json')
        self.current_version = self._get_current_version()
        
        # Регистрируем доступные миграции
        self._register_migrations()
    
    def _do_initialize(self) -> bool:
        """
        Выполняет фактическую инициализацию сервиса.
        
        Returns:
            bool: True если инициализация прошла успешно, иначе False
        """
        try:
            # Создаем резервную директорию если её нет
            backup_dir = os.path.join(self.data_dir, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Проверяем доступ к файлам
            self._save_current_version(self.current_version)
            
            return True
        except Exception as e:
            self._logger.error(f"Ошибка при инициализации DataMigration: {e}")
            return False
    
    def _get_current_version(self) -> int:
        """
        Получает текущую версию схемы данных.
        
        Returns:
            int: Номер текущей версии данных
        """
        try:
            if os.path.exists(self.version_file):
                with open(self.version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version', 0)
            else:
                # Если файл версии не существует, считаем версию 0
                return 0
        except Exception as e:
            self._logger.error(f"Ошибка при чтении версии данных: {e}")
            return 0
    
    def _save_current_version(self, version: int) -> None:
        """
        Сохраняет текущую версию схемы данных.
        
        Args:
            version (int): Номер версии для сохранения
        """
        try:
            with open(self.version_file, 'w', encoding='utf-8') as f:
                json.dump({'version': version, 'updated_at': time.time()}, f)
            self.current_version = version
        except Exception as e:
            self._logger.error(f"Ошибка при сохранении версии данных: {e}")
    
    def _register_migrations(self) -> None:
        """Регистрирует доступные миграции данных"""
        # Миграция с версии 0 на версию 1 (первоначальная структура)
        self.migrations.append({
            'from_version': 0,
            'to_version': 1,
            'description': 'Начальная структура данных',
            'handler': self._migrate_v0_to_v1
        })
        
        # Миграция с версии 1 на версию 2 (удаление структуры карт)
        self.migrations.append({
            'from_version': 1,
            'to_version': 2,
            'description': 'Удаление структуры исторических карт',
            'handler': self._migrate_v1_to_v2
        })
    
    def _migrate_v0_to_v1(self) -> bool:
        """
        Миграция данных с версии 0 на версию 1.
        
        Returns:
            bool: True если миграция успешна, иначе False
        """
        try:
            # Проверяем наличие необходимых файлов
            required_files = ['user_states.json', 'admins.json']
            for file in required_files:
                file_path = os.path.join(self.data_dir, file)
                if not os.path.exists(file_path):
                    # Создаем файл с базовой структурой
                    default_data = {}
                    
                    if file == 'user_states.json':
                        default_data = {'users': {}}
                    elif file == 'admins.json':
                        default_data = {'admin_ids': [], 'super_admin_ids': []}
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(default_data, f, ensure_ascii=False, indent=2)
                    
                    self._logger.info(f"Создан файл {file} с базовой структурой")
            
            return True
        except Exception as e:
            self._logger.error(f"Ошибка при миграции с версии 0 на версию 1: {e}")
            return False
    
    def _migrate_v1_to_v2(self) -> bool:
        """
        Миграция данных с версии 1 на версию 2 - удаление структуры исторических карт.
        
        Returns:
            bool: True если миграция успешна, иначе False
        """
        try:
            # Проверяем и удаляем файл исторических событий
            historical_events_file = os.path.join(self.data_dir, 'historical_events.json')
            if os.path.exists(historical_events_file):
                # Сначала создаем резервную копию
                backup_path = os.path.join(self.data_dir, 'backups', f'historical_events_backup_{int(time.time())}.json')
                shutil.copy2(historical_events_file, backup_path)
                self._logger.info(f"Создана резервная копия исторических событий: {backup_path}")
                
                # Удаляем оригинальный файл
                os.remove(historical_events_file)
                self._logger.info(f"Удален файл исторических событий: {historical_events_file}")
            
            # Проверяем и очищаем директорию с картами
            maps_dir = os.path.join(self.data_dir, 'generated_maps')
            if os.path.exists(maps_dir) and os.path.isdir(maps_dir):
                # Создаем резервную копию всей директории
                backup_maps_dir = os.path.join(
                    self.data_dir, 'backups', f'generated_maps_backup_{int(time.time())}'
                )
                if os.listdir(maps_dir):  # Копируем только если есть файлы
                    shutil.copytree(maps_dir, backup_maps_dir)
                    self._logger.info(f"Создана резервная копия сгенерированных карт: {backup_maps_dir}")
                
                    # Очищаем директорию
                    for item in os.listdir(maps_dir):
                        item_path = os.path.join(maps_dir, item)
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    
                    self._logger.info(f"Очищена директория с картами: {maps_dir}")
            
            # Обновляем user_states.json - удаляем записи о режиме карты
            user_states_file = os.path.join(self.data_dir, 'user_states.json')
            if os.path.exists(user_states_file):
                # Создаем резервную копию
                backup_states_path = os.path.join(
                    self.data_dir, 'backups', f'user_states_backup_{int(time.time())}.json'
                )
                shutil.copy2(user_states_file, backup_states_path)
                
                # Загружаем данные и удаляем информацию о картах
                with open(user_states_file, 'r', encoding='utf-8') as f:
                    user_states = json.load(f)
                
                # Удаляем состояния, связанные с картой
                if 'users' in user_states:
                    for user_id, user_data in user_states['users'].items():
                        if 'waiting_for_map_topic' in user_data:
                            del user_data['waiting_for_map_topic']
                        if 'last_map_category' in user_data:
                            del user_data['last_map_category']
                
                # Сохраняем обновленные данные
                with open(user_states_file, 'w', encoding='utf-8') as f:
                    json.dump(user_states, f, ensure_ascii=False, indent=2)
                
                self._logger.info(f"Обновлен файл состояний пользователей: {user_states_file}")
            
            return True
        except Exception as e:
            self._logger.error(f"Ошибка при миграции с версии 1 на версию 2: {e}")
            return False
    
    def check_and_migrate(self) -> bool:
        """
        Проверяет необходимость миграции и выполняет её при необходимости.
        
        Returns:
            bool: True если миграция не требовалась или была успешна, иначе False
        """
        try:
            # Получаем текущую версию данных
            current_version = self._get_current_version()
            self._logger.info(f"Текущая версия данных: {current_version}")
            
            # Определяем, какие миграции нужно выполнить
            pending_migrations = [
                m for m in self.migrations 
                if m['from_version'] == current_version
            ]
            
            if not pending_migrations:
                self._logger.info("Миграция не требуется, данные в актуальном состоянии")
                return True
            
            # Создаем общую резервную копию данных перед миграцией
            self._create_backup()
            
            # Выполняем миграции последовательно
            for migration in pending_migrations:
                self._logger.info(
                    f"Выполняется миграция с версии {migration['from_version']} на "
                    f"версию {migration['to_version']}: {migration['description']}"
                )
                
                # Выполняем миграцию
                success = migration['handler']()
                
                if success:
                    # Обновляем версию данных
                    self._save_current_version(migration['to_version'])
                    self._logger.info(
                        f"Миграция на версию {migration['to_version']} успешно завершена"
                    )
                else:
                    self._logger.error(
                        f"Ошибка при миграции на версию {migration['to_version']}"
                    )
                    return False
            
            return True
        except Exception as e:
            self._logger.error(f"Ошибка при проверке и выполнении миграции: {e}")
            return False
    
    def _create_backup(self) -> Optional[str]:
        """
        Создает полную резервную копию данных перед миграцией.
        
        Returns:
            Optional[str]: Путь к резервной копии или None в случае ошибки
        """
        try:
            # Создаем имя резервной копии на основе времени
            timestamp = int(time.time())
            backup_name = f'data_backup_v{self.current_version}_{timestamp}'
            backup_dir = os.path.join(self.data_dir, 'backups', backup_name)
            
            # Создаем директорию для резервной копии
            os.makedirs(backup_dir, exist_ok=True)
            
            # Копируем все JSON файлы из корневой директории
            for file in os.listdir(self.data_dir):
                if file.endswith('.json') and os.path.isfile(os.path.join(self.data_dir, file)):
                    src_path = os.path.join(self.data_dir, file)
                    dst_path = os.path.join(backup_dir, file)
                    shutil.copy2(src_path, dst_path)
            
            self._logger.info(f"Создана резервная копия данных: {backup_dir}")
            return backup_dir
        except Exception as e:
            self._logger.error(f"Ошибка при создании резервной копии данных: {e}")
            return None
    
    def restore_backup(self, backup_path: Optional[str] = None) -> bool:
        """
        Восстанавливает данные из резервной копии.
        
        Args:
            backup_path (str, optional): Путь к конкретной резервной копии.
                Если не указан, используется последняя доступная копия.
                
        Returns:
            bool: True если восстановление успешно, иначе False
        """
        try:
            # Получаем путь к резервной копии
            if not backup_path:
                # Ищем последнюю резервную копию
                backups_dir = os.path.join(self.data_dir, 'backups')
                if not os.path.exists(backups_dir) or not os.path.isdir(backups_dir):
                    self._logger.error("Директория с резервными копиями не найдена")
                    return False
                
                # Ищем директории с бэкапами, сортируем по времени создания
                backup_dirs = [
                    d for d in os.listdir(backups_dir) 
                    if os.path.isdir(os.path.join(backups_dir, d)) and d.startswith('data_backup_v')
                ]
                if not backup_dirs:
                    self._logger.error("Резервные копии не найдены")
                    return False
                
                # Сортируем по времени (берем последнюю)
                backup_dirs.sort(reverse=True)
                backup_path = os.path.join(backups_dir, backup_dirs[0])
            
            if not os.path.exists(backup_path) or not os.path.isdir(backup_path):
                self._logger.error(f"Путь к резервной копии не существует: {backup_path}")
                return False
            
            # Восстанавливаем файлы из резервной копии
            for file in os.listdir(backup_path):
                if file.endswith('.json'):
                    src_path = os.path.join(backup_path, file)
                    dst_path = os.path.join(self.data_dir, file)
                    shutil.copy2(src_path, dst_path)
            
            self._logger.info(f"Данные успешно восстановлены из резервной копии: {backup_path}")
            
            # Обновляем текущую версию после восстановления
            self.current_version = self._get_current_version()
            
            return True
        except Exception as e:
            self._logger.error(f"Ошибка при восстановлении данных из резервной копии: {e}")
            return False
    
    def get_available_backups(self) -> List[Dict[str, Any]]:
        """
        Получает список доступных резервных копий.
        
        Returns:
            List[Dict[str, Any]]: Список резервных копий с метаданными
        """
        backups = []
        try:
            backups_dir = os.path.join(self.data_dir, 'backups')
            if not os.path.exists(backups_dir) or not os.path.isdir(backups_dir):
                return []
            
            # Ищем директории с бэкапами
            for d in os.listdir(backups_dir):
                dir_path = os.path.join(backups_dir, d)
                if os.path.isdir(dir_path) and d.startswith('data_backup_v'):
                    try:
                        # Парсим версию и временную метку из имени
                        parts = d.split('_')
                        version = int(parts[2][1:])  # Извлекаем число после 'v'
                        timestamp = int(parts[3]) if len(parts) > 3 else 0
                        
                        # Получаем количество файлов в бэкапе
                        file_count = len([f for f in os.listdir(dir_path) if f.endswith('.json')])
                        
                        backups.append({
                            'path': dir_path,
                            'name': d,
                            'version': version,
                            'timestamp': timestamp,
                            'date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp)),
                            'file_count': file_count
                        })
                    except (ValueError, IndexError) as e:
                        self._logger.warning(f"Ошибка при парсинге имени резервной копии {d}: {e}")
            
            # Сортируем по времени (от новых к старым)
            backups.sort(key=lambda b: b['timestamp'], reverse=True)
            
        except Exception as e:
            self._logger.error(f"Ошибка при получении списка резервных копий: {e}")
        
        return backups
