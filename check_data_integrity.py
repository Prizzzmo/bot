
#!/usr/bin/env python3
"""
Скрипт для проверки целостности данных пользователей и истории.
"""

import os
import json
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataIntegrityChecker:
    """Класс для проверки целостности данных"""
    
    def __init__(self):
        self.integrity_issues = []
        self.user_states_file = 'user_states.json'
        self.historical_events_file = 'historical_events.json'
        self.backup_dir = 'backups'
    
    def check_user_states(self):
        """Проверяет целостность данных о пользователях"""
        if not os.path.exists(self.user_states_file):
            self.integrity_issues.append({
                "severity": "ERROR",
                "message": f"Файл {self.user_states_file} не найден"
            })
            return False
        
        try:
            with open(self.user_states_file, 'r', encoding='utf-8') as f:
                user_states = json.load(f)
            
            # Проверка формата данных
            if not isinstance(user_states, dict):
                self.integrity_issues.append({
                    "severity": "ERROR", 
                    "message": f"Файл {self.user_states_file} имеет неверный формат (ожидается словарь)"
                })
                return False
            
            # Проверка структуры данных для каждого пользователя
            for user_id, user_data in user_states.items():
                if not isinstance(user_data, dict):
                    self.integrity_issues.append({
                        "severity": "WARNING",
                        "message": f"Данные пользователя {user_id} имеют неверный формат"
                    })
                    continue
                
                required_fields = ['state', 'last_activity']
                for field in required_fields:
                    if field not in user_data:
                        self.integrity_issues.append({
                            "severity": "WARNING",
                            "message": f"В данных пользователя {user_id} отсутствует обязательное поле '{field}'"
                        })
            
            logger.info(f"Проверено {len(user_states)} записей о пользователях")
            return True
            
        except json.JSONDecodeError as e:
            self.integrity_issues.append({
                "severity": "ERROR",
                "message": f"Ошибка при чтении файла {self.user_states_file}: {str(e)}"
            })
            return False
        except Exception as e:
            self.integrity_issues.append({
                "severity": "ERROR",
                "message": f"Непредвиденная ошибка при проверке {self.user_states_file}: {str(e)}"
            })
            return False
    
    def check_historical_events(self):
        """Проверяет целостность данных исторических событий"""
        if not os.path.exists(self.historical_events_file):
            self.integrity_issues.append({
                "severity": "ERROR",
                "message": f"Файл {self.historical_events_file} не найден"
            })
            return False
        
        try:
            with open(self.historical_events_file, 'r', encoding='utf-8') as f:
                events = json.load(f)
            
            # Проверка формата данных
            if not isinstance(events, dict) or "events" not in events:
                self.integrity_issues.append({
                    "severity": "ERROR", 
                    "message": f"Файл {self.historical_events_file} имеет неверный формат (ожидается словарь с ключом 'events')"
                })
                return False
            
            events_list = events.get("events", [])
            if not isinstance(events_list, list):
                self.integrity_issues.append({
                    "severity": "ERROR", 
                    "message": f"Поле 'events' в файле {self.historical_events_file} не является списком"
                })
                return False
            
            # Проверка структуры каждого события
            for i, event in enumerate(events_list):
                if not isinstance(event, dict):
                    self.integrity_issues.append({
                        "severity": "WARNING",
                        "message": f"Событие #{i} имеет неверный формат (не является словарем)"
                    })
                    continue
                
                required_fields = ['id', 'date', 'title', 'description']
                for field in required_fields:
                    if field not in event:
                        self.integrity_issues.append({
                            "severity": "WARNING",
                            "message": f"В событии #{i} (ID: {event.get('id', 'N/A')}) отсутствует обязательное поле '{field}'"
                        })
            
            logger.info(f"Проверено {len(events_list)} исторических событий")
            return True
            
        except json.JSONDecodeError as e:
            self.integrity_issues.append({
                "severity": "ERROR",
                "message": f"Ошибка при чтении файла {self.historical_events_file}: {str(e)}"
            })
            return False
        except Exception as e:
            self.integrity_issues.append({
                "severity": "ERROR",
                "message": f"Непредвиденная ошибка при проверке {self.historical_events_file}: {str(e)}"
            })
            return False
    
    def create_backup(self):
        """Создает резервную копию данных"""
        try:
            # Создаем директорию для резервных копий, если она не существует
            if not os.path.exists(self.backup_dir):
                os.makedirs(self.backup_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Бэкап файла user_states.json
            if os.path.exists(self.user_states_file):
                backup_path = os.path.join(self.backup_dir, f"user_states_backup_{timestamp}.json")
                with open(self.user_states_file, 'r', encoding='utf-8') as src:
                    with open(backup_path, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                logger.info(f"Создана резервная копия файла {self.user_states_file} в {backup_path}")
            
            # Бэкап файла historical_events.json
            if os.path.exists(self.historical_events_file):
                backup_path = os.path.join(self.backup_dir, f"historical_events_backup_{timestamp}.json")
                with open(self.historical_events_file, 'r', encoding='utf-8') as src:
                    with open(backup_path, 'w', encoding='utf-8') as dst:
                        dst.write(src.read())
                logger.info(f"Создана резервная копия файла {self.historical_events_file} в {backup_path}")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании резервной копии: {str(e)}")
            return False
    
    def run_check(self):
        """Запускает проверку целостности данных"""
        logger.info("Начинаем проверку целостности данных...")
        
        # Создаем резервную копию данных перед проверкой
        self.create_backup()
        
        # Проверяем данные пользователей
        logger.info("Проверка данных пользователей...")
        user_states_ok = self.check_user_states()
        
        # Проверяем исторические события
        logger.info("Проверка исторических событий...")
        historical_events_ok = self.check_historical_events()
        
        # Формируем отчет
        errors = sum(1 for issue in self.integrity_issues if issue["severity"] == "ERROR")
        warnings = sum(1 for issue in self.integrity_issues if issue["severity"] == "WARNING")
        
        logger.info("Проверка завершена!")
        logger.info(f"Найдено ошибок: {errors}")
        logger.info(f"Найдено предупреждений: {warnings}")
        
        return {
            "status": "OK" if user_states_ok and historical_events_ok else "ERROR",
            "errors": errors,
            "warnings": warnings,
            "issues": self.integrity_issues
        }
    
    def save_report(self, filename="data_integrity_report.json"):
        """Сохраняет отчет о проверке целостности данных в файл"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "errors": sum(1 for issue in self.integrity_issues if issue["severity"] == "ERROR"),
                "warnings": sum(1 for issue in self.integrity_issues if issue["severity"] == "WARNING"),
                "total_issues": len(self.integrity_issues)
            },
            "issues": sorted(self.integrity_issues, key=lambda x: 0 if x["severity"] == "ERROR" else 1)
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            logger.info(f"Отчет о проверке целостности данных сохранен в файл: {filename}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении отчета: {str(e)}")

if __name__ == "__main__":
    checker = DataIntegrityChecker()
    checker.run_check()
    checker.save_report()
