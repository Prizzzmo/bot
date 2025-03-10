
// Глобальные переменные
let isAuthenticated = true; // Всегда авторизован по умолчанию, как вы и просили

// DOM-элементы
document.addEventListener('DOMContentLoaded', function() {
    // Получаем ссылки на элементы интерфейса
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    const adminList = document.getElementById('admin-list');
    const superAdminList = document.getElementById('super-admin-list');
    const adminToRemove = document.getElementById('admin-to-remove');
    const addAdminForm = document.getElementById('add-admin-form');
    const removeAdminForm = document.getElementById('remove-admin-form');
    const botSettingsForm = document.getElementById('bot-settings-form');
    const logsContainer = document.getElementById('logs-container');
    const statsData = document.getElementById('stats-data');
    
    // Кнопки для технического обслуживания
    const clearCacheButton = document.getElementById('clear-cache');
    const createBackupButton = document.getElementById('create-backup');
    const updateApiDataButton = document.getElementById('update-api-data');
    const cleanLogsButton = document.getElementById('clean-logs');
    const restartBotButton = document.getElementById('restart-bot');
    
    // Загружаем данные админ-панели
    loadAdminData();
    
    // Обработчики вкладок
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
        });
    });
    
    // Функция для загрузки данных админ-панели
    function loadAdminData() {
        loadStats();
        loadAdmins();
        loadLogs();
        loadSettings();
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
                
                // Обновляем содержимое блока статистики
                statsData.innerHTML = `
                    <div class="stat-item">
                        <h3>Пользователи</h3>
                        <p>${data.user_count}</p>
                    </div>
                    <div class="stat-item">
                        <h3>Сообщения</h3>
                        <p>${data.message_count}</p>
                    </div>
                    <div class="stat-item">
                        <h3>Время работы</h3>
                        <p>${data.uptime}</p>
                    </div>
                    <div class="stat-item">
                        <h3>Запусков бота</h3>
                        <p>${data.bot_starts}</p>
                    </div>
                    <div class="stat-item">
                        <h3>Запросов тем</h3>
                        <p>${data.topic_requests}</p>
                    </div>
                    <div class="stat-item">
                        <h3>Пройдено тестов</h3>
                        <p>${data.completed_tests}</p>
                    </div>
                `;
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
                adminList.innerHTML = '';
                superAdminList.innerHTML = '';
                adminToRemove.innerHTML = '<option value="">Выберите администратора</option>';
                
                // Заполняем список супер-админов
                if (data.super_admin_ids && data.super_admin_ids.length > 0) {
                    data.super_admin_ids.forEach(adminId => {
                        const listItem = document.createElement('li');
                        listItem.textContent = `ID: ${adminId}`;
                        superAdminList.appendChild(listItem);
                        
                        // Добавляем в список для удаления
                        const option = document.createElement('option');
                        option.value = adminId;
                        option.textContent = `Супер-админ: ${adminId}`;
                        adminToRemove.appendChild(option);
                    });
                } else {
                    const listItem = document.createElement('li');
                    listItem.textContent = 'Нет супер-администраторов';
                    superAdminList.appendChild(listItem);
                }
                
                // Заполняем список обычных админов
                if (data.admin_ids && data.admin_ids.length > 0) {
                    data.admin_ids.forEach(adminId => {
                        const listItem = document.createElement('li');
                        listItem.textContent = `ID: ${adminId}`;
                        adminList.appendChild(listItem);
                        
                        // Добавляем в список для удаления
                        const option = document.createElement('option');
                        option.value = adminId;
                        option.textContent = `Админ: ${adminId}`;
                        adminToRemove.appendChild(option);
                    });
                } else {
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
        const logLevel = document.getElementById('log-level').value;
        const logLimit = document.getElementById('log-limit').value;
        
        fetch(`/api/admin/logs?level=${logLevel}&lines=${logLimit}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showNotification(data.error, 'error');
                    return;
                }
                
                logsContainer.innerHTML = data.join('');
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
                
                // Обновляем состояние чекбоксов
                document.getElementById('auto-update-topics').checked = data.auto_update_topics || false;
                document.getElementById('collect-statistics').checked = data.collect_statistics || false;
                document.getElementById('developer-mode').checked = data.developer_mode || false;
                document.getElementById('private-mode').checked = data.private_mode || false;
            })
            .catch(error => {
                console.error('Ошибка при загрузке настроек:', error);
                showNotification('Ошибка при загрузке настроек', 'error');
            });
    }
    
    // Обработчик формы добавления администратора
    if (addAdminForm) {
        addAdminForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const adminId = document.getElementById('new-admin-id').value;
            const isSuper = document.getElementById('is-super-admin').checked;
            
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
        });
    }
    
    // Обработчик формы удаления администратора
    if (removeAdminForm) {
        removeAdminForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const adminId = adminToRemove.value;
            
            if (!adminId) {
                showNotification('Выберите администратора для удаления', 'error');
                return;
            }
            
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
        });
    }
    
    // Обработчик формы настроек бота
    if (botSettingsForm) {
        botSettingsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const settings = {
                auto_update_topics: document.getElementById('auto-update-topics').checked,
                collect_statistics: document.getElementById('collect-statistics').checked,
                developer_mode: document.getElementById('developer-mode').checked,
                private_mode: document.getElementById('private-mode').checked
            };
            
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
            })
            .catch(error => {
                console.error('Ошибка при сохранении настроек:', error);
                showNotification('Ошибка при сохранении настроек', 'error');
            });
        });
    }
    
    // Обработчик кнопки обновления логов
    document.getElementById('refresh-logs').addEventListener('click', loadLogs);
    
    // Обработчики кнопок технического обслуживания
    if (clearCacheButton) {
        clearCacheButton.addEventListener('click', function() {
            performMaintenanceAction('clear-cache', 'Очистка кэша');
        });
    }
    
    if (createBackupButton) {
        createBackupButton.addEventListener('click', function() {
            performMaintenanceAction('backup', 'Создание резервной копии');
        });
    }
    
    if (updateApiDataButton) {
        updateApiDataButton.addEventListener('click', function() {
            performMaintenanceAction('update-api', 'Обновление данных API');
        });
    }
    
    if (cleanLogsButton) {
        cleanLogsButton.addEventListener('click', function() {
            performMaintenanceAction('clean-logs', 'Очистка логов');
        });
    }
    
    if (restartBotButton) {
        restartBotButton.addEventListener('click', function() {
            if (confirm('Вы уверены, что хотите перезапустить бота?')) {
                performMaintenanceAction('restart', 'Перезапуск бота');
            }
        });
    }
    
    // Функция для выполнения операций обслуживания
    function performMaintenanceAction(action, actionName) {
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
            
            // Добавляем стили для контейнера
            notificationContainer.style.position = 'fixed';
            notificationContainer.style.top = '20px';
            notificationContainer.style.right = '20px';
            notificationContainer.style.zIndex = '9999';
        }
        
        // Создаем элемент уведомления
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        // Добавляем стили для уведомления
        notification.style.backgroundColor = type === 'success' ? '#4CAF50' : type === 'error' ? '#F44336' : '#2196F3';
        notification.style.color = 'white';
        notification.style.padding = '10px 15px';
        notification.style.margin = '5px 0';
        notification.style.borderRadius = '4px';
        notification.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
        notification.style.position = 'relative';
        
        // Добавляем уведомление в контейнер
        notificationContainer.appendChild(notification);
        
        // Автоматически удаляем уведомление через 3 секунды
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.5s';
            
            setTimeout(() => {
                notificationContainer.removeChild(notification);
                
                // Удаляем контейнер, если больше нет уведомлений
                if (notificationContainer.childNodes.length === 0) {
                    document.body.removeChild(notificationContainer);
                }
            }, 500);
        }, 3000);
    }
});
