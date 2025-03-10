
// Глобальные переменные
let isAuthenticated = false; 
let currentUser = null;
let usersList = [];
let eventsData = [];
let statisticsData = {};
let settingsData = {};

// DOM-элементы
document.addEventListener('DOMContentLoaded', function() {
    // Проверяем аутентификацию при загрузке
    checkAuthentication();
    
    // Инициализация необходимых компонентов
    initializeTabs();
    initializeThemeToggle();
    
    // Привязка обработчиков форм
    attachFormHandlers();
    
    // Добавляем обработчик событий для кнопки выхода
    const logoutButton = document.getElementById('logout-button');
    if (logoutButton) {
        logoutButton.addEventListener('click', handleLogout);
    }
});

// Функция для проверки аутентификации
function checkAuthentication() {
    fetch('/api/admin/check-auth')
        .then(response => response.json())
        .then(data => {
            if (data.authenticated) {
                isAuthenticated = true;
                currentUser = data.user;
                showAdminPanel();
                loadAdminData();
                updateUserInfo();
            } else {
                isAuthenticated = false;
                showLoginForm();
            }
        })
        .catch(error => {
            console.error('Ошибка при проверке аутентификации:', error);
            isAuthenticated = false;
            showLoginForm();
        });
}

// Показываем форму входа
function showLoginForm() {
    const adminAuth = document.getElementById('admin-auth');
    const adminContainer = document.querySelector('.admin-container');
    
    if (adminAuth && adminContainer) {
        adminAuth.style.display = 'flex';
        adminContainer.style.display = 'none';
        
        // Добавляем обработчик для формы входа
        const loginForm = document.getElementById('admin-login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', handleLogin);
        }
    }
}

// Показываем админ-панель
function showAdminPanel() {
    const adminAuth = document.getElementById('admin-auth');
    const adminContainer = document.querySelector('.admin-container');
    
    if (adminAuth && adminContainer) {
        adminAuth.style.display = 'none';
        adminContainer.style.display = 'block';
    }
}

// Обработчик входа в систему
function handleLogin(e) {
    e.preventDefault();
    
    const adminPassword = document.getElementById('admin-password').value;
    const loginButton = document.querySelector('#admin-login-form button');
    const originalButtonText = loginButton.innerHTML;
    
    if (!adminPassword) {
        showAuthError('Введите пароль администратора');
        return;
    }
    
    // Показываем индикатор загрузки
    loginButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Вход...';
    loginButton.disabled = true;
    
    fetch('/api/admin/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ admin_password: adminPassword })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Ошибка HTTP: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showAuthError('Вход выполнен успешно!', true);
            setTimeout(() => {
                isAuthenticated = true;
                currentUser = data.user;
                showAdminPanel();
                loadAdminData();
                updateUserInfo();
                showNotification('Вы успешно вошли в систему', 'success');
            }, 1000);
        } else {
            loginButton.innerHTML = originalButtonText;
            loginButton.disabled = false;
            showAuthError(data.message || 'Неверный пароль администратора');
        }
    })
    .catch(error => {
        console.error('Ошибка при входе:', error);
        loginButton.innerHTML = originalButtonText;
        loginButton.disabled = false;
        showAuthError('Ошибка при авторизации: ' + error.message);
    });
}

// Показываем ошибку или сообщение авторизации
function showAuthError(message, isSuccess = false) {
    const authError = document.querySelector('.auth-error');
    if (authError) {
        authError.textContent = message;
        
        // Удаляем все классы стилей
        authError.classList.remove('visible', 'success', 'error');
        
        // Добавляем соответствующие классы
        authError.classList.add('visible');
        authError.classList.add(isSuccess ? 'success' : 'error');
        
        // Скрываем сообщение через 3 секунды
        setTimeout(() => {
            authError.classList.remove('visible');
        }, 3000);
    }
}

// Обработчик выхода из системы
function handleLogout() {
    // Удаляем cookie с ID администратора
    document.cookie = 'admin_id=; Max-Age=0; path=/;';
    
    // Сбрасываем состояние
    isAuthenticated = false;
    currentUser = null;
    
    // Показываем форму входа
    showLoginForm();
    
    showNotification('Вы успешно вышли из системы', 'info');
}

// Обновляем информацию о пользователе в интерфейсе
function updateUserInfo() {
    if (!currentUser) return;
    
    const userNameElement = document.getElementById('user-name');
    const userRoleElement = document.getElementById('user-role');
    
    if (userNameElement) {
        userNameElement.textContent = `ID: ${currentUser.id}`;
    }
    
    if (userRoleElement) {
        userRoleElement.textContent = currentUser.is_super_admin ? 'Супер-администратор' : 'Администратор';
    }
    
    // Управление видимостью элементов в зависимости от роли
    const superAdminElements = document.querySelectorAll('.super-admin-only');
    superAdminElements.forEach(element => {
        element.style.display = currentUser.is_super_admin ? 'block' : 'none';
    });
}

// Инициализация вкладок
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Удаляем активный класс у всех кнопок
            tabButtons.forEach(btn => btn.classList.remove('active'));
            
            // Добавляем активный класс нажатой кнопке
            this.classList.add('active');
            
            // Получаем идентификатор вкладки
            const tabId = this.getAttribute('data-tab');
            
            // Скрываем все вкладки
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Показываем нужную вкладку
            document.getElementById(`${tabId}-tab`).classList.add('active');
            
            // Загружаем данные для вкладки при необходимости
            if (tabId === 'stats') {
                loadStats();
            } else if (tabId === 'admins') {
                loadAdmins();
            } else if (tabId === 'logs') {
                loadLogs();
            } else if (tabId === 'settings') {
                loadSettings();
            } else if (tabId === 'maintenance') {
                // Ничего не загружаем для вкладки обслуживания
            } else if (tabId === 'users') {
                loadUsers();
            } else if (tabId === 'events') {
                loadEvents();
            } else if (tabId === 'dashboard') {
                loadDashboard();
            }
        });
    });
}

// Инициализация переключателя темы
function initializeThemeToggle() {
    // Создаем переключатель темы, если его нет
    if (!document.querySelector('.theme-toggle')) {
        const themeToggle = document.createElement('div');
        themeToggle.className = 'theme-toggle';
        themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
        document.body.appendChild(themeToggle);
        
        // Проверяем сохраненную тему
        const savedTheme = localStorage.getItem('admin-theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-theme');
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
        }
        
        // Добавляем обработчик клика
        themeToggle.addEventListener('click', function() {
            if (document.body.classList.contains('dark-theme')) {
                document.body.classList.remove('dark-theme');
                localStorage.setItem('admin-theme', 'light');
                themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
            } else {
                document.body.classList.add('dark-theme');
                localStorage.setItem('admin-theme', 'dark');
                themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
            }
        });
    }
}

// Привязка обработчиков форм
function attachFormHandlers() {
    // Форма добавления администратора
    const addAdminForm = document.getElementById('add-admin-form');
    if (addAdminForm) {
        addAdminForm.addEventListener('submit', handleAddAdmin);
    }
    
    // Форма удаления администратора
    const removeAdminForm = document.getElementById('remove-admin-form');
    if (removeAdminForm) {
        removeAdminForm.addEventListener('submit', handleRemoveAdmin);
    }
    
    // Форма настроек бота
    const botSettingsForm = document.getElementById('bot-settings-form');
    if (botSettingsForm) {
        botSettingsForm.addEventListener('submit', handleSaveSettings);
    }
    
    // Обработчик обновления логов
    const refreshLogsButton = document.getElementById('refresh-logs');
    if (refreshLogsButton) {
        refreshLogsButton.addEventListener('click', loadLogs);
    }
    
    // Обработчики для фильтров логов
    const logLevelFilter = document.getElementById('log-level');
    const logLimitFilter = document.getElementById('log-limit');
    
    if (logLevelFilter) {
        logLevelFilter.addEventListener('change', loadLogs);
    }
    
    if (logLimitFilter) {
        logLimitFilter.addEventListener('input', debounce(loadLogs, 500));
    }
    
    // Обработчики кнопок технического обслуживания
    const maintenanceButtons = document.querySelectorAll('.maintenance-action');
    maintenanceButtons.forEach(button => {
        button.addEventListener('click', function() {
            const action = button.getAttribute('data-action');
            handleMaintenanceAction(action);
        });
    });
    
    // Обработчик фильтрации пользователей
    const userSearchInput = document.getElementById('user-search');
    if (userSearchInput) {
        userSearchInput.addEventListener('input', debounce(filterUsers, 300));
    }
    
    // Обработчик фильтрации событий
    const eventSearchInput = document.getElementById('event-search');
    if (eventSearchInput) {
        eventSearchInput.addEventListener('input', debounce(filterEvents, 300));
    }
}

// Функция debounce для предотвращения частых вызовов функции
function debounce(func, wait) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), wait);
    };
}

// Загрузка всех данных админ-панели
function loadAdminData() {
    loadDashboard();
    loadStats();
    loadAdmins();
    loadLogs();
    loadSettings();
    loadUsers();
    loadEvents();
}

// Загрузка данных для дашборда
function loadDashboard() {
    Promise.all([
        fetch('/api/admin/stats').then(res => res.json()),
        fetch('/api/statistics').then(res => res.json()),
        fetch('/api/statistics/daily?days=7').then(res => res.json())
    ])
    .then(([adminStats, generalStats, dailyStats]) => {
        if (adminStats.error) {
            showNotification(adminStats.error, 'error');
            return;
        }
        
        // Обновляем дашборд
        updateDashboard(adminStats, generalStats, dailyStats);
    })
    .catch(error => {
        console.error('Ошибка при загрузке данных дашборда:', error);
        showNotification('Ошибка при загрузке дашборда', 'error');
    });
}

// Обновление дашборда
function updateDashboard(adminStats, generalStats, dailyStats) {
    const dashboardContainer = document.getElementById('dashboard-data');
    if (!dashboardContainer) return;
    
    // Получаем сегодняшнюю статистику и вчерашнюю для сравнения
    const today = dailyStats[dailyStats.length - 1] || {requests: 0, unique_users: 0};
    const yesterday = dailyStats[dailyStats.length - 2] || {requests: 0, unique_users: 0};
    
    // Рассчитываем изменения
    const requestChange = today.requests - yesterday.requests;
    const userChange = today.unique_users - yesterday.unique_users;
    
    // Заполняем данные дашборда
    dashboardContainer.innerHTML = `
        <div class="dashboard-grid">
            <div class="dashboard-card">
                <div class="dashboard-card-header">Пользователи</div>
                <div class="dashboard-card-body">
                    <div class="dashboard-value">
                        ${adminStats.user_count || 0}
                        <span class="dashboard-change ${userChange >= 0 ? '' : 'negative'}">
                            ${userChange >= 0 ? '+' : ''}${userChange}
                        </span>
                    </div>
                    <div class="dashboard-label">Всего пользователей</div>
                </div>
                <div class="dashboard-card-footer">
                    <span>Сегодня активных: ${today.unique_users || 0}</span>
                    <a href="#" class="btn btn-small" onclick="showTab('users')">Детали</a>
                </div>
            </div>
            
            <div class="dashboard-card">
                <div class="dashboard-card-header">Запросы</div>
                <div class="dashboard-card-body">
                    <div class="dashboard-value">
                        ${adminStats.message_count || 0}
                        <span class="dashboard-change ${requestChange >= 0 ? '' : 'negative'}">
                            ${requestChange >= 0 ? '+' : ''}${requestChange}
                        </span>
                    </div>
                    <div class="dashboard-label">Всего сообщений</div>
                </div>
                <div class="dashboard-card-footer">
                    <span>Сегодня запросов: ${today.requests || 0}</span>
                    <a href="#" class="btn btn-small" onclick="showTab('logs')">Логи</a>
                </div>
            </div>
            
            <div class="dashboard-card">
                <div class="dashboard-card-header">События</div>
                <div class="dashboard-card-body">
                    <div class="dashboard-value">
                        ${generalStats.events_count || 0}
                    </div>
                    <div class="dashboard-label">Исторических событий</div>
                </div>
                <div class="dashboard-card-footer">
                    <span>Категорий: ${generalStats.categories_count || 0}</span>
                    <a href="#" class="btn btn-small" onclick="showTab('events')">Просмотр</a>
                </div>
            </div>
            
            <div class="dashboard-card">
                <div class="dashboard-card-header">Система</div>
                <div class="dashboard-card-body">
                    <div class="dashboard-value">
                        ${adminStats.uptime || "Н/Д"}
                    </div>
                    <div class="dashboard-label">Время работы системы</div>
                </div>
                <div class="dashboard-card-footer">
                    <span>Запусков бота: ${adminStats.bot_starts || 0}</span>
                    <a href="#" class="btn btn-small" onclick="showTab('maintenance')">Управление</a>
                </div>
            </div>
        </div>
        
        <div class="stats-chart">
            <h3>Активность пользователей за 7 дней</h3>
            <img src="/api/chart/daily_activity?days=7" alt="График активности" width="100%">
        </div>
    `;
}

// Показываем определенную вкладку
function showTab(tabId) {
    const tabButton = document.querySelector(`.tab-button[data-tab="${tabId}"]`);
    if (tabButton) {
        tabButton.click();
    }
}

// Функция для загрузки статистики
function loadStats() {
    fetch('/api/admin/stats')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showNotification(data.error, 'error');
                return;
            }
            
            // Сохраняем данные глобально
            statisticsData = data;
            
            // Обновляем содержимое блока статистики
            const statsData = document.getElementById('stats-data');
            if (statsData) {
                statsData.innerHTML = `
                    <div class="stat-item">
                        <h3>Пользователи</h3>
                        <p>${data.user_count || 0}</p>
                    </div>
                    <div class="stat-item">
                        <h3>Сообщения</h3>
                        <p>${data.message_count || 0}</p>
                    </div>
                    <div class="stat-item">
                        <h3>Время работы</h3>
                        <p>${data.uptime || "Н/Д"}</p>
                    </div>
                    <div class="stat-item">
                        <h3>Запусков бота</h3>
                        <p>${data.bot_starts || 0}</p>
                    </div>
                    <div class="stat-item">
                        <h3>Запросов тем</h3>
                        <p>${data.topic_requests || 0}</p>
                    </div>
                    <div class="stat-item">
                        <h3>Пройдено тестов</h3>
                        <p>${data.completed_tests || 0}</p>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Ошибка при загрузке статистики:', error);
            showNotification('Ошибка при загрузке статистики', 'error');
        });
}

// Функция для загрузки списка администраторов
function loadAdmins() {
    fetch('/api/admin/admins')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showNotification(data.error, 'error');
                return;
            }
            
            // Очищаем списки
            const adminList = document.getElementById('admin-list');
            const superAdminList = document.getElementById('super-admin-list');
            const adminToRemove = document.getElementById('admin-to-remove');
            
            if (adminList) adminList.innerHTML = '';
            if (superAdminList) superAdminList.innerHTML = '';
            if (adminToRemove) adminToRemove.innerHTML = '<option value="">Выберите администратора</option>';
            
            // Заполняем список супер-админов
            if (superAdminList && data.super_admin_ids && data.super_admin_ids.length > 0) {
                data.super_admin_ids.forEach(adminId => {
                    const listItem = document.createElement('li');
                    listItem.innerHTML = `
                        <span>ID: ${adminId}</span>
                        ${adminId === currentUser.id ? '<span class="admin-badge">Это вы</span>' : ''}
                        <div class="admin-actions">
                            ${currentUser.is_super_admin && adminId !== currentUser.id ? 
                               `<button class="btn btn-small btn-danger" onclick="deleteAdmin(${adminId})">Удалить</button>` : ''}
                        </div>
                    `;
                    superAdminList.appendChild(listItem);
                    
                    // Добавляем в список для удаления
                    if (adminToRemove && adminId !== currentUser.id) {
                        const option = document.createElement('option');
                        option.value = adminId;
                        option.textContent = `Супер-админ: ${adminId}`;
                        adminToRemove.appendChild(option);
                    }
                });
            } else if (superAdminList) {
                const listItem = document.createElement('li');
                listItem.textContent = 'Нет супер-администраторов';
                superAdminList.appendChild(listItem);
            }
            
            // Заполняем список обычных админов
            if (adminList && data.admin_ids && data.admin_ids.length > 0) {
                data.admin_ids.forEach(adminId => {
                    const listItem = document.createElement('li');
                    listItem.innerHTML = `
                        <span>ID: ${adminId}</span>
                        ${adminId === currentUser.id ? '<span class="admin-badge">Это вы</span>' : ''}
                        <div class="admin-actions">
                            ${currentUser.is_super_admin ? 
                               `<button class="btn btn-small btn-danger" onclick="deleteAdmin(${adminId})">Удалить</button>` : ''}
                        </div>
                    `;
                    adminList.appendChild(listItem);
                    
                    // Добавляем в список для удаления
                    if (adminToRemove) {
                        const option = document.createElement('option');
                        option.value = adminId;
                        option.textContent = `Админ: ${adminId}`;
                        adminToRemove.appendChild(option);
                    }
                });
            } else if (adminList) {
                const listItem = document.createElement('li');
                listItem.textContent = 'Нет администраторов';
                adminList.appendChild(listItem);
            }
        })
        .catch(error => {
            console.error('Ошибка при загрузке администраторов:', error);
            showNotification('Ошибка при загрузке администраторов', 'error');
        });
}

// Функция для загрузки логов
function loadLogs() {
    const logLevel = document.getElementById('log-level')?.value || 'all';
    const logLimit = document.getElementById('log-limit')?.value || 100;
    
    fetch(`/api/admin/logs?level=${logLevel}&lines=${logLimit}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showNotification(data.error, 'error');
                return;
            }
            
            const logsContainer = document.getElementById('logs-container');
            if (!logsContainer) return;
            
            // Форматируем логи с подсветкой уровней
            let formattedLogs = '';
            data.forEach(log => {
                let logClass = 'log-info';
                if (log.includes(' - WARNING - ')) {
                    logClass = 'log-warning';
                } else if (log.includes(' - ERROR - ')) {
                    logClass = 'log-error';
                } else if (log.includes(' - DEBUG - ')) {
                    logClass = 'log-debug';
                }
                
                formattedLogs += `<div class="log-line ${logClass}">${escapeHtml(log)}</div>`;
            });
            
            logsContainer.innerHTML = formattedLogs || 'Логи отсутствуют';
            
            // Прокручиваем логи вниз для отображения последних записей
            logsContainer.scrollTop = logsContainer.scrollHeight;
        })
        .catch(error => {
            console.error('Ошибка при загрузке логов:', error);
            showNotification('Ошибка при загрузке логов', 'error');
        });
}

// Функция для загрузки настроек
function loadSettings() {
    fetch('/api/admin/settings')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showNotification(data.error, 'error');
                return;
            }
            
            // Сохраняем данные глобально
            settingsData = data;
            
            // Обновляем состояние чекбоксов
            document.getElementById('auto-update-topics')?.checked = data.auto_update_topics || false;
            document.getElementById('collect-statistics')?.checked = data.collect_statistics || false;
            document.getElementById('developer-mode')?.checked = data.developer_mode || false;
            document.getElementById('private-mode')?.checked = data.private_mode || false;
            
            // Дополнительные настройки
            if (document.getElementById('api-request-limit')) {
                document.getElementById('api-request-limit').value = data.api_request_limit || 100;
            }
            
            if (document.getElementById('cache-duration')) {
                document.getElementById('cache-duration').value = data.cache_duration || 24;
            }
            
            if (document.getElementById('notification-level')) {
                document.getElementById('notification-level').value = data.notification_level || 'all';
            }
        })
        .catch(error => {
            console.error('Ошибка при загрузке настроек:', error);
            showNotification('Ошибка при загрузке настроек', 'error');
        });
}

// Функция для загрузки пользователей
function loadUsers() {
    // Заглушка - в реальном коде здесь был бы запрос к API
    // Для демонстрации создаем тестовых пользователей
    const mockUsers = [
        { id: 123456789, name: "Иван", status: "active", last_activity: "2023-03-09 15:30", messages: 42 },
        { id: 987654321, name: "Мария", status: "active", last_activity: "2023-03-09 16:45", messages: 28 },
        { id: 555555555, name: "Алексей", status: "inactive", last_activity: "2023-03-05 10:15", messages: 13 },
        { id: 111111111, name: "Елена", status: "active", last_activity: "2023-03-09 14:20", messages: 37 },
        { id: 222222222, name: "Сергей", status: "blocked", last_activity: "2023-02-15 08:30", messages: 5 }
    ];
    
    usersList = mockUsers;
    displayUsers(usersList);
}

// Отображение пользователей
function displayUsers(users) {
    const usersContainer = document.getElementById('users-data');
    if (!usersContainer) return;
    
    if (users.length === 0) {
        usersContainer.innerHTML = '<p>Пользователи не найдены</p>';
        return;
    }
    
    let html = `
        <div class="users-list-header">
            <div>ID</div>
            <div>Имя</div>
            <div>Статус</div>
            <div>Посл. активность</div>
            <div>Сообщения</div>
        </div>
    `;
    
    users.forEach(user => {
        let statusClass = '';
        let statusText = '';
        
        switch (user.status) {
            case 'active':
                statusClass = 'active';
                statusText = 'Активен';
                break;
            case 'inactive':
                statusClass = 'inactive';
                statusText = 'Неактивен';
                break;
            case 'blocked':
                statusClass = 'blocked';
                statusText = 'Заблокирован';
                break;
            default:
                statusClass = 'inactive';
                statusText = 'Неизвестно';
        }
        
        html += `
            <div class="users-list-item">
                <div>${user.id}</div>
                <div>${user.name || 'Без имени'}</div>
                <div><span class="user-status ${statusClass}">${statusText}</span></div>
                <div>${user.last_activity || 'Н/Д'}</div>
                <div>${user.messages || 0}</div>
            </div>
        `;
    });
    
    usersContainer.innerHTML = html;
}

// Фильтрация пользователей
function filterUsers() {
    const searchQuery = document.getElementById('user-search')?.value.toLowerCase() || '';
    
    if (!searchQuery) {
        displayUsers(usersList);
        return;
    }
    
    const filteredUsers = usersList.filter(user => {
        return (
            user.id.toString().includes(searchQuery) ||
            (user.name && user.name.toLowerCase().includes(searchQuery))
        );
    });
    
    displayUsers(filteredUsers);
}

// Функция для загрузки исторических событий
function loadEvents() {
    // В реальном коде здесь был бы запрос к API для получения списка событий
    // Для демонстрации создаем тестовые события
    fetch('/api/historical-events?limit=10')
        .then(response => response.json())
        .then(data => {
            eventsData = data.slice(0, 10); // Ограничиваем для демонстрации
            displayEvents(eventsData);
        })
        .catch(error => {
            console.error('Ошибка при загрузке событий:', error);
            showNotification('Ошибка при загрузке исторических событий', 'error');
            
            // Показываем заглушку в случае ошибки
            const eventsContainer = document.getElementById('events-data');
            if (eventsContainer) {
                eventsContainer.innerHTML = '<p>Ошибка при загрузке событий. Пожалуйста, попробуйте позже.</p>';
            }
        });
}

// Отображение исторических событий
function displayEvents(events) {
    const eventsContainer = document.getElementById('events-data');
    if (!eventsContainer) return;
    
    if (!events || events.length === 0) {
        eventsContainer.innerHTML = '<p>События не найдены</p>';
        return;
    }
    
    let html = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Название</th>
                    <th>Дата</th>
                    <th>Категория</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    events.forEach(event => {
        html += `
            <tr>
                <td>${event.id || 'Н/Д'}</td>
                <td>${event.title || 'Без названия'}</td>
                <td>${event.date || 'Н/Д'}</td>
                <td>${event.category || 'Без категории'}</td>
                <td class="actions">
                    <button class="btn btn-small" onclick="showEventDetails('${event.id}')">Просмотр</button>
                </td>
            </tr>
        `;
    });
    
    html += `
            </tbody>
        </table>
    `;
    
    eventsContainer.innerHTML = html;
}

// Фильтрация исторических событий
function filterEvents() {
    const searchQuery = document.getElementById('event-search')?.value.toLowerCase() || '';
    
    if (!searchQuery) {
        displayEvents(eventsData);
        return;
    }
    
    const filteredEvents = eventsData.filter(event => {
        return (
            (event.id && event.id.toString().includes(searchQuery)) ||
            (event.title && event.title.toLowerCase().includes(searchQuery)) ||
            (event.date && event.date.toLowerCase().includes(searchQuery)) ||
            (event.category && event.category.toLowerCase().includes(searchQuery))
        );
    });
    
    displayEvents(filteredEvents);
}

// Показ подробной информации о событии
function showEventDetails(eventId) {
    const event = eventsData.find(e => e.id === eventId);
    
    if (!event) {
        showNotification('Событие не найдено', 'error');
        return;
    }
    
    // Создаем модальное окно для отображения информации
    const modalHtml = `
        <div class="modal-header">
            <h3>${event.title || 'Без названия'}</h3>
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            <p><strong>Дата:</strong> ${event.date || 'Не указана'}</p>
            <p><strong>Категория:</strong> ${event.category || 'Не указана'}</p>
            <p><strong>Описание:</strong> ${event.description || 'Описание отсутствует'}</p>
            ${event.location ? `
                <p><strong>Местоположение:</strong> 
                   Широта: ${event.location.lat}, Долгота: ${event.location.lng}
                </p>
            ` : ''}
        </div>
        <div class="modal-footer">
            <button class="btn" onclick="closeModal()">Закрыть</button>
        </div>
    `;
    
    showModal(modalHtml);
}

// Показ модального окна
function showModal(content) {
    // Проверяем, существует ли уже модальное окно
    let modalOverlay = document.querySelector('.modal-overlay');
    
    if (!modalOverlay) {
        modalOverlay = document.createElement('div');
        modalOverlay.className = 'modal-overlay';
        document.body.appendChild(modalOverlay);
    }
    
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = content;
    
    modalOverlay.innerHTML = '';
    modalOverlay.appendChild(modal);
    
    // Запускаем анимацию открытия
    setTimeout(() => {
        modalOverlay.classList.add('active');
    }, 10);
    
    // Закрытие по клику вне модального окна
    modalOverlay.addEventListener('click', function(e) {
        if (e.target === modalOverlay) {
            closeModal();
        }
    });
}

// Закрытие модального окна
function closeModal() {
    const modalOverlay = document.querySelector('.modal-overlay');
    if (!modalOverlay) return;
    
    modalOverlay.classList.remove('active');
    
    // Удаляем модальное окно после анимации
    setTimeout(() => {
        modalOverlay.remove();
    }, 300);
}

// Обработчик добавления администратора
function handleAddAdmin(e) {
    e.preventDefault();
    
    const adminId = document.getElementById('new-admin-id')?.value;
    const isSuper = document.getElementById('is-super-admin')?.checked || false;
    
    if (!adminId) {
        showNotification('Укажите ID пользователя', 'error');
        return;
    }
    
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
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }
        
        showNotification('Администратор успешно добавлен', 'success');
        document.getElementById('new-admin-id').value = '';
        document.getElementById('is-super-admin').checked = false;
        
        // Обновляем список администраторов
        loadAdmins();
    })
    .catch(error => {
        console.error('Ошибка при добавлении администратора:', error);
        showNotification('Ошибка при добавлении администратора', 'error');
    });
}

// Обработчик удаления администратора
function handleRemoveAdmin(e) {
    e.preventDefault();
    
    const adminId = document.getElementById('admin-to-remove')?.value;
    
    if (!adminId) {
        showNotification('Выберите администратора для удаления', 'error');
        return;
    }
    
    // Подтверждение перед удалением
    if (!confirm(`Вы уверены, что хотите удалить администратора с ID ${adminId}?`)) {
        return;
    }
    
    deleteAdmin(adminId);
}

// Функция удаления администратора
function deleteAdmin(adminId) {
    fetch(`/api/admin/admins/${adminId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }
        
        showNotification('Администратор успешно удален', 'success');
        
        // Обновляем список администраторов
        loadAdmins();
    })
    .catch(error => {
        console.error('Ошибка при удалении администратора:', error);
        showNotification('Ошибка при удалении администратора', 'error');
    });
}

// Обработчик сохранения настроек
function handleSaveSettings(e) {
    e.preventDefault();
    
    const settings = {
        auto_update_topics: document.getElementById('auto-update-topics')?.checked || false,
        collect_statistics: document.getElementById('collect-statistics')?.checked || false,
        developer_mode: document.getElementById('developer-mode')?.checked || false,
        private_mode: document.getElementById('private-mode')?.checked || false
    };
    
    // Дополнительные настройки
    if (document.getElementById('api-request-limit')) {
        settings.api_request_limit = parseInt(document.getElementById('api-request-limit').value) || 100;
    }
    
    if (document.getElementById('cache-duration')) {
        settings.cache_duration = parseInt(document.getElementById('cache-duration').value) || 24;
    }
    
    if (document.getElementById('notification-level')) {
        settings.notification_level = document.getElementById('notification-level').value || 'all';
    }
    
    fetch('/api/admin/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }
        
        showNotification('Настройки успешно сохранены', 'success');
        
        // Обновляем сохраненные настройки
        settingsData = settings;
    })
    .catch(error => {
        console.error('Ошибка при сохранении настроек:', error);
        showNotification('Ошибка при сохранении настроек', 'error');
    });
}

// Обработчик операций технического обслуживания
function handleMaintenanceAction(action) {
    // Для операций, которые могут быть опасными, запрашиваем подтверждение
    if (action === 'restart' && !confirm('Вы уверены, что хотите перезапустить бота?')) {
        return;
    }
    
    if (action === 'clean-logs' && !confirm('Вы уверены, что хотите очистить старые логи?')) {
        return;
    }
    
    let actionName = '';
    switch (action) {
        case 'clear-cache': actionName = 'Очистка кэша'; break;
        case 'backup': actionName = 'Создание резервной копии'; break;
        case 'update-api': actionName = 'Обновление данных API'; break;
        case 'clean-logs': actionName = 'Очистка логов'; break;
        case 'restart': actionName = 'Перезапуск бота'; break;
        default: actionName = 'Операция';
    }
    
    fetch(`/api/admin/maintenance/${action}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            showNotification(data.error, 'error');
            return;
        }
        
        showNotification(data.message || `${actionName} выполнено успешно`, 'success');
        
        // Обновляем данные, если необходимо
        if (action === 'clear-cache' || action === 'update-api') {
            loadStats();
        } else if (action === 'clean-logs') {
            loadLogs();
        } else if (action === 'restart') {
            setTimeout(() => {
                window.location.reload();
            }, 5000);
            showNotification('Страница будет перезагружена через 5 секунд...', 'info');
        }
    })
    .catch(error => {
        console.error(`Ошибка при выполнении операции ${actionName}:`, error);
        showNotification(`Ошибка при выполнении операции ${actionName}`, 'error');
    });
}

// Функция для отображения уведомлений
function showNotification(message, type = 'info') {
    // Проверяем, существует ли уже контейнер уведомлений
    let notificationContainer = document.getElementById('notification-container');
    
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        document.body.appendChild(notificationContainer);
    }
    
    // Создаем элемент уведомления
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    // Определяем иконку в зависимости от типа
    let icon = '';
    switch (type) {
        case 'success': icon = '✓'; break;
        case 'error': icon = '✕'; break;
        case 'warning': icon = '⚠'; break;
        default: icon = 'ℹ';
    }
    
    notification.innerHTML = `
        ${icon} ${message}
        <button class="close-btn" onclick="this.parentElement.remove()">&times;</button>
    `;
    
    // Добавляем уведомление в контейнер
    notificationContainer.appendChild(notification);
    
    // Автоматически удаляем уведомление через 3 секунды
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.opacity = '0';
            
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
                
                // Удаляем контейнер, если больше нет уведомлений
                if (notificationContainer.childNodes.length === 0) {
                    notificationContainer.remove();
                }
            }, 500);
        }
    }, 3000);
}

// Вспомогательная функция для экранирования HTML
function escapeHtml(text) {
    if (!text) return '';
    
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Экспорт функций для использования в HTML
window.showTab = showTab;
window.deleteAdmin = deleteAdmin;
window.showEventDetails = showEventDetails;
window.closeModal = closeModal;
window.handleMaintenanceAction = handleMaintenanceAction;
