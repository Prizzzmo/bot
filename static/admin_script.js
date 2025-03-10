
// Глобальные переменные
let isAuthenticated = false;
let currentUser = null;
let isDarkTheme = localStorage.getItem('admin_dark_theme') === 'true';
let sidebarCollapsed = localStorage.getItem('admin_sidebar_collapsed') === 'true';
let currentPage = 'dashboard';
let eventsPagination = { currentPage: 1, totalPages: 1, itemsPerPage: 25 };
let usersPagination = { currentPage: 1, totalPages: 1, itemsPerPage: 25 };
let systemInfo = {};
let maintenanceStatus = {};
let adminTypes = {
    admin: "Администратор",
    super: "Супер-администратор"
};

// Инициализация при загрузке документа
document.addEventListener('DOMContentLoaded', function() {
    // Проверяем авторизацию
    checkAuthentication();
    
    // Применяем сохраненную тему
    applyTheme();
    
    // Применяем сохраненное состояние боковой панели
    applySidebarState();
    
    // Регистрируем обработчики событий для UI компонентов
    registerEventHandlers();
    
    // Обновляем время сервера
    startServerTimeUpdater();
});

// Проверка аутентификации
function checkAuthentication() {
    // В данной версии автоматически аутентифицируем пользователя
    isAuthenticated = true;
    // Создаем дефолтного пользователя
    currentUser = {
        id: 7225056628, // ID из admins.json
        is_super_admin: true
    };
    
    // Показываем админ-панель и загружаем данные
    showAdminPanel();
    loadAdminData();
    updateUserInfo();
}

// Показываем админ-панель
function showAdminPanel() {
    const adminContainer = document.querySelector('.app-container');
    if (adminContainer) {
        adminContainer.style.display = 'flex';
    }
}

// Загрузка данных для админ-панели
function loadAdminData() {
    // Загружаем данные для выбранной страницы
    loadPageData(currentPage);
    
    // Общие данные для всех страниц
    loadAdminsData();
}

// Загрузка данных для конкретной страницы
function loadPageData(page) {
    switch(page) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'events':
            loadEventsData();
            break;
        case 'users':
            loadUsersData();
            break;
        case 'admins':
            loadAdminsData();
            break;
        case 'logs':
            loadLogsData();
            break;
        case 'settings':
            loadSettingsData();
            break;
        case 'maintenance':
            loadMaintenanceData();
            break;
    }
    
    // Обновляем хлебные крошки и активный пункт меню
    updateBreadcrumbs(page);
    updateActiveMenuItem(page);
}

// Обновление хлебных крошек
function updateBreadcrumbs(page) {
    const pageIcons = {
        'dashboard': 'fa-tachometer-alt',
        'events': 'fa-calendar-alt',
        'users': 'fa-users',
        'admins': 'fa-user-shield',
        'logs': 'fa-file-alt',
        'settings': 'fa-cog',
        'maintenance': 'fa-tools'
    };
    
    const pageNames = {
        'dashboard': 'Обзор',
        'events': 'События истории',
        'users': 'Пользователи',
        'admins': 'Администраторы',
        'logs': 'Логи',
        'settings': 'Настройки',
        'maintenance': 'Обслуживание'
    };
    
    document.getElementById('current-section-icon').className = `fas ${pageIcons[page]}`;
    document.getElementById('current-section-name').textContent = pageNames[page];
}

// Обновление активного пункта меню
function updateActiveMenuItem(page) {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    const activeItem = document.querySelector(`.nav-item[data-page="${page}"]`);
    if (activeItem) {
        activeItem.classList.add('active');
    }
}

// Регистрация обработчиков событий
function registerEventHandlers() {
    // Обработка переключения страниц в боковой панели
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const page = this.getAttribute('data-page');
            switchPage(page);
        });
    });
    
    // Обработка нажатия на выход
    document.getElementById('logout-button').addEventListener('click', handleLogout);
    
    // Обработка переключения темы
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
    
    // Обработка переключения боковой панели
    document.getElementById('sidebar-toggle').addEventListener('click', toggleSidebar);
    
    // Обработка полноэкранного режима
    document.getElementById('fullscreen-toggle').addEventListener('click', toggleFullscreen);
    
    // Обработка обновления данных
    document.getElementById('refresh-data').addEventListener('click', refreshCurrentPageData);
    
    // События формы настроек
    const settingsForm = document.getElementById('settings-form');
    if (settingsForm) {
        settingsForm.addEventListener('submit', handleSettingsSubmit);
    }
    
    // Обработчики для страницы администраторов
    const addAdminForm = document.getElementById('add-admin-form');
    if (addAdminForm) {
        addAdminForm.addEventListener('submit', handleAddAdminSubmit);
    }
    
    const removeAdminForm = document.getElementById('remove-admin-form');
    if (removeAdminForm) {
        removeAdminForm.addEventListener('submit', handleRemoveAdminSubmit);
    }
    
    // Обработчики для модальных окон
    document.getElementById('modal-overlay').addEventListener('click', function(e) {
        if (e.target === this) {
            closeModal();
        }
    });
    
    // Обработчики для операций обслуживания
    document.querySelectorAll('.maintenance-action').forEach(button => {
        button.addEventListener('click', handleMaintenanceAction);
    });
    
    // Обработчики для таблиц данных
    setupEventsTableHandlers();
    setupUsersTableHandlers();
    
    // Обработчики для панели логов
    setupLogsHandlers();
    
    // Глобальный поиск
    document.getElementById('global-search').addEventListener('input', handleGlobalSearch);
    
    // Привязываем обработчики для связанных элементов управления
    setupRangeInputSync();
    
    // Привязываем выбор периода активности к обновлению графика
    document.getElementById('activity-period').addEventListener('change', updateActivityChart);
    
    // Кнопка просмотра всех активностей
    document.getElementById('view-all-activities').addEventListener('click', viewAllActivities);
    
    // Кнопка проверки системы
    document.getElementById('check-system').addEventListener('click', checkSystemStatus);
}

// Переключение страницы
function switchPage(page) {
    // Скрываем все страницы
    document.querySelectorAll('.page').forEach(p => {
        p.classList.remove('active');
    });
    
    // Показываем выбранную страницу
    const activePage = document.getElementById(`${page}-page`);
    if (activePage) {
        activePage.classList.add('active');
        currentPage = page;
        
        // Загружаем данные для выбранной страницы
        loadPageData(page);
        
        // Обновляем URL с использованием hash
        window.location.hash = page;
    }
}

// Обработка выхода из админ-панели
function handleLogout() {
    // Очищаем куки администратора
    document.cookie = 'admin_id=; Max-Age=0; path=/;';
    
    // Перезагружаем страницу или перенаправляем
    window.location.href = '/';
}

// Переключение темы (светлая/темная)
function toggleTheme() {
    isDarkTheme = !isDarkTheme;
    localStorage.setItem('admin_dark_theme', isDarkTheme);
    applyTheme();
}

// Применение выбранной темы
function applyTheme() {
    const body = document.body;
    const themeIcon = document.querySelector('#theme-toggle i');
    
    if (isDarkTheme) {
        body.classList.add('dark-theme');
        themeIcon.classList.remove('fa-moon');
        themeIcon.classList.add('fa-sun');
    } else {
        body.classList.remove('dark-theme');
        themeIcon.classList.remove('fa-sun');
        themeIcon.classList.add('fa-moon');
    }
}

// Переключение сворачивания боковой панели
function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
    localStorage.setItem('admin_sidebar_collapsed', sidebarCollapsed);
    applySidebarState();
}

// Применение состояния боковой панели
function applySidebarState() {
    const body = document.body;
    
    if (sidebarCollapsed) {
        body.classList.add('sidebar-collapsed');
    } else {
        body.classList.remove('sidebar-collapsed');
    }
}

// Переключение полноэкранного режима
function toggleFullscreen() {
    const fsIcon = document.querySelector('#fullscreen-toggle i');
    
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => {
            showNotification('Ошибка включения полноэкранного режима: ' + err.message, 'error');
        });
        
        fsIcon.classList.remove('fa-expand');
        fsIcon.classList.add('fa-compress');
    } else {
        if (document.exitFullscreen) {
            document.exitFullscreen();
            fsIcon.classList.remove('fa-compress');
            fsIcon.classList.add('fa-expand');
        }
    }
}

// Обновление данных текущей страницы
function refreshCurrentPageData() {
    const refreshIcon = document.querySelector('#refresh-data i');
    
    // Анимация вращения
    refreshIcon.classList.add('fa-spin');
    
    // Загрузка данных текущей страницы
    loadPageData(currentPage);
    
    // Отображаем уведомление
    showNotification('Данные успешно обновлены', 'success');
    
    // Останавливаем анимацию через 1 секунду
    setTimeout(() => {
        refreshIcon.classList.remove('fa-spin');
    }, 1000);
}

// Отображение уведомления
function showNotification(message, type = 'info') {
    const container = document.getElementById('notifications-container');
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    const icon = document.createElement('i');
    icon.className = 'fas';
    
    switch(type) {
        case 'success':
            icon.classList.add('fa-check-circle');
            break;
        case 'error':
            icon.classList.add('fa-exclamation-triangle');
            break;
        case 'warning':
            icon.classList.add('fa-exclamation-circle');
            break;
        default:
            icon.classList.add('fa-info-circle');
    }
    
    const content = document.createElement('div');
    content.className = 'notification-content';
    content.textContent = message;
    
    const closeBtn = document.createElement('button');
    closeBtn.className = 'notification-close';
    closeBtn.innerHTML = '&times;';
    closeBtn.addEventListener('click', function() {
        notification.classList.add('closing');
        setTimeout(() => {
            notification.remove();
        }, 300);
    });
    
    notification.appendChild(icon);
    notification.appendChild(content);
    notification.appendChild(closeBtn);
    
    container.appendChild(notification);
    
    // Автоматическое скрытие через 5 секунд
    setTimeout(() => {
        if (notification.parentNode) {
            notification.classList.add('closing');
            setTimeout(() => {
                notification.remove();
            }, 300);
        }
    }, 5000);
}

// Загрузка данных для страницы обзора
function loadDashboardData() {
    // Загружаем статистику системы
    fetch('/api/admin/stats')
        .then(response => response.json())
        .then(data => {
            updateDashboardCounters(data);
            updateSystemInfo(data);
            loadRecentActivities();
            updateActivityChart();
        })
        .catch(error => {
            console.error('Ошибка при загрузке статистики:', error);
            showNotification('Ошибка при загрузке статистики', 'error');
        });
}

// Обновление счетчиков на странице обзора
function updateDashboardCounters(data) {
    // Обновляем счетчики и их изменения
    document.getElementById('user-count').textContent = data.user_count || 0;
    document.getElementById('user-change').textContent = data.user_growth ? `+${data.user_growth}%` : '+0%';
    
    document.getElementById('message-count').textContent = data.message_count || 0;
    document.getElementById('message-change').textContent = data.message_growth ? `+${data.message_growth}%` : '+0%';
    
    document.getElementById('events-count').textContent = data.events_count || 0;
    document.getElementById('events-change').textContent = data.events_growth ? `+${data.events_growth}%` : '+0%';
    
    document.getElementById('uptime').textContent = data.uptime || '00:00:00';
    
    // Обновляем статистику запросов
    const queriesStats = document.getElementById('queries-stats');
    if (queriesStats && data.queries) {
        queriesStats.innerHTML = `
            <div class="stat-item">
                <div class="stat-label">Запросов сегодня</div>
                <div class="stat-value">${data.queries.today || 0}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Запросов всего</div>
                <div class="stat-value">${data.queries.total || 0}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Запросов в минуту</div>
                <div class="stat-value">${data.queries.per_minute || 0}</div>
            </div>
            <div class="stat-item">
                <div class="stat-label">Среднее время ответа</div>
                <div class="stat-value">${data.queries.avg_response_time || 0} мс</div>
            </div>
        `;
    }
}

// Обновление системной информации
function updateSystemInfo(data) {
    systemInfo = data.system || {
        version: '1.2.0',
        api_status: 'Активна',
        cache_size: '250 МБ',
        last_update: '2 часа назад'
    };
    
    const sysInfoEl = document.getElementById('system-info');
    if (sysInfoEl) {
        sysInfoEl.innerHTML = `
            <div class="info-item">
                <div class="info-label">Версия бота</div>
                <div class="info-value">${systemInfo.version}</div>
            </div>
            <div class="info-item">
                <div class="info-label">API запросы</div>
                <div class="info-value">${systemInfo.api_status}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Кэш</div>
                <div class="info-value">${systemInfo.cache_size}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Обновлено</div>
                <div class="info-value">${systemInfo.last_update}</div>
            </div>
        `;
    }
}

// Загрузка последних действий
function loadRecentActivities() {
    // Симуляция данных для примера
    const activities = [
        {
            id: 1,
            user_id: 7225056628,
            user_name: 'Администратор',
            action: 'login',
            details: 'Вход в систему',
            timestamp: '2023-03-09 15:30'
        },
        {
            id: 2,
            user_id: 7225056628,
            user_name: 'Администратор',
            action: 'edit_settings',
            details: 'Изменение настроек системы',
            timestamp: '2023-03-09 15:35'
        },
        {
            id: 3,
            user_id: 7225056628,
            user_name: 'Администратор',
            action: 'clear_cache',
            details: 'Очистка кэша системы',
            timestamp: '2023-03-09 15:40'
        }
    ];
    
    const activitiesList = document.getElementById('recent-activities');
    if (activitiesList) {
        activitiesList.innerHTML = '';
        
        activities.forEach(activity => {
            const actionIcons = {
                'login': 'fa-sign-in-alt',
                'logout': 'fa-sign-out-alt',
                'edit_settings': 'fa-cog',
                'clear_cache': 'fa-broom',
                'add_admin': 'fa-user-plus',
                'remove_admin': 'fa-user-minus'
            };
            
            const icon = actionIcons[activity.action] || 'fa-history';
            
            const li = document.createElement('li');
            li.className = 'activity-item';
            li.innerHTML = `
                <div class="activity-icon">
                    <i class="fas ${icon}"></i>
                </div>
                <div class="activity-details">
                    <div class="activity-header">
                        <span class="activity-user">${activity.user_name}</span>
                        <span class="activity-time">${activity.timestamp}</span>
                    </div>
                    <div class="activity-description">${activity.details}</div>
                </div>
            `;
            
            activitiesList.appendChild(li);
        });
    }
}

// Обновление графика активности
function updateActivityChart() {
    const period = document.getElementById('activity-period').value;
    const chartImg = document.getElementById('activity-chart');
    
    if (chartImg) {
        // В реальном проекте здесь был бы запрос к API
        // Для примера просто меняем параметр URL для имитации обновления
        chartImg.src = `/api/chart/daily_activity?period=${period}&_t=${Date.now()}`;
    }
}

// Просмотр всех активностей
function viewAllActivities() {
    // Открываем модальное окно со всеми активностями
    const modalContent = `
        <div class="modal-header">
            <h2>История действий</h2>
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <div class="activities-filter">
                <div class="filter-group">
                    <label for="activity-date-filter">Период:</label>
                    <select id="activity-date-filter">
                        <option value="today">Сегодня</option>
                        <option value="week" selected>За неделю</option>
                        <option value="month">За месяц</option>
                        <option value="all">Все время</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label for="activity-user-filter">Пользователь:</label>
                    <select id="activity-user-filter">
                        <option value="all">Все пользователи</option>
                        <option value="7225056628">Администратор</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label for="activity-type-filter">Тип действия:</label>
                    <select id="activity-type-filter">
                        <option value="all">Все действия</option>
                        <option value="login">Вход в систему</option>
                        <option value="edit_settings">Изменение настроек</option>
                        <option value="clear_cache">Очистка кэша</option>
                    </select>
                </div>
                <button class="btn btn-primary" id="filter-activities-btn">
                    <i class="fas fa-filter"></i> Применить
                </button>
            </div>
            
            <div class="activities-list-container">
                <ul class="activities-list">
                    <li class="activity-item">
                        <div class="activity-icon">
                            <i class="fas fa-sign-in-alt"></i>
                        </div>
                        <div class="activity-details">
                            <div class="activity-header">
                                <span class="activity-user">Администратор</span>
                                <span class="activity-time">2023-03-09 15:30</span>
                            </div>
                            <div class="activity-description">Вход в систему</div>
                        </div>
                    </li>
                    <li class="activity-item">
                        <div class="activity-icon">
                            <i class="fas fa-cog"></i>
                        </div>
                        <div class="activity-details">
                            <div class="activity-header">
                                <span class="activity-user">Администратор</span>
                                <span class="activity-time">2023-03-09 15:35</span>
                            </div>
                            <div class="activity-description">Изменение настроек системы</div>
                        </div>
                    </li>
                    <li class="activity-item">
                        <div class="activity-icon">
                            <i class="fas fa-broom"></i>
                        </div>
                        <div class="activity-details">
                            <div class="activity-header">
                                <span class="activity-user">Администратор</span>
                                <span class="activity-time">2023-03-09 15:40</span>
                            </div>
                            <div class="activity-description">Очистка кэша системы</div>
                        </div>
                    </li>
                    <li class="activity-item">
                        <div class="activity-icon">
                            <i class="fas fa-user-plus"></i>
                        </div>
                        <div class="activity-details">
                            <div class="activity-header">
                                <span class="activity-user">Администратор</span>
                                <span class="activity-time">2023-03-08 11:20</span>
                            </div>
                            <div class="activity-description">Добавление нового администратора</div>
                        </div>
                    </li>
                    <li class="activity-item">
                        <div class="activity-icon">
                            <i class="fas fa-sync-alt"></i>
                        </div>
                        <div class="activity-details">
                            <div class="activity-header">
                                <span class="activity-user">Администратор</span>
                                <span class="activity-time">2023-03-08 10:15</span>
                            </div>
                            <div class="activity-description">Обновление данных API</div>
                        </div>
                    </li>
                </ul>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-primary" onclick="exportActivities()">
                <i class="fas fa-download"></i> Экспорт
            </button>
            <button class="btn btn-secondary" onclick="closeModal()">
                <i class="fas fa-times"></i> Закрыть
            </button>
        </div>
    `;
    
    openModal(modalContent, 'large');
    
    // Привязываем обработчик к кнопке фильтрации
    document.getElementById('filter-activities-btn').addEventListener('click', function() {
        showNotification('Фильтры применены', 'success');
    });
}

// Функция проверки статуса системы
function checkSystemStatus() {
    showNotification('Выполняется проверка системы...', 'info');
    
    // Имитация проверки (в реальном проекте здесь был бы запрос)
    setTimeout(() => {
        // Показываем результаты проверки в модальном окне
        const modalContent = `
            <div class="modal-header">
                <h2>Результаты проверки системы</h2>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="system-check-results">
                    <div class="check-item success">
                        <div class="check-icon">
                            <i class="fas fa-check-circle"></i>
                        </div>
                        <div class="check-details">
                            <div class="check-name">API сервисы</div>
                            <div class="check-status">Работают нормально</div>
                        </div>
                    </div>
                    <div class="check-item success">
                        <div class="check-icon">
                            <i class="fas fa-check-circle"></i>
                        </div>
                        <div class="check-details">
                            <div class="check-name">База данных</div>
                            <div class="check-status">Работает нормально</div>
                        </div>
                    </div>
                    <div class="check-item warning">
                        <div class="check-icon">
                            <i class="fas fa-exclamation-circle"></i>
                        </div>
                        <div class="check-details">
                            <div class="check-name">Кэш</div>
                            <div class="check-status">Рекомендуется очистка</div>
                        </div>
                    </div>
                    <div class="check-item success">
                        <div class="check-icon">
                            <i class="fas fa-check-circle"></i>
                        </div>
                        <div class="check-details">
                            <div class="check-name">Дисковое пространство</div>
                            <div class="check-status">Достаточно (75% свободно)</div>
                        </div>
                    </div>
                    <div class="check-item success">
                        <div class="check-icon">
                            <i class="fas fa-check-circle"></i>
                        </div>
                        <div class="check-details">
                            <div class="check-name">Доступ к API ключам</div>
                            <div class="check-status">Успешно</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-primary" onclick="executeSystemFix()">
                    <i class="fas fa-wrench"></i> Исправить проблемы
                </button>
                <button class="btn btn-secondary" onclick="closeModal()">
                    <i class="fas fa-times"></i> Закрыть
                </button>
            </div>
        `;
        
        openModal(modalContent);
    }, 1500);
}

// Функция для исправления проблем системы
function executeSystemFix() {
    showNotification('Выполняется исправление проблем...', 'info');
    
    // Имитация исправления
    setTimeout(() => {
        showNotification('Проблемы успешно исправлены', 'success');
        closeModal();
    }, 1500);
}

// Экспорт истории активностей
function exportActivities() {
    showNotification('Выполняется экспорт активностей...', 'info');
    
    // Имитация экспорта
    setTimeout(() => {
        showNotification('Данные успешно экспортированы', 'success');
    }, 1000);
}

// Загрузка данных для страницы исторических событий
function loadEventsData() {
    // Загружаем категории для фильтров
    loadEventCategories();
    
    // Загружаем события для таблицы с учетом пагинации
    const page = eventsPagination.currentPage;
    const itemsPerPage = eventsPagination.itemsPerPage;
    
    // Запрос данных от API
    fetch(`/api/historical-events?page=${page}&limit=${itemsPerPage}`)
        .then(response => response.json())
        .then(data => {
            displayEventsData(data);
            
            // Обновляем пагинацию
            eventsPagination.totalPages = Math.ceil(data.length / itemsPerPage);
            updateEventsPagination();
        })
        .catch(error => {
            console.error('Ошибка при загрузке данных о событиях:', error);
            showNotification('Ошибка при загрузке данных о событиях', 'error');
        });
}

// Загрузка категорий событий
function loadEventCategories() {
    fetch('/api/categories')
        .then(response => response.json())
        .then(categories => {
            const categoryFilter = document.getElementById('event-category-filter');
            if (categoryFilter) {
                // Очищаем предыдущие опции, оставляя первую
                while (categoryFilter.options.length > 1) {
                    categoryFilter.remove(1);
                }
                
                // Добавляем новые опции
                categories.forEach(category => {
                    const option = document.createElement('option');
                    option.value = category;
                    option.textContent = category;
                    categoryFilter.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Ошибка при загрузке категорий:', error);
        });
    
    // Симуляция данных для века и региона
    const centuries = ['XVIII', 'XIX', 'XX', 'XXI'];
    const regions = ['Европейская часть', 'Сибирь', 'Дальний Восток', 'Кавказ', 'Средняя Азия'];
    
    const centuryFilter = document.getElementById('event-century-filter');
    if (centuryFilter) {
        // Очищаем предыдущие опции, оставляя первую
        while (centuryFilter.options.length > 1) {
            centuryFilter.remove(1);
        }
        
        // Добавляем новые опции
        centuries.forEach(century => {
            const option = document.createElement('option');
            option.value = century;
            option.textContent = century + ' век';
            centuryFilter.appendChild(option);
        });
    }
    
    const regionFilter = document.getElementById('event-location-filter');
    if (regionFilter) {
        // Очищаем предыдущие опции, оставляя первую
        while (regionFilter.options.length > 1) {
            regionFilter.remove(1);
        }
        
        // Добавляем новые опции
        regions.forEach(region => {
            const option = document.createElement('option');
            option.value = region;
            option.textContent = region;
            regionFilter.appendChild(option);
        });
    }
}

// Отображение данных о событиях в таблице
function displayEventsData(events) {
    const tbody = document.getElementById('events-table-body');
    if (!tbody) return;
    
    // Очищаем таблицу
    tbody.innerHTML = '';
    
    // Если нет данных, показываем сообщение
    if (!events || events.length === 0) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="6" class="no-data">Нет данных для отображения</td>';
        tbody.appendChild(tr);
        return;
    }
    
    // Отображаем данные о событиях
    const startIndex = (eventsPagination.currentPage - 1) * eventsPagination.itemsPerPage;
    const endIndex = Math.min(startIndex + eventsPagination.itemsPerPage, events.length);
    
    for (let i = 0; i < Math.min(eventsPagination.itemsPerPage, events.length); i++) {
        const event = events[i];
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${event.id || '-'}</td>
            <td>${event.title || '-'}</td>
            <td>${event.date || '-'}</td>
            <td>${event.category || '-'}</td>
            <td>${event.location && event.location.lat ? `${event.location.lat}, ${event.location.lng}` : '-'}</td>
            <td class="actions">
                <button class="btn-icon btn-view" data-id="${event.id}" title="Просмотр">
                    <i class="fas fa-eye"></i>
                </button>
                <button class="btn-icon btn-edit" data-id="${event.id}" title="Редактировать">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn-icon btn-delete" data-id="${event.id}" title="Удалить">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </td>
        `;
        
        tbody.appendChild(tr);
    }
    
    // Привязываем обработчики событий к кнопкам
    tbody.querySelectorAll('.btn-view').forEach(btn => {
        btn.addEventListener('click', function() {
            const eventId = this.getAttribute('data-id');
            viewEvent(eventId);
        });
    });
    
    tbody.querySelectorAll('.btn-edit').forEach(btn => {
        btn.addEventListener('click', function() {
            const eventId = this.getAttribute('data-id');
            editEvent(eventId);
        });
    });
    
    tbody.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', function() {
            const eventId = this.getAttribute('data-id');
            deleteEvent(eventId);
        });
    });
}

// Обновление пагинации для событий
function updateEventsPagination() {
    const paginationContainer = document.getElementById('events-pagination');
    if (!paginationContainer) return;
    
    // Очищаем контейнер
    paginationContainer.innerHTML = '';
    
    // Если нет страниц, не показываем пагинацию
    if (eventsPagination.totalPages <= 1) return;
    
    // Добавляем кнопку "Предыдущая"
    const prevBtn = document.createElement('button');
    prevBtn.className = 'pagination-item prev';
    prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
    prevBtn.disabled = eventsPagination.currentPage === 1;
    prevBtn.addEventListener('click', function() {
        if (eventsPagination.currentPage > 1) {
            eventsPagination.currentPage--;
            loadEventsData();
        }
    });
    paginationContainer.appendChild(prevBtn);
    
    // Добавляем кнопки с номерами страниц
    for (let i = 1; i <= eventsPagination.totalPages; i++) {
        // Показываем только текущую страницу, первую, последнюю и по одной странице до и после текущей
        if (
            i === 1 || 
            i === eventsPagination.totalPages || 
            i === eventsPagination.currentPage || 
            i === eventsPagination.currentPage - 1 || 
            i === eventsPagination.currentPage + 1
        ) {
            const pageBtn = document.createElement('button');
            pageBtn.className = `pagination-item ${i === eventsPagination.currentPage ? 'active' : ''}`;
            pageBtn.textContent = i;
            pageBtn.addEventListener('click', function() {
                eventsPagination.currentPage = i;
                loadEventsData();
            });
            paginationContainer.appendChild(pageBtn);
        } else if (
            (i === eventsPagination.currentPage - 2 && eventsPagination.currentPage > 3) || 
            (i === eventsPagination.currentPage + 2 && eventsPagination.currentPage < eventsPagination.totalPages - 2)
        ) {
            // Добавляем многоточие
            const dots = document.createElement('span');
            dots.className = 'pagination-dots';
            dots.textContent = '...';
            paginationContainer.appendChild(dots);
        }
    }
    
    // Добавляем кнопку "Следующая"
    const nextBtn = document.createElement('button');
    nextBtn.className = 'pagination-item next';
    nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
    nextBtn.disabled = eventsPagination.currentPage === eventsPagination.totalPages;
    nextBtn.addEventListener('click', function() {
        if (eventsPagination.currentPage < eventsPagination.totalPages) {
            eventsPagination.currentPage++;
            loadEventsData();
        }
    });
    paginationContainer.appendChild(nextBtn);
}

// Настройка обработчиков для таблицы событий
function setupEventsTableHandlers() {
    // Обработка изменения количества элементов на странице
    const eventsPerPage = document.getElementById('events-per-page');
    if (eventsPerPage) {
        eventsPerPage.addEventListener('change', function() {
            eventsPagination.itemsPerPage = parseInt(this.value);
            eventsPagination.currentPage = 1; // Сбрасываем на первую страницу
            loadEventsData();
        });
    }
    
    // Обработка кнопок фильтров
    const filterApply = document.getElementById('filter-apply');
    if (filterApply) {
        filterApply.addEventListener('click', function() {
            // Собираем данные фильтров
            const category = document.getElementById('event-category-filter').value;
            const century = document.getElementById('event-century-filter').value;
            const location = document.getElementById('event-location-filter').value;
            const search = document.getElementById('event-search').value;
            
            // Сбрасываем на первую страницу
            eventsPagination.currentPage = 1;
            
            // Применяем фильтры и загружаем данные
            loadEventsData();
            
            showNotification('Фильтры применены', 'success');
        });
    }
    
    const filterReset = document.getElementById('filter-reset');
    if (filterReset) {
        filterReset.addEventListener('click', function() {
            // Сбрасываем значения фильтров
            document.getElementById('event-category-filter').value = 'all';
            document.getElementById('event-century-filter').value = 'all';
            document.getElementById('event-location-filter').value = 'all';
            document.getElementById('event-search').value = '';
            
            // Сбрасываем на первую страницу
            eventsPagination.currentPage = 1;
            
            // Загружаем данные без фильтров
            loadEventsData();
            
            showNotification('Фильтры сброшены', 'success');
        });
    }
    
    // Обработка кнопки добавления нового события
    const addNewEvent = document.getElementById('add-new-event');
    if (addNewEvent) {
        addNewEvent.addEventListener('click', function() {
            showEventForm();
        });
    }
}

// Отображение формы события (создание/редактирование)
function showEventForm(eventId = null) {
    let event = null;
    let formTitle = 'Добавление нового события';
    
    // Если указан ID, то это редактирование
    if (eventId) {
        formTitle = 'Редактирование события';
        // Здесь можно было бы загрузить данные события по ID
        // Для примера используем заглушку
        event = {
            id: eventId,
            title: 'Пример события',
            date: '1800-01-01',
            category: 'Войны и сражения',
            location: { lat: 55.7558, lng: 37.6173 },
            description: 'Описание события'
        };
    }
    
    const modalContent = `
        <div class="modal-header">
            <h2>${formTitle}</h2>
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <form id="event-form">
                <input type="hidden" id="event-id" value="${event ? event.id : ''}">
                
                <div class="form-group">
                    <label for="event-title">Название события</label>
                    <input type="text" id="event-title" class="form-control" value="${event ? event.title : ''}" required>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="event-date">Дата</label>
                        <input type="text" id="event-date" class="form-control" value="${event ? event.date : ''}" placeholder="ГГГГ-ММ-ДД" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="event-category">Категория</label>
                        <select id="event-category" class="form-control" required>
                            <option value="">Выберите категорию</option>
                            <option value="Войны и сражения" ${event && event.category === 'Войны и сражения' ? 'selected' : ''}>Войны и сражения</option>
                            <option value="Революции и перевороты" ${event && event.category === 'Революции и перевороты' ? 'selected' : ''}>Революции и перевороты</option>
                            <option value="Политические реформы" ${event && event.category === 'Политические реформы' ? 'selected' : ''}>Политические реформы</option>
                            <option value="Культура и религия" ${event && event.category === 'Культура и религия' ? 'selected' : ''}>Культура и религия</option>
                        </select>
                    </div>
                </div>
                
                <div class="form-row">
                    <div class="form-group">
                        <label for="event-lat">Широта</label>
                        <input type="number" id="event-lat" class="form-control" value="${event && event.location ? event.location.lat : ''}" step="0.0001" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="event-lng">Долгота</label>
                        <input type="number" id="event-lng" class="form-control" value="${event && event.location ? event.location.lng : ''}" step="0.0001" required>
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="event-description">Описание</label>
                    <textarea id="event-description" class="form-control" rows="5" required>${event ? event.description : ''}</textarea>
                </div>
            </form>
        </div>
        <div class="modal-footer">
            <button class="btn btn-primary" onclick="saveEvent()">
                <i class="fas fa-save"></i> Сохранить
            </button>
            <button class="btn btn-secondary" onclick="closeModal()">
                <i class="fas fa-times"></i> Отмена
            </button>
        </div>
    `;
    
    openModal(modalContent);
}

// Функция сохранения события
function saveEvent() {
    const eventId = document.getElementById('event-id').value;
    const isNew = !eventId;
    
    // Собираем данные формы
    const eventData = {
        id: eventId || Date.now().toString(), // Генерируем ID для новых событий
        title: document.getElementById('event-title').value,
        date: document.getElementById('event-date').value,
        category: document.getElementById('event-category').value,
        location: {
            lat: parseFloat(document.getElementById('event-lat').value),
            lng: parseFloat(document.getElementById('event-lng').value)
        },
        description: document.getElementById('event-description').value
    };
    
    // Проверка обязательных полей
    if (!eventData.title || !eventData.date || !eventData.category || !eventData.location.lat || !eventData.location.lng || !eventData.description) {
        showNotification('Пожалуйста, заполните все обязательные поля', 'warning');
        return;
    }
    
    // В реальном приложении здесь будет отправка данных на сервер
    // Для примера просто показываем уведомление
    
    if (isNew) {
        showNotification('Событие успешно добавлено', 'success');
    } else {
        showNotification('Событие успешно обновлено', 'success');
    }
    
    // Закрываем модальное окно и обновляем данные
    closeModal();
    loadEventsData();
}

// Функция просмотра события
function viewEvent(eventId) {
    // Здесь можно было бы загрузить данные события по ID
    // Для примера используем заглушку
    const event = {
        id: eventId,
        title: 'Пример события',
        date: '1800-01-01',
        category: 'Войны и сражения',
        location: { lat: 55.7558, lng: 37.6173 },
        description: 'Подробное описание исторического события, содержащее важную информацию о ходе событий, их причинах и последствиях для истории России.'
    };
    
    const modalContent = `
        <div class="modal-header">
            <h2>${event.title}</h2>
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <div class="event-details">
                <div class="detail-row">
                    <div class="detail-label">ID:</div>
                    <div class="detail-value">${event.id}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Дата:</div>
                    <div class="detail-value">${event.date}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Категория:</div>
                    <div class="detail-value">${event.category}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Координаты:</div>
                    <div class="detail-value">${event.location.lat}, ${event.location.lng}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Описание:</div>
                    <div class="detail-value">${event.description}</div>
                </div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-primary" onclick="editEvent('${event.id}')">
                <i class="fas fa-edit"></i> Редактировать
            </button>
            <button class="btn btn-secondary" onclick="closeModal()">
                <i class="fas fa-times"></i> Закрыть
            </button>
        </div>
    `;
    
    openModal(modalContent);
}

// Функция редактирования события
function editEvent(eventId) {
    closeModal(); // Закрываем предыдущее модальное окно, если открыто
    showEventForm(eventId);
}

// Функция удаления события
function deleteEvent(eventId) {
    const modalContent = `
        <div class="modal-header">
            <h2>Подтверждение удаления</h2>
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <p>Вы действительно хотите удалить событие с ID ${eventId}?</p>
            <p class="warning-text">Это действие невозможно отменить!</p>
        </div>
        <div class="modal-footer">
            <button class="btn btn-danger" onclick="confirmDeleteEvent('${eventId}')">
                <i class="fas fa-trash-alt"></i> Удалить
            </button>
            <button class="btn btn-secondary" onclick="closeModal()">
                <i class="fas fa-times"></i> Отмена
            </button>
        </div>
    `;
    
    openModal(modalContent, 'small');
}

// Функция подтверждения удаления события
function confirmDeleteEvent(eventId) {
    // В реальном приложении здесь будет отправка запроса на удаление
    // Для примера просто показываем уведомление
    
    showNotification(`Событие с ID ${eventId} успешно удалено`, 'success');
    
    // Закрываем модальное окно и обновляем данные
    closeModal();
    loadEventsData();
}

// Загрузка данных о пользователях
function loadUsersData() {
    // Запрос данных от API
    fetch(`/api/admin/users?page=${usersPagination.currentPage}&limit=${usersPagination.itemsPerPage}`)
        .then(response => response.json())
        .then(users => {
            displayUsersData(users);
            
            // Обновляем пагинацию
            usersPagination.totalPages = Math.ceil(users.length / usersPagination.itemsPerPage);
            updateUsersPagination();
        })
        .catch(error => {
            console.error('Ошибка при загрузке данных о пользователях:', error);
            showNotification('Ошибка при загрузке данных о пользователях', 'error');
        });
}

// Отображение данных о пользователях
function displayUsersData(users) {
    const tbody = document.getElementById('users-table-body');
    if (!tbody) return;
    
    // Очищаем таблицу
    tbody.innerHTML = '';
    
    // Если нет данных, показываем сообщение
    if (!users || users.length === 0) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="6" class="no-data">Нет данных для отображения</td>';
        tbody.appendChild(tr);
        return;
    }
    
    // Отображаем данные о пользователях
    users.forEach(user => {
        const tr = document.createElement('tr');
        
        // Определяем класс строки в зависимости от статуса
        if (user.status === 'blocked') {
            tr.classList.add('blocked-row');
        }
        
        // Добавляем статус как класс для стилизации
        tr.classList.add(`status-${user.status}`);
        
        tr.innerHTML = `
            <td>${user.id || '-'}</td>
            <td>${user.name || '-'}</td>
            <td>
                <span class="status-badge ${user.status}">${getStatusText(user.status)}</span>
            </td>
            <td>${user.last_activity || '-'}</td>
            <td>${user.messages || 0}</td>
            <td class="actions">
                <button class="btn-icon btn-view" data-id="${user.id}" title="Просмотр">
                    <i class="fas fa-eye"></i>
                </button>
                ${user.status === 'blocked' ? 
                    `<button class="btn-icon btn-unblock" data-id="${user.id}" title="Разблокировать">
                        <i class="fas fa-unlock"></i>
                    </button>` : 
                    `<button class="btn-icon btn-block" data-id="${user.id}" title="Заблокировать">
                        <i class="fas fa-ban"></i>
                    </button>`
                }
                <button class="btn-icon btn-message" data-id="${user.id}" title="Отправить сообщение">
                    <i class="fas fa-envelope"></i>
                </button>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
    
    // Привязываем обработчики событий к кнопкам
    tbody.querySelectorAll('.btn-view').forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.getAttribute('data-id');
            viewUser(userId);
        });
    });
    
    tbody.querySelectorAll('.btn-block').forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.getAttribute('data-id');
            blockUser(userId);
        });
    });
    
    tbody.querySelectorAll('.btn-unblock').forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.getAttribute('data-id');
            unblockUser(userId);
        });
    });
    
    tbody.querySelectorAll('.btn-message').forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.getAttribute('data-id');
            messageUser(userId);
        });
    });
}

// Получение текстового представления статуса
function getStatusText(status) {
    const statusTexts = {
        'active': 'Активен',
        'inactive': 'Неактивен',
        'blocked': 'Заблокирован'
    };
    
    return statusTexts[status] || status;
}

// Обновление пагинации для пользователей
function updateUsersPagination() {
    const paginationContainer = document.getElementById('users-pagination');
    if (!paginationContainer) return;
    
    // Очищаем контейнер
    paginationContainer.innerHTML = '';
    
    // Если нет страниц, не показываем пагинацию
    if (usersPagination.totalPages <= 1) return;
    
    // Добавляем кнопку "Предыдущая"
    const prevBtn = document.createElement('button');
    prevBtn.className = 'pagination-item prev';
    prevBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
    prevBtn.disabled = usersPagination.currentPage === 1;
    prevBtn.addEventListener('click', function() {
        if (usersPagination.currentPage > 1) {
            usersPagination.currentPage--;
            loadUsersData();
        }
    });
    paginationContainer.appendChild(prevBtn);
    
    // Добавляем кнопки с номерами страниц
    for (let i = 1; i <= usersPagination.totalPages; i++) {
        // Показываем только текущую страницу, первую, последнюю и по одной странице до и после текущей
        if (
            i === 1 || 
            i === usersPagination.totalPages || 
            i === usersPagination.currentPage || 
            i === usersPagination.currentPage - 1 || 
            i === usersPagination.currentPage + 1
        ) {
            const pageBtn = document.createElement('button');
            pageBtn.className = `pagination-item ${i === usersPagination.currentPage ? 'active' : ''}`;
            pageBtn.textContent = i;
            pageBtn.addEventListener('click', function() {
                usersPagination.currentPage = i;
                loadUsersData();
            });
            paginationContainer.appendChild(pageBtn);
        } else if (
            (i === usersPagination.currentPage - 2 && usersPagination.currentPage > 3) || 
            (i === usersPagination.currentPage + 2 && usersPagination.currentPage < usersPagination.totalPages - 2)
        ) {
            // Добавляем многоточие
            const dots = document.createElement('span');
            dots.className = 'pagination-dots';
            dots.textContent = '...';
            paginationContainer.appendChild(dots);
        }
    }
    
    // Добавляем кнопку "Следующая"
    const nextBtn = document.createElement('button');
    nextBtn.className = 'pagination-item next';
    nextBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
    nextBtn.disabled = usersPagination.currentPage === usersPagination.totalPages;
    nextBtn.addEventListener('click', function() {
        if (usersPagination.currentPage < usersPagination.totalPages) {
            usersPagination.currentPage++;
            loadUsersData();
        }
    });
    paginationContainer.appendChild(nextBtn);
}

// Настройка обработчиков для таблицы пользователей
function setupUsersTableHandlers() {
    // Обработка изменения количества элементов на странице
    const usersPerPage = document.getElementById('users-per-page');
    if (usersPerPage) {
        usersPerPage.addEventListener('change', function() {
            usersPagination.itemsPerPage = parseInt(this.value);
            usersPagination.currentPage = 1; // Сбрасываем на первую страницу
            loadUsersData();
        });
    }
    
    // Обработка кнопок фильтров
    const filterApply = document.getElementById('users-filter-apply');
    if (filterApply) {
        filterApply.addEventListener('click', function() {
            // Собираем данные фильтров
            const status = document.getElementById('user-status-filter').value;
            const activity = document.getElementById('user-activity-filter').value;
            const search = document.getElementById('user-search').value;
            
            // Сбрасываем на первую страницу
            usersPagination.currentPage = 1;
            
            // Применяем фильтры и загружаем данные
            loadUsersData();
            
            showNotification('Фильтры применены', 'success');
        });
    }
    
    const filterReset = document.getElementById('users-filter-reset');
    if (filterReset) {
        filterReset.addEventListener('click', function() {
            // Сбрасываем значения фильтров
            document.getElementById('user-status-filter').value = 'all';
            document.getElementById('user-activity-filter').value = 'all';
            document.getElementById('user-search').value = '';
            
            // Сбрасываем на первую страницу
            usersPagination.currentPage = 1;
            
            // Загружаем данные без фильтров
            loadUsersData();
            
            showNotification('Фильтры сброшены', 'success');
        });
    }
    
    // Обработка кнопки экспорта
    const exportUsers = document.getElementById('export-users');
    if (exportUsers) {
        exportUsers.addEventListener('click', function() {
            exportUsersData();
        });
    }
}

// Функция экспорта данных о пользователях
function exportUsersData() {
    showNotification('Выполняется экспорт данных о пользователях...', 'info');
    
    // Имитация экспорта
    setTimeout(() => {
        showNotification('Данные успешно экспортированы', 'success');
    }, 1000);
}

// Функция просмотра пользователя
function viewUser(userId) {
    // Запрос данных о пользователе
    fetch(`/api/admin/user/${userId}`)
        .then(response => response.json())
        .then(user => {
            const modalContent = `
                <div class="modal-header">
                    <h2>Пользователь: ${user.name || 'Без имени'}</h2>
                    <button class="modal-close" onclick="closeModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="user-details">
                        <div class="detail-row">
                            <div class="detail-label">ID:</div>
                            <div class="detail-value">${user.id}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Имя:</div>
                            <div class="detail-value">${user.name || 'Не указано'}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Статус:</div>
                            <div class="detail-value">
                                <span class="status-badge ${user.status}">${getStatusText(user.status)}</span>
                            </div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Последняя активность:</div>
                            <div class="detail-value">${user.last_activity || 'Неизвестно'}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Сообщений:</div>
                            <div class="detail-value">${user.messages || 0}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Дата регистрации:</div>
                            <div class="detail-value">${user.registration_date || 'Неизвестно'}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Пройдено тестов:</div>
                            <div class="detail-value">${user.tests_completed || 0}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Избранные темы:</div>
                            <div class="detail-value">
                                ${user.favorite_topics && user.favorite_topics.length > 0 ? 
                                    user.favorite_topics.map(topic => `<span class="tag">${topic}</span>`).join(' ') : 
                                    'Нет избранных тем'
                                }
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    ${user.status === 'blocked' ? 
                        `<button class="btn btn-success" onclick="unblockUser(${user.id})">
                            <i class="fas fa-unlock"></i> Разблокировать
                        </button>` : 
                        `<button class="btn btn-warning" onclick="blockUser(${user.id})">
                            <i class="fas fa-ban"></i> Заблокировать
                        </button>`
                    }
                    <button class="btn btn-primary" onclick="messageUser(${user.id})">
                        <i class="fas fa-envelope"></i> Отправить сообщение
                    </button>
                    <button class="btn btn-secondary" onclick="closeModal()">
                        <i class="fas fa-times"></i> Закрыть
                    </button>
                </div>
            `;
            
            openModal(modalContent);
        })
        .catch(error => {
            console.error('Ошибка при загрузке данных о пользователе:', error);
            showNotification('Ошибка при загрузке данных о пользователе', 'error');
        });
}

// Функция блокировки пользователя
function blockUser(userId) {
    const modalContent = `
        <div class="modal-header">
            <h2>Блокировка пользователя</h2>
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <p>Вы действительно хотите заблокировать пользователя с ID ${userId}?</p>
            <div class="form-group">
                <label for="block-reason">Причина блокировки:</label>
                <select id="block-reason" class="form-control">
                    <option value="spam">Спам</option>
                    <option value="abuse">Оскорбления</option>
                    <option value="fraud">Мошенничество</option>
                    <option value="other">Другое</option>
                </select>
            </div>
            <div class="form-group" id="other-reason-container" style="display: none;">
                <label for="other-reason">Укажите причину:</label>
                <textarea id="other-reason" class="form-control" rows="2"></textarea>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-danger" onclick="confirmBlockUser(${userId})">
                <i class="fas fa-ban"></i> Заблокировать
            </button>
            <button class="btn btn-secondary" onclick="closeModal()">
                <i class="fas fa-times"></i> Отмена
            </button>
        </div>
    `;
    
    openModal(modalContent, 'small');
    
    // Отображение поля для ввода другой причины
    document.getElementById('block-reason').addEventListener('change', function() {
        const otherReasonContainer = document.getElementById('other-reason-container');
        if (this.value === 'other') {
            otherReasonContainer.style.display = 'block';
        } else {
            otherReasonContainer.style.display = 'none';
        }
    });
}

// Функция подтверждения блокировки пользователя
function confirmBlockUser(userId) {
    const blockReason = document.getElementById('block-reason').value;
    let reason = blockReason;
    
    if (blockReason === 'other') {
        const otherReason = document.getElementById('other-reason').value;
        if (!otherReason) {
            showNotification('Укажите причину блокировки', 'warning');
            return;
        }
        reason = otherReason;
    }
    
    // В реальном приложении здесь будет отправка запроса на блокировку
    fetch(`/api/admin/user/${userId}/block`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ reason: reason })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Пользователь с ID ${userId} заблокирован`, 'success');
            // Закрываем модальное окно и обновляем данные
            closeModal();
            loadUsersData();
        } else {
            showNotification(`Ошибка при блокировке пользователя: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        console.error('Ошибка при блокировке пользователя:', error);
        showNotification('Ошибка при блокировке пользователя', 'error');
    });
}

// Функция разблокировки пользователя
function unblockUser(userId) {
    const modalContent = `
        <div class="modal-header">
            <h2>Разблокировка пользователя</h2>
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <p>Вы действительно хотите разблокировать пользователя с ID ${userId}?</p>
        </div>
        <div class="modal-footer">
            <button class="btn btn-success" onclick="confirmUnblockUser(${userId})">
                <i class="fas fa-unlock"></i> Разблокировать
            </button>
            <button class="btn btn-secondary" onclick="closeModal()">
                <i class="fas fa-times"></i> Отмена
            </button>
        </div>
    `;
    
    openModal(modalContent, 'small');
}

// Функция подтверждения разблокировки пользователя
function confirmUnblockUser(userId) {
    // В реальном приложении здесь будет отправка запроса на разблокировку
    fetch(`/api/admin/user/${userId}/unblock`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`Пользователь с ID ${userId} разблокирован`, 'success');
            // Закрываем модальное окно и обновляем данные
            closeModal();
            loadUsersData();
        } else {
            showNotification(`Ошибка при разблокировке пользователя: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        console.error('Ошибка при разблокировке пользователя:', error);
        showNotification('Ошибка при разблокировке пользователя', 'error');
    });
}

// Функция отправки сообщения пользователю
function messageUser(userId) {
    const modalContent = `
        <div class="modal-header">
            <h2>Отправка сообщения пользователю</h2>
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <p>Отправка сообщения пользователю с ID ${userId}</p>
            
            <div class="form-group">
                <label for="message-subject">Тема сообщения:</label>
                <input type="text" id="message-subject" class="form-control" placeholder="Введите тему сообщения">
            </div>
            
            <div class="form-group">
                <label for="message-text">Текст сообщения:</label>
                <textarea id="message-text" class="form-control" rows="5" placeholder="Введите текст сообщения"></textarea>
            </div>
            
            <div class="form-check">
                <input type="checkbox" id="message-important" class="form-check-input">
                <label for="message-important" class="form-check-label">Пометить как важное</label>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-primary" onclick="sendUserMessage(${userId})">
                <i class="fas fa-paper-plane"></i> Отправить
            </button>
            <button class="btn btn-secondary" onclick="closeModal()">
                <i class="fas fa-times"></i> Отмена
            </button>
        </div>
    `;
    
    openModal(modalContent);
}

// Функция отправки сообщения пользователю
function sendUserMessage(userId) {
    const subject = document.getElementById('message-subject').value;
    const text = document.getElementById('message-text').value;
    const isImportant = document.getElementById('message-important').checked;
    
    // Проверка обязательных полей
    if (!subject || !text) {
        showNotification('Заполните тему и текст сообщения', 'warning');
        return;
    }
    
    // В реальном приложении здесь будет отправка запроса
    // Для примера просто показываем уведомление
    
    showNotification(`Сообщение пользователю ${userId} отправлено`, 'success');
    
    // Закрываем модальное окно
    closeModal();
}

// Загрузка данных для страницы администраторов
function loadAdminsData() {
    // Запрос данных от API
    fetch('/api/admin/admins')
        .then(response => response.json())
        .then(data => {
            displayAdminsData(data);
        })
        .catch(error => {
            console.error('Ошибка при загрузке данных об администраторах:', error);
            showNotification('Ошибка при загрузке данных об администраторах', 'error');
        });
}

// Отображение данных об администраторах
function displayAdminsData(admins) {
    const superAdminList = document.getElementById('super-admin-list');
    const adminList = document.getElementById('admin-list');
    const adminToRemoveSelect = document.getElementById('admin-to-remove');
    
    // Обновляем список супер-администраторов
    if (superAdminList) {
        superAdminList.innerHTML = '';
        
        if (admins.super_admin_ids && admins.super_admin_ids.length > 0) {
            admins.super_admin_ids.forEach(adminId => {
                const li = document.createElement('li');
                li.className = 'admin-item';
                li.innerHTML = `
                    <div class="admin-icon super">
                        <i class="fas fa-user-shield"></i>
                    </div>
                    <div class="admin-details">
                        <div class="admin-id">${adminId}</div>
                        <div class="admin-type">Супер-администратор</div>
                    </div>
                `;
                superAdminList.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.className = 'admin-item no-data';
            li.innerHTML = 'Нет супер-администраторов';
            superAdminList.appendChild(li);
        }
    }
    
    // Обновляем список обычных администраторов
    if (adminList) {
        adminList.innerHTML = '';
        
        if (admins.admin_ids && admins.admin_ids.length > 0) {
            admins.admin_ids.forEach(adminId => {
                const li = document.createElement('li');
                li.className = 'admin-item';
                li.innerHTML = `
                    <div class="admin-icon">
                        <i class="fas fa-user-tie"></i>
                    </div>
                    <div class="admin-details">
                        <div class="admin-id">${adminId}</div>
                        <div class="admin-type">Администратор</div>
                    </div>
                `;
                adminList.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.className = 'admin-item no-data';
            li.innerHTML = 'Нет администраторов';
            adminList.appendChild(li);
        }
    }
    
    // Обновляем список администраторов для удаления
    if (adminToRemoveSelect) {
        // Очищаем предыдущие опции, оставляя первую
        while (adminToRemoveSelect.options.length > 1) {
            adminToRemoveSelect.remove(1);
        }
        
        // Добавляем супер-администраторов
        if (admins.super_admin_ids && admins.super_admin_ids.length > 0) {
            const currentUserId = currentUser.id;
            
            admins.super_admin_ids.forEach(adminId => {
                // Не добавляем текущего пользователя в список для удаления
                if (adminId !== currentUserId) {
                    const option = document.createElement('option');
                    option.value = adminId;
                    option.textContent = `Супер-администратор: ${adminId}`;
                    adminToRemoveSelect.appendChild(option);
                }
            });
        }
        
        // Добавляем обычных администраторов
        if (admins.admin_ids && admins.admin_ids.length > 0) {
            admins.admin_ids.forEach(adminId => {
                const option = document.createElement('option');
                option.value = adminId;
                option.textContent = `Администратор: ${adminId}`;
                adminToRemoveSelect.appendChild(option);
            });
        }
    }
    
    // Проверяем, нужно ли показывать блок управления администраторами
    const adminManagement = document.querySelector('.admin-management');
    if (adminManagement) {
        if (currentUser && currentUser.is_super_admin) {
            adminManagement.style.display = 'flex';
        } else {
            adminManagement.style.display = 'none';
        }
    }
}

// Обработчик отправки формы добавления администратора
function handleAddAdminSubmit(e) {
    e.preventDefault();
    
    const adminId = document.getElementById('new-admin-id').value;
    const isSuper = document.getElementById('is-super-admin').checked;
    
    // Проверка ID администратора
    if (!adminId) {
        showNotification('Укажите ID пользователя', 'warning');
        return;
    }
    
    // Отправка запроса на добавление администратора
    fetch('/api/admin/admins', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            user_id: parseInt(adminId),
            is_super: isSuper
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`${isSuper ? 'Супер-администратор' : 'Администратор'} успешно добавлен`, 'success');
            // Сбрасываем форму
            document.getElementById('add-admin-form').reset();
            // Обновляем данные
            loadAdminsData();
        } else {
            showNotification(`Ошибка при добавлении администратора: ${data.message || 'Неизвестная ошибка'}`, 'error');
        }
    })
    .catch(error => {
        console.error('Ошибка при добавлении администратора:', error);
        showNotification('Ошибка при добавлении администратора', 'error');
    });
}

// Обработчик отправки формы удаления администратора
function handleRemoveAdminSubmit(e) {
    e.preventDefault();
    
    const adminId = document.getElementById('admin-to-remove').value;
    
    // Проверка ID администратора
    if (!adminId) {
        showNotification('Выберите администратора для удаления', 'warning');
        return;
    }
    
    // Отправка запроса на удаление администратора
    fetch(`/api/admin/admins/${adminId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Администратор успешно удален', 'success');
            // Сбрасываем форму
            document.getElementById('remove-admin-form').reset();
            // Обновляем данные
            loadAdminsData();
        } else {
            showNotification(`Ошибка при удалении администратора: ${data.message || 'Неизвестная ошибка'}`, 'error');
        }
    })
    .catch(error => {
        console.error('Ошибка при удалении администратора:', error);
        showNotification('Ошибка при удалении администратора', 'error');
    });
}

// Загрузка данных для страницы логов
function loadLogsData() {
    // Получаем параметры из элементов фильтрации
    const level = document.getElementById('log-level').value;
    const component = document.getElementById('log-component').value;
    const limit = document.getElementById('log-limit').value;
    
    // Формируем URL с параметрами
    const url = `/api/admin/logs?level=${level}&component=${component}&limit=${limit}`;
    
    // Запрос данных от API
    fetch(url)
        .then(response => response.json())
        .then(logs => {
            displayLogsData(logs);
            
            // Обновляем статистику логов
            document.getElementById('log-stats').textContent = `Загружено строк: ${logs.length}`;
        })
        .catch(error => {
            console.error('Ошибка при загрузке логов:', error);
            showNotification('Ошибка при загрузке логов', 'error');
        });
}

// Отображение данных логов
function displayLogsData(logs) {
    const logsContainer = document.getElementById('logs-container');
    if (!logsContainer) return;
    
    // Очищаем контейнер
    logsContainer.innerHTML = '';
    
    // Если нет данных, показываем сообщение
    if (!logs || logs.length === 0) {
        logsContainer.textContent = 'Логи отсутствуют';
        return;
    }
    
    // Отображаем логи с цветовой подсветкой
    let logsHtml = '';
    
    logs.forEach(log => {
        let logClass = '';
        
        // Определяем класс на основе уровня логирования
        if (log.includes(' - ERROR - ') || log.includes(' - CRITICAL - ')) {
            logClass = 'log-error';
        } else if (log.includes(' - WARNING - ')) {
            logClass = 'log-warning';
        } else if (log.includes(' - INFO - ')) {
            logClass = 'log-info';
        } else if (log.includes(' - DEBUG - ')) {
            logClass = 'log-debug';
        }
        
        logsHtml += `<div class="log-line ${logClass}">${escapeHtml(log)}</div>`;
    });
    
    logsContainer.innerHTML = logsHtml;
    
    // Если включена автопрокрутка, прокручиваем до конца
    if (document.getElementById('auto-scroll').classList.contains('active')) {
        logsContainer.scrollTop = logsContainer.scrollHeight;
    }
}

// Экранирование HTML
function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Настройка обработчиков для панели логов
function setupLogsHandlers() {
    // Обработчик кнопки обновления логов
    const refreshLogs = document.getElementById('refresh-logs');
    if (refreshLogs) {
        refreshLogs.addEventListener('click', function() {
            loadLogsData();
        });
    }
    
    // Обработчик кнопки автопрокрутки
    const autoScroll = document.getElementById('auto-scroll');
    if (autoScroll) {
        autoScroll.addEventListener('click', function() {
            this.classList.toggle('active');
            
            // Если включена автопрокрутка, прокручиваем до конца
            if (this.classList.contains('active')) {
                const logsContainer = document.getElementById('logs-container');
                logsContainer.scrollTop = logsContainer.scrollHeight;
            }
        });
    }
    
    // Обработчик кнопки копирования логов
    const copyLogs = document.getElementById('copy-logs');
    if (copyLogs) {
        copyLogs.addEventListener('click', function() {
            const logsContainer = document.getElementById('logs-container');
            const logsText = logsContainer.innerText;
            
            // Копируем текст в буфер обмена
            navigator.clipboard.writeText(logsText)
                .then(() => {
                    showNotification('Логи скопированы в буфер обмена', 'success');
                })
                .catch(err => {
                    console.error('Ошибка при копировании:', err);
                    showNotification('Ошибка при копировании логов', 'error');
                });
        });
    }
    
    // Обработчик кнопки разворачивания логов
    const expandLogs = document.getElementById('expand-logs');
    if (expandLogs) {
        expandLogs.addEventListener('click', function() {
            const logsTerminal = document.querySelector('.logs-terminal');
            logsTerminal.classList.toggle('expanded');
            
            // Меняем иконку
            const icon = this.querySelector('i');
            if (logsTerminal.classList.contains('expanded')) {
                icon.classList.remove('fa-expand-alt');
                icon.classList.add('fa-compress-alt');
            } else {
                icon.classList.remove('fa-compress-alt');
                icon.classList.add('fa-expand-alt');
            }
        });
    }
    
    // Обработчик кнопки экспорта логов
    const exportLogs = document.getElementById('export-logs');
    if (exportLogs) {
        exportLogs.addEventListener('click', function() {
            const level = document.getElementById('log-level').value;
            const limit = document.getElementById('log-limit').value;
            
            // Формируем URL для экспорта
            const url = `/api/admin/export-logs?level=${level}&limit=${limit}`;
            
            // Открываем URL в новой вкладке для скачивания
            window.open(url, '_blank');
        });
    }
    
    // Обработчик кнопки очистки логов
    const clearLogs = document.getElementById('clear-logs');
    if (clearLogs) {
        clearLogs.addEventListener('click', function() {
            // Показываем модальное окно подтверждения
            const modalContent = `
                <div class="modal-header">
                    <h2>Подтверждение очистки логов</h2>
                    <button class="modal-close" onclick="closeModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <p>Вы действительно хотите очистить логи?</p>
                    <p class="warning-text">Это действие невозможно отменить!</p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-danger" onclick="confirmClearLogs()">
                        <i class="fas fa-trash-alt"></i> Очистить
                    </button>
                    <button class="btn btn-secondary" onclick="closeModal()">
                        <i class="fas fa-times"></i> Отмена
                    </button>
                </div>
            `;
            
            openModal(modalContent, 'small');
        });
    }
    
    // Обработчики изменения фильтров
    const logFilters = document.querySelectorAll('#log-level, #log-component, #log-limit');
    logFilters.forEach(filter => {
        filter.addEventListener('change', function() {
            loadLogsData();
        });
    });
}

// Функция подтверждения очистки логов
function confirmClearLogs() {
    // В реальном приложении здесь будет отправка запроса на очистку логов
    // Для примера просто показываем уведомление
    
    showNotification('Логи успешно очищены', 'success');
    
    // Закрываем модальное окно и обновляем данные
    closeModal();
    loadLogsData();
}

// Загрузка данных для страницы настроек
function loadSettingsData() {
    // Запрос данных от API
    fetch('/api/admin/settings')
        .then(response => response.json())
        .then(settings => {
            // Заполняем форму настройками
            fillSettingsForm(settings);
        })
        .catch(error => {
            console.error('Ошибка при загрузке настроек:', error);
            showNotification('Ошибка при загрузке настроек', 'error');
        });
}

// Заполнение формы настроек
function fillSettingsForm(settings) {
    // Основные настройки
    document.getElementById('auto-update-topics').checked = settings.auto_update_topics !== false;
    document.getElementById('collect-statistics').checked = settings.collect_statistics !== false;
    document.getElementById('developer-mode').checked = settings.developer_mode === true;
    document.getElementById('private-mode').checked = settings.private_mode === true;
    
    // Настройки API
    if (settings.api_request_limit) {
        document.getElementById('api-request-limit').value = settings.api_request_limit;
        document.getElementById('api-request-limit-range').value = settings.api_request_limit;
    }
    
    if (settings.cache_duration) {
        document.getElementById('cache-duration').value = settings.cache_duration;
        document.getElementById('cache-duration-range').value = settings.cache_duration;
    }
    
    if (settings.api_model) {
        document.getElementById('api-model').value = settings.api_model;
    }
    
    if (settings.api_key) {
        document.getElementById('api-key').value = settings.api_key;
    }
    
    // Настройки уведомлений
    if (settings.notification_level) {
        document.getElementById('notification-level').value = settings.notification_level;
    }
    
    if (settings.notification_channel) {
        document.getElementById('notification-channel').value = settings.notification_channel;
    }
    
    if (settings.notification_schedule) {
        document.getElementById('notification-schedule').value = settings.notification_schedule;
    }
}

// Обработчик отправки формы настроек
function handleSettingsSubmit(e) {
    e.preventDefault();
    
    // Собираем данные формы
    const settings = {
        // Основные настройки
        auto_update_topics: document.getElementById('auto-update-topics').checked,
        collect_statistics: document.getElementById('collect-statistics').checked,
        developer_mode: document.getElementById('developer-mode').checked,
        private_mode: document.getElementById('private-mode').checked,
        
        // Настройки API
        api_request_limit: parseInt(document.getElementById('api-request-limit').value),
        cache_duration: parseInt(document.getElementById('cache-duration').value),
        api_model: document.getElementById('api-model').value,
        api_key: document.getElementById('api-key').value,
        
        // Настройки уведомлений
        notification_level: document.getElementById('notification-level').value,
        notification_channel: document.getElementById('notification-channel').value,
        notification_schedule: document.getElementById('notification-schedule').value
    };
    
    // Отправка настроек на сервер
    fetch('/api/admin/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Настройки успешно сохранены', 'success');
        } else {
            showNotification(`Ошибка при сохранении настроек: ${data.message || 'Неизвестная ошибка'}`, 'error');
        }
    })
    .catch(error => {
        console.error('Ошибка при сохранении настроек:', error);
        showNotification('Ошибка при сохранении настроек', 'error');
    });
}

// Синхронизация связанных элементов управления (ползунок и поле ввода)
function setupRangeInputSync() {
    // API лимит запросов
    const apiRequestLimitRange = document.getElementById('api-request-limit-range');
    const apiRequestLimit = document.getElementById('api-request-limit');
    
    if (apiRequestLimitRange && apiRequestLimit) {
        apiRequestLimitRange.addEventListener('input', function() {
            apiRequestLimit.value = this.value;
        });
        
        apiRequestLimit.addEventListener('input', function() {
            apiRequestLimitRange.value = this.value;
        });
    }
    
    // Продолжительность кэширования
    const cacheDurationRange = document.getElementById('cache-duration-range');
    const cacheDuration = document.getElementById('cache-duration');
    
    if (cacheDurationRange && cacheDuration) {
        cacheDurationRange.addEventListener('input', function() {
            cacheDuration.value = this.value;
        });
        
        cacheDuration.addEventListener('input', function() {
            cacheDurationRange.value = this.value;
        });
    }
    
    // Переключатель видимости API ключа
    const toggleApiKey = document.getElementById('toggle-api-key');
    const apiKey = document.getElementById('api-key');
    
    if (toggleApiKey && apiKey) {
        toggleApiKey.addEventListener('click', function() {
            const icon = this.querySelector('i');
            
            if (apiKey.type === 'password') {
                apiKey.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                apiKey.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    }
}

// Загрузка данных для страницы обслуживания
function loadMaintenanceData() {
    // Загружаем размер кэша
    fetch('/api/admin/maintenance/cache-size')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('cache-status').innerHTML = `Размер кэша: <span class="status-value">${data.size}</span>`;
            }
        })
        .catch(error => {
            console.error('Ошибка при получении размера кэша:', error);
        });
    
    // Загружаем время последнего резервного копирования
    fetch('/api/admin/maintenance/last-backup')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('last-backup-time').textContent = data.time || 'Никогда';
            }
        })
        .catch(error => {
            console.error('Ошибка при получении времени последнего резервного копирования:', error);
        });
    
    // Загружаем размер логов
    fetch('/api/admin/maintenance/logs-size')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('logs-size').textContent = data.size || '0 КБ';
            }
        })
        .catch(error => {
            console.error('Ошибка при получении размера логов:', error);
        });
}

// Обработчик действий обслуживания
function handleMaintenanceAction(e) {
    const action = this.getAttribute('data-action');
    
    // Показываем индикатор загрузки
    this.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Выполнение...`;
    this.disabled = true;
    
    // Выполняем действие
    fetch(`/api/admin/maintenance/${action}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        // Восстанавливаем кнопку
        this.disabled = false;
        
        if (data.success) {
            showNotification(data.message || 'Операция выполнена успешно', 'success');
            
            // Обновляем данные страницы
            loadMaintenanceData();
            
            // Обработка специфических действий
            if (action === 'backup') {
                document.getElementById('last-backup-time').textContent = data.backup_time || 'Сейчас';
            } else if (action === 'update-api') {
                // Запускаем отслеживание прогресса
                startProgressTracking();
            }
        } else {
            showNotification(data.error || 'Ошибка при выполнении операции', 'error');
        }
        
        // Восстанавливаем исходный текст кнопки
        updateMaintenanceButtonText(this, action);
    })
    .catch(error => {
        console.error(`Ошибка при выполнении действия ${action}:`, error);
        showNotification(`Ошибка при выполнении операции: ${error.message}`, 'error');
        
        // Восстанавливаем кнопку и текст
        this.disabled = false;
        updateMaintenanceButtonText(this, action);
    });
}

// Обновление текста кнопки обслуживания
function updateMaintenanceButtonText(button, action) {
    const actionTexts = {
        'clear-cache': '<i class="fas fa-broom"></i> Полная очистка',
        'selective-cache': '<i class="fas fa-filter"></i> Выборочно',
        'backup': '<i class="fas fa-hdd"></i> Выполнить',
        'update-api': '<i class="fas fa-cloud-download-alt"></i> Выполнить',
        'clean-logs': '<i class="fas fa-eraser"></i> Выполнить',
        'restart': '<i class="fas fa-redo"></i> Выполнить',
        'integrate': '<i class="fas fa-exchange-alt"></i> Выполнить',
        'security': '<i class="fas fa-tasks"></i> Выполнить'
    };
    
    button.innerHTML = actionTexts[action] || '<i class="fas fa-check"></i> Выполнить';
}

// Отслеживание прогресса операции
function startProgressTracking() {
    const progressBar = document.getElementById('api-progress');
    const progressText = document.querySelector('.progress-text');
    
    if (!progressBar || !progressText) return;
    
    let progress = 0;
    const progressInterval = setInterval(() => {
        // Симуляция прогресса для демонстрации
        progress += 5;
        if (progress > 100) {
            clearInterval(progressInterval);
            progress = 100;
        }
        
        progressBar.style.width = `${progress}%`;
        progressText.textContent = `${progress}%`;
        
        if (progress === 100) {
            showNotification('Обновление данных API завершено', 'success');
        }
    }, 500);
}

// Открытие модального окна
function openModal(content, size = 'medium') {
    const modalOverlay = document.getElementById('modal-overlay');
    const modalContainer = document.getElementById('modal-container');
    
    if (!modalOverlay || !modalContainer) return;
    
    // Устанавливаем размер модального окна
    modalContainer.className = `modal ${size}`;
    
    // Устанавливаем содержимое
    modalContainer.innerHTML = content;
    
    // Показываем модальное окно
    modalOverlay.style.display = 'flex';
    setTimeout(() => {
        modalOverlay.classList.add('visible');
    }, 10);
    
    // Блокируем прокрутку страницы
    document.body.style.overflow = 'hidden';
}

// Закрытие модального окна
function closeModal() {
    const modalOverlay = document.getElementById('modal-overlay');
    
    if (!modalOverlay) return;
    
    // Скрываем модальное окно
    modalOverlay.classList.remove('visible');
    setTimeout(() => {
        modalOverlay.style.display = 'none';
    }, 300);
    
    // Разблокируем прокрутку страницы
    document.body.style.overflow = '';
}

// Обработчик глобального поиска
function handleGlobalSearch() {
    const searchTerm = this.value.trim().toLowerCase();
    
    if (searchTerm.length < 2) return;
    
    // Выводим результаты поиска в уведомлении
    showNotification(`Поиск по запросу: "${searchTerm}"`, 'info');
}

// Обновление информации о текущем пользователе
function updateUserInfo() {
    const userNameEl = document.getElementById('user-name');
    const userRoleEl = document.getElementById('user-role');
    
    if (userNameEl) {
        userNameEl.textContent = 'Администратор';
    }
    
    if (userRoleEl) {
        userRoleEl.textContent = currentUser && currentUser.is_super_admin ? 'Супер-администратор' : 'Администратор';
    }
}

// Запуск таймера обновления времени сервера
function startServerTimeUpdater() {
    // Обновляем время каждую секунду
    setInterval(() => {
        // В реальной версии здесь был бы запрос к серверу
        // Для демонстрации используем текущее время браузера
        const now = new Date();
        
        // Пока не используется
    }, 1000);
}

// При загрузке страницы переходим на страницу из хэша URL
window.addEventListener('hashchange', function() {
    const page = window.location.hash.substring(1);
    if (page && document.getElementById(`${page}-page`)) {
        switchPage(page);
    }
});

// Инициализируем страницу из хэша URL, если есть
if (window.location.hash) {
    const page = window.location.hash.substring(1);
    if (page && document.getElementById(`${page}-page`)) {
        currentPage = page;
    }
}
