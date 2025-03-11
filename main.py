"""
Главный модуль для запуска образовательного Telegram бота по истории России.

Этот модуль инициализирует всю экосистему приложения, включая:
- Настройку логирования
- Загрузку конфигурации из .env файла
- Создание и запуск бота через фабрику
- Обработку исключений и корректное завершение работы
"""

import logging
import os
import traceback
import sys
import atexit
from dotenv import load_dotenv
import threading

from src.config import Config
from src.factory import BotFactory
from src.data_migration import DataMigration
from src.task_queue import TaskQueue

def check_running_bot():
    """
    Проверяет, не запущен ли уже экземпляр бота.
    Создает и проверяет lock-файл.

    Returns:
        bool: True если можно запускать бота, False если уже запущен
    """
    import os
    import sys

    lock_file = "bot.lock"

    # Проверяем существование lock-файла
    if os.path.exists(lock_file):
        try:
            # Читаем PID из lock-файла
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())

            # Проверяем, существует ли процесс с таким PID
            # Для Linux
            if os.path.exists(f"/proc/{pid}"):
                return False

            # Если процесс не существует, удаляем устаревший lock-файл
            os.remove(lock_file)
        except (IOError, ValueError):
            # Если файл поврежден или не содержит PID, удаляем его
            os.remove(lock_file)

    # Создаем новый lock-файл с текущим PID
    with open(lock_file, 'w') as f:
        f.write(str(os.getpid()))

    return True

def start_bot(config, logger):
    """Creates and runs the bot."""
    logger.info("Создание бота через фабрику")
    bot = BotFactory.create_bot(config)

    # Проверяем, что бот был успешно создан
    if not bot:
        logger.error("Не удалось создать экземпляр бота!")
        return

    # Настраиваем бота
    logger.info("Настройка бота")
    if not bot.setup():
        logger.error("Ошибка при настройке бота!")
        return

    logger.info("Бот успешно настроен и готов к запуску")

    # Проверяем необходимость миграции данных
    data_migration = DataMigration(logger)
    if data_migration.check_and_migrate():
        logger.info("Миграция данных успешно завершена или не требовалась")
    else:
        logger.warning("Возникли проблемы при миграции данных, проверьте логи")

    # Инициализируем очередь отложенных задач
    task_queue = TaskQueue(num_workers=2, logger=logger)
    task_queue.start()
    logger.info("Инициализирована система отложенных задач")

    # Регистрируем очередь задач в конфигурации для доступа из других модулей
    config.set_task_queue(task_queue)

    # Запускаем бота напрямую в основном потоке
    bot.run()


def start_admin_panel():
    """Запускает админ-панель в отдельном потоке"""
    from webapp.admin_server import run_admin_server
    import threading

    # Запускаем админ-сервер в отдельном потоке
    admin_thread = threading.Thread(target=run_admin_server, kwargs={'host': '0.0.0.0', 'port': 8000})
    admin_thread.daemon = True
    admin_thread.start()
    logging.info("Сервер админ-панели запущен на порту 8000")

def main():
    """
    Основная функция для запуска бота и веб-сервера
    """
    # Запуск веб-сервера в отдельном потоке
    import threading
    from webapp.server import run_server

    # Устанавливаем переменную окружения для вебсервера
    repl_id = os.environ.get('REPL_ID', '')
    repl_slug = os.environ.get('REPL_SLUG', '')
    repl_owner = os.environ.get('REPL_OWNER', '')
    deployment_id = os.environ.get('REPL_DEPLOYMENT_ID', '')

    # Сохраняем URL в переменной окружения для использования в bot_integration.py
    if deployment_id:
        os.environ['WEBAPP_URL'] = f"https://{deployment_id}.deployment.repl.co"
    elif repl_slug and repl_owner:
        os.environ['WEBAPP_URL'] = f"https://{repl_slug}.{repl_owner}.repl.co"
    else:
        os.environ['WEBAPP_URL'] = f"https://{repl_id}.id.repl.co"

    # Запускаем веб-сервер
    webapp_thread = threading.Thread(target=run_server, args=('0.0.0.0', 8080), daemon=True)
    webapp_thread.start()
    print(f"Веб-сервер запущен на порту 8080 с URL: {os.environ.get('WEBAPP_URL')}")

    logger = None

    try:
        # Проверяем, не запущен ли уже бот
        if not check_running_bot():
            print("Бот уже запущен в другом процессе. Завершение работы.")
            sys.exit(1)

        # Загружаем переменные окружения из .env файла
        load_dotenv()

        # Настраиваем базовое логирование с оптимизированными параметрами
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)
        logger.info("Запуск историчеcкого образовательного бота")

        # Предварительно проверяем наличие всех необходимых директорий
        # для предотвращения ошибок при параллельной работе
        for directory in ["logs", "generated_maps"]:
            if not os.path.exists(directory):
                os.makedirs(directory)

        # Загружаем конфигурацию
        logger.info("Загрузка конфигурации")
        config = Config()

        # Проверяем валидность конфигурации
        if not config.validate():
            logger.error("Ошибка в конфигурации! Проверьте .env файл.")
            return

        start_admin_panel()
        start_bot(config, logger)


    except KeyboardInterrupt:
        if logger:
            logger.info("Бот остановлен пользователем")
        # Удаляем lock-файл при завершении работы
        if os.path.exists("bot.lock"):
            os.remove("bot.lock")
    except Exception as e:
        if logger:
            logger.error(f"Критическая ошибка: {e}")
            logger.error(traceback.format_exc())
        else:
            print(f"Критическая ошибка: {e}")
            print(traceback.format_exc())

        # Удаляем lock-файл при завершении работы с ошибкой
        if os.path.exists("bot.lock"):
            os.remove("bot.lock")

        # Завершаем процесс с кодом ошибки
        sys.exit(1)
    finally:
        # Гарантированное удаление lock-файла в любом случае
        if os.path.exists("bot.lock"):
            os.remove("bot.lock")

def check_system_resources():
    """
    Проверяет доступные системные ресурсы и оптимизирует настройки
    в зависимости от доступных ресурсов
    """
    import psutil
    import os
    from src.logger import Logger
    
    logger = Logger()
    
    try:
        # Проверяем доступную память
        memory = psutil.virtual_memory()
        memory_available_mb = memory.available / (1024 * 1024)
        total_memory_mb = memory.total / (1024 * 1024)
        
        # Проверяем доступное место на диске
        disk = psutil.disk_usage('/')
        disk_free_mb = disk.free / (1024 * 1024)
        
        # Проверяем количество доступных процессоров
        cpu_count = psutil.cpu_count(logical=False) or 1
        
        logger.info(f"Запуск с {cpu_count} CPU, {memory_available_mb:.1f} МБ свободной RAM и {disk_free_mb:.1f} МБ на диске")
        
        # Оптимизации на основе ресурсов
        # 1. Размер кэша на основе доступной памяти
        cache_size_limit = min(int(memory_available_mb * 0.2), 500)  # Не более 20% RAM или 500 МБ
        os.environ['API_CACHE_SIZE_LIMIT'] = str(cache_size_limit)
        
        # 2. Количество рабочих потоков на основе ядер CPU
        worker_count = max(1, min(cpu_count, 4))  # От 1 до 4 рабочих потоков
        os.environ['WORKER_THREAD_COUNT'] = str(worker_count)
        
        # 3. Интервал автосохранения метрик на основе доступного места
        if disk_free_mb < 500:  # Если менее 500 МБ свободного места
            os.environ['METRICS_SAVE_INTERVAL'] = '3600'  # Сохранять метрики раз в час
            os.environ['METRICS_RETENTION_DAYS'] = '1'    # Хранить метрики только за 1 день
            logger.warning("Мало места на диске, ограничено сохранение метрик")
        else:
            os.environ['METRICS_SAVE_INTERVAL'] = '900'   # Сохранять метрики каждые 15 минут
            os.environ['METRICS_RETENTION_DAYS'] = '7'    # Хранить метрики за неделю
        
        # 4. Решение об очистке старых логов
        try:
            logs_dir = 'logs'
            if os.path.exists(logs_dir) and disk_free_mb < 1000:
                log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
                # Сортируем по времени изменения (от старых к новым)
                log_files.sort(key=lambda x: os.path.getmtime(os.path.join(logs_dir, x)))
                
                # Оставляем только 3 последних лог-файла если мало места
                if len(log_files) > 3:
                    for old_log in log_files[:-3]:
                        os.remove(os.path.join(logs_dir, old_log))
                    logger.info(f"Удалено {len(log_files) - 3} устаревших лог-файлов для освобождения места")
        except Exception as e:
            logger.error(f"Ошибка при очистке старых логов: {e}")
        
        # 5. Проверка и оптимизация размеров кэш-файлов
        cache_files = ['api_cache.json', 'local_cache.json']
        total_cache_size = 0
        
        for cache_file in cache_files:
            if os.path.exists(cache_file):
                file_size_mb = os.path.getsize(cache_file) / (1024 * 1024)
                total_cache_size += file_size_mb
                
                # Если файл кэша слишком большой, пометим его для очистки
                if file_size_mb > 50:  # Более 50 МБ
                    os.environ[f'CLEAN_{cache_file.upper().replace(".", "_")}'] = 'true'
        
        # Если общий размер кэш-файлов занимает более 30% свободного места, принудительно очищаем
        if total_cache_size > (disk_free_mb * 0.3):
            os.environ['FORCE_CLEAN_ALL_CACHES'] = 'true'
            logger.warning(f"Кэш-файлы ({total_cache_size:.1f} МБ) занимают слишком много места, будет выполнена принудительная очистка")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при проверке системных ресурсов: {e}")
        return False

def clear_caches():
    """Очищает все кэши при запуске проекта"""
    from src.logger import Logger
    from src.config import Config
    import os
    
    logger = Logger()
    config = Config()
    
    # Проверяем, включена ли автоматическая очистка кэша или принудительная очистка
    force_clean = os.environ.get('FORCE_CLEAN_ALL_CACHES', 'false').lower() == 'true'
    
    if not force_clean and (not hasattr(config, 'clear_cache_on_startup') or not config.clear_cache_on_startup):
        logger.info("Автоматическая очистка кэша при запуске отключена в конфигурации")
        return
    
    try:
        import gc
        # Запускаем сборщик мусора перед очисткой кэша
        gc.collect()
        
        # Очистка API кэша
        from src.api_cache import APICache
        api_cache = APICache(logger)
        
        # Получаем оптимальный размер кэша из переменной окружения
        if 'API_CACHE_SIZE_LIMIT' in os.environ:
            api_cache.max_size = int(os.environ['API_CACHE_SIZE_LIMIT'])
        
        # Проверяем нужна ли принудительная очистка конкретного кэша
        if force_clean or os.environ.get('CLEAN_API_CACHE_JSON', 'false').lower() == 'true':
            cleared_items = api_cache.clear_cache()
            logger.info(f"При запуске проекта очищено {cleared_items} записей из API кэша (принудительная очистка)")
        else:
            # Проверяем заполненность кэша 
            stats = api_cache.get_stats()
            if stats.get("fill_percentage", 0) > 80:  # Если заполнен более чем на 80%
                cleared_items = api_cache.clear_cache()
                logger.info(f"При запуске проекта очищено {cleared_items} записей из API кэша (заполнен на {stats.get('fill_percentage'):.1f}%)")
        
        # Очистка распределенного кэша, если он используется
        try:
            from src.distributed_cache import DistributedCache
            distributed_cache = DistributedCache(logger)
            
            # Проверяем нужна ли принудительная очистка
            if force_clean or os.environ.get('CLEAN_LOCAL_CACHE_JSON', 'false').lower() == 'true':
                cleared_distributed = distributed_cache.clear_cache()
                logger.info(f"При запуске проекта очищено {cleared_distributed} записей из распределенного кэша (принудительная очистка)")
            else:
                stats = distributed_cache.get_stats()
                if stats.get("local_fill_percentage", 0) > 80:
                    cleared_distributed = distributed_cache.clear_cache()
                    logger.info(f"При запуске проекта очищено {cleared_distributed} записей из распределенного кэша (заполнен на {stats.get('local_fill_percentage'):.1f}%)")
        except Exception as e:
            logger.debug(f"Распределенный кэш не используется или произошла ошибка: {e}")
        
        # Очистка текстового кэша, если он используется
        try:
            from src.text_cache_service import TextCacheService
            text_cache = TextCacheService(logger)
            
            if force_clean:
                cleared_text = text_cache.clear_cache()
                logger.info(f"При запуске проекта очищено {cleared_text} записей из текстового кэша (принудительная очистка)")
        except Exception as e:
            logger.debug(f"Текстовый кэш не используется или произошла ошибка: {e}")
            
        # Запускаем сборщик мусора после очистки кэша
        gc.collect()
        
        logger.info("Автоматическая очистка кэша при запуске успешно выполнена")
    except Exception as e:
        logger.error(f"Ошибка при автоматической очистке кэша при запуске: {e}")

def run_cleanup_if_needed():
    """Запускает скрипт очистки, если это необходимо"""
    import os
    from datetime import datetime, timedelta
    
    try:
        # Проверяем свободное место на диске
        import psutil
        disk = psutil.disk_usage('/')
        disk_free_mb = disk.free / (1024 * 1024)
        
        # Проверяем дату последней очистки
        last_cleanup_file = 'last_cleanup.txt'
        run_cleanup = False
        
        # Запускаем очистку если мало места (менее 500 МБ)
        if disk_free_mb < 500:
            run_cleanup = True
        elif os.path.exists(last_cleanup_file):
            try:
                with open(last_cleanup_file, 'r') as f:
                    last_date_str = f.readline().strip()
                    last_date = datetime.strptime(last_date_str, '%Y-%m-%d %H:%M:%S')
                    
                    # Запускаем очистку раз в 3 дня
                    if datetime.now() - last_date > timedelta(days=3):
                        run_cleanup = True
            except Exception:
                # Если не удалось прочитать дату, запускаем очистку
                run_cleanup = True
        else:
            # Если файл с датой последней очистки не существует
            run_cleanup = True
        
        if run_cleanup:
            import subprocess
            import sys
            
            # Запускаем скрипт очистки в фоновом режиме
            python_executable = sys.executable
            subprocess.Popen([python_executable, 'cleanup_old_backups.py'])
    except Exception as e:
        # Игнорируем ошибки при проверке необходимости очистки
        print(f"Ошибка при проверке необходимости очистки: {e}")

if __name__ == "__main__":
    # Проверка системных ресурсов и оптимизация
    check_system_resources()
    
    # Запуск очистки старых файлов при необходимости
    run_cleanup_if_needed()
    
    # Очистка кэшей при запуске
    clear_caches()
    
    # Запуск основного приложения
    main()