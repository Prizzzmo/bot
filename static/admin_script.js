
document.addEventListener('DOMContentLoaded', function() {
    // Переменные для хранения состояния
    let currentUser = null;
    let isAuthenticated = false;
    
    // Элементы аутентификации
    const authContainer = document.getElementById('admin-auth');
    const loginForm = document.getElementById('admin-login-form');
    
    // Табы
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Формы
    const addAdminForm = document.getElementById('add-admin-form');
    const removeAdminForm = document.getElementById('remove-admin-form');
    const botSettingsForm = document.getElementById('bot-settings-form');
    
    // Другие элементы
    const adminList = document.getElementById('admin-list');
    const superAdminList = document.getElementById('super-admin-list');
    const adminToRemove = document.getElementById('admin-to-remove');
    const logsContainer = document.getElementById('logs-container');
    const logLevel = document.getElementById('log-level');
    const logLimit = document.getElementById('log-limit');
    const refreshLogsButton = document.getElementById('refresh-logs');
    const statsData = document.getElementById('stats-data');
    
    // Кнопки технического обслуживания
    const clearCacheButton = document.getElementById('clear-cache');
    const createBackupButton = document.getElementById('create-backup');
    const updateApiDataButton = document.getElementById('update-api-data');
    const cleanLogsButton = document.getElementById('clean-logs');
    const restartBotButton = document.getElementById('restart-bot');
    
    // Функция для проверки аутентификации
    async function checkAuth() {
        try {
            const response = await fetch('/api/admin/check-auth');
            const data = await response.json();
            
            if (data.authenticated) {
                isAuthenticated = true;
                currentUser = data.user;
                authContainer.style.display = 'none';
                loadAdminData();
            } else {
                isAuthenticated = false;
                authContainer.style.display = 'flex';
            }
        } catch (error) {
            console.error('Ошибка при проверке аутентификации:', error);
            showNotification('Ошибка при проверке аутентификации', 'error');
        }
    }
    
    // Функция для загрузки данных админ-панели
    function loadAdminData() {
        loadStats();
        loadAdmins();
        loadLogs();
        loadSettings();
    }
    
    // Функция для обработки входа
    async function handleLogin(e) {
        e.preventDefault();
        
        const adminId = document.getElementById('admin-id').value;
        
        try {
            const response = await fetch('/api/admin/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ admin_id: adminId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                isAuthenticated = true;
                currentUser = data.user;
                authContainer.style.display = 'none';
                loadAdminData();
            } else {
                showNotification(data.message || 'Ошибка аутентификации', 'error');
            }
        } catch (error) {
            console.error('Ошибка при входе:', error);
            showNotification('Ошибка при входе', 'error');
        }
    }
    
    // Функция для загрузки статистики
    async function loadStats() {
        try {
            const response = await fetch('/api/admin/stats');
            const data = await response.json();
            
            if (data.error) {
                statsData.innerHTML = `<p class="error">Ошибка: ${data.error}</p>`;
                return;
            }
            
            statsData.innerHTML = `
                <div class="stat-item">
                    <h3>Пользователи</h3>
                    <p>Всего: ${data.users || 0}</p>
                </div>
                <div class="stat-item">
                    <h3>Сообщения</h3>
                    <p>Всего: ${data.messages || 0}</p>
                </div>
                <div class="stat-item">
                    <h3>Время работы</h3>
                    <p>${data.uptime || 'Неизвестно'}</p>
                </div>
                <div class="stat-item">
                    <h3>За последние 24 часа</h3>
                    <p>Запусков бота: ${data.bot_starts || 0}</p>
                    <p>Запросов тем: ${data.topic_requests || 0}</p>
                    <p>Пройдено тестов: ${data.completed_tests || 0}</p>
                </div>
            `;
        } catch (error) {
            console.error('Ошибка при загрузке статистики:', error);
            statsData.innerHTML = '<p class="error">Ошибка при загрузке статистики</p>';
        }
    }
    
    // Функция для загрузки списка администраторов
    async function loadAdmins() {
        try {
            const response = await fetch('/api/admin/admins');
            const data = await response.json();
            
            if (data.error) {
                adminList.innerHTML = `<li class="error">Ошибка: ${data.error}</li>`;
                superAdminList.innerHTML = `<li class="error">Ошибка: ${data.error}</li>`;
                return;
            }
            
            // Очистка списков
            adminList.innerHTML = '';
            superAdminList.innerHTML = '';
            adminToRemove.innerHTML = '<option value="">Выберите администратора</option>';
            
            // Заполнение списка администраторов
            if (data.admin_ids && data.admin_ids.length > 0) {
                data.admin_ids.forEach(adminId => {
                    const li = document.createElement('li');
                    li.textContent = `ID: ${adminId}`;
                    adminList.appendChild(li);
                    
                    const option = document.createElement('option');
                    option.value = adminId;
                    option.textContent = `Админ: ${adminId}`;
                    adminToRemove.appendChild(option);
                });
            } else {
                adminList.innerHTML = '<li>Нет администраторов</li>';
            }
            
            // Заполнение списка супер-администраторов
            if (data.super_admin_ids && data.super_admin_ids.length > 0) {
                data.super_admin_ids.forEach(adminId => {
                    const li = document.createElement('li');
                    li.textContent = `ID: ${adminId}`;
                    superAdminList.appendChild(li);
                    
                    // Не добавляем текущего пользователя в список для удаления
                    if (adminId != currentUser?.id) {
                        const option = document.createElement('option');
                        option.value = adminId;
                        option.textContent = `Супер-админ: ${adminId}`;
                        adminToRemove.appendChild(option);
                    }
                });
            } else {
                superAdminList.innerHTML = '<li>Нет супер-администраторов</li>';
            }
        } catch (error) {
            console.error('Ошибка при загрузке списка администраторов:', error);
            adminList.innerHTML = '<li class="error">Ошибка при загрузке списка администраторов</li>';
            superAdminList.innerHTML = '<li class="error">Ошибка при загрузке списка администраторов</li>';
        }
    }
    
    // Функция для загрузки логов
    async function loadLogs() {
        try {
            const level = logLevel.value !== 'all' ? logLevel.value : '';
            const limit = logLimit.value || 100;
            
            const response = await fetch(`/api/logs?level=${level}&limit=${limit}`);
            const data = await response.json();
            
            if (data.error) {
                logsContainer.innerHTML = `Ошибка: ${data.error}`;
                return;
            }
            
            if (Array.isArray(data) && data.length > 0) {
                logsContainer.innerHTML = data.join('\n');
            } else {
                logsContainer.innerHTML = 'Логи отсутствуют';
            }
            
            // Прокрутка вниз для отображения последних логов
            logsContainer.scrollTop = logsContainer.scrollHeight;
        } catch (error) {
            console.error('Ошибка при загрузке логов:', error);
            logsContainer.innerHTML = 'Ошибка при загрузке логов';
        }
    }
    
    // Функция для загрузки настроек
    async function loadSettings() {
        try {
            const response = await fetch('/api/admin/settings');
            const data = await response.json();
            
            if (data.error) {
                showNotification(`Ошибка: ${data.error}`, 'error');
                return;
            }
            
            document.getElementById('auto-update-topics').checked = data.auto_update_topics || false;
            document.getElementById('collect-statistics').checked = data.collect_statistics || false;
            document.getElementById('developer-mode').checked = data.developer_mode || false;
            document.getElementById('private-mode').checked = data.private_mode || false;
        } catch (error) {
            console.error('Ошибка при загрузке настроек:', error);
            showNotification('Ошибка при загрузке настроек', 'error');
        }
    }
    
    // Функция для добавления администратора
    async function addAdmin(e) {
        e.preventDefault();
        
        const adminId = document.getElementById('new-admin-id').value;
        const isSuper = document.getElementById('is-super-admin').checked;
        
        try {
            const response = await fetch('/api/admin/add-admin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    admin_id: adminId,
                    is_super: isSuper
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showNotification('Администратор успешно добавлен', 'success');
                document.getElementById('new-admin-id').value = '';
                document.getElementById('is-super-admin').checked = false;
                loadAdmins();
            } else {
                showNotification(data.message || 'Ошибка при добавлении администратора', 'error');
            }
        } catch (error) {
            console.error('Ошибка при добавлении администратора:', error);
            showNotification('Ошибка при добавлении администратора', 'error');
        }
    }
    
    // Функция для удаления администратора
    async function removeAdmin(e) {
        e.preventDefault();
        
        const adminId = adminToRemove.value;
        
        if (!adminId) {
            showNotification('Выберите администратора для удаления', 'error');
            return;
        }
        
        if (confirm(`Вы уверены, что хотите удалить администратора с ID ${adminId}?`)) {
            try {
                const response = await fetch('/api/admin/remove-admin', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        admin_id: adminId
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showNotification('Администратор успешно удален', 'success');
                    loadAdmins();
                } else {
                    showNotification(data.message || 'Ошибка при удалении администратора', 'error');
                }
            } catch (error) {
                console.error('Ошибка при удалении администратора:', error);
                showNotification('Ошибка при удалении администратора', 'error');
            }
        }
    }
    
    // Функция для сохранения настроек
    async function saveSettings(e) {
        e.preventDefault();
        
        const settings = {
            auto_update_topics: document.getElementById('auto-update-topics').checked,
            collect_statistics: document.getElementById('collect-statistics').checked,
            developer_mode: document.getElementById('developer-mode').checked,
            private_mode: document.getElementById('private-mode').checked
        };
        
        try {
            const response = await fetch('/api/admin/save-settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });
            
            const data = await response.json();
            
            if (data.success) {
                showNotification('Настройки успешно сохранены', 'success');
            } else {
                showNotification(data.message || 'Ошибка при сохранении настроек', 'error');
            }
        } catch (error) {
            console.error('Ошибка при сохранении настроек:', error);
            showNotification('Ошибка при сохранении настроек', 'error');
        }
    }
    
    // Функция для выполнения действий технического обслуживания
    async function performMaintenance(action) {
        try {
            const response = await fetch('/api/admin/maintenance', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ action })
            });
            
            const data = await response.json();
            
            if (data.success) {
                showNotification(data.message || 'Операция выполнена успешно', 'success');
                
                // Обновляем данные после операции
                if (action === 'restart_bot') {
                    setTimeout(() => {
                        checkAuth();
                    }, 5000); // Даем боту время перезапуститься
                } else {
                    loadAdminData();
                }
            } else {
                showNotification(data.message || 'Ошибка при выполнении операции', 'error');
            }
        } catch (error) {
            console.error(`Ошибка при выполнении операции ${action}:`, error);
            showNotification('Ошибка при выполнении операции', 'error');
        }
    }
    
    // Функция для отображения уведомлений
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 500);
        }, 3000);
    }
    
    // Обработчики событий
    
    // Переключение табов
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            
            // Активация выбранной вкладки
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Отображение соответствующего содержимого
            tabContents.forEach(content => content.classList.remove('active'));
            document.getElementById(`${tabName}-tab`).classList.add('active');
        });
    });
    
    // Авторизация
    loginForm.addEventListener('submit', handleLogin);
    
    // Формы
    addAdminForm.addEventListener('submit', addAdmin);
    removeAdminForm.addEventListener('submit', removeAdmin);
    botSettingsForm.addEventListener('submit', saveSettings);
    
    // Обновление логов
    refreshLogsButton.addEventListener('click', loadLogs);
    
    // Кнопки технического обслуживания
    clearCacheButton.addEventListener('click', () => performMaintenance('clear_cache'));
    createBackupButton.addEventListener('click', () => performMaintenance('create_backup'));
    updateApiDataButton.addEventListener('click', () => performMaintenance('update_api_data'));
    cleanLogsButton.addEventListener('click', () => performMaintenance('clean_logs'));
    restartBotButton.addEventListener('click', () => {
        if (confirm('Вы уверены, что хотите перезапустить бота? Это приведет к кратковременной недоступности сервиса.')) {
            performMaintenance('restart_bot');
        }
    });
    
    // Проверка аутентификации при загрузке страницы
    checkAuth();
    
    // Создание CSS для уведомлений
    const style = document.createElement('style');
    style.textContent = `
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            background: #2ecc71;
            color: white;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1001;
            transition: opacity 0.5s ease;
        }
        
        .notification.error {
            background: #e74c3c;
        }
        
        .notification.info {
            background: #3498db;
        }
    `;
    document.head.appendChild(style);
});
