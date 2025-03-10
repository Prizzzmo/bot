
// Initialize Telegram WebApp
const tgApp = window.Telegram.WebApp;
tgApp.expand();

// Apply Telegram theme
document.documentElement.className = tgApp.colorScheme === 'dark' ? 'dark-theme' : '';

// Функции для административной панели
let isAdminAuthenticated = false;

// Initialize map variables
let map;
let markers = [];
let markerCluster;
let historicalEvents = [];
let filteredEvents = [];

// DOM Elements
const categoryFilter = document.getElementById('category-filter');
const centuryFilter = document.getElementById('century-filter');
const resetFiltersBtn = document.getElementById('reset-filters');
const eventDetails = document.getElementById('event-details');
const closeDetailsBtn = document.getElementById('close-details');
const eventTitle = document.getElementById('event-title');
const eventDate = document.getElementById('event-date');
const eventCategory = document.getElementById('event-category');
const eventDescription = document.getElementById('event-description');

// Initialize map
function initMap() {
    // Create map centered at Russia
    map = L.map('map').setView([61.5240, 105.3188], 4);

    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Initialize marker cluster group
    markerCluster = L.markerClusterGroup();
    map.addLayer(markerCluster);
    
    // Load historical data
    loadHistoricalData();
}

// Load historical data from JSON file
async function loadHistoricalData() {
    try {
        const response = await fetch('/api/historical-events');
        historicalEvents = await response.json();
        
        // Process events
        processEvents(historicalEvents);
        
        // Initialize filters
        initializeFilters();
        
        // Apply default filters
        applyFilters();
    } catch (error) {
        console.error('Error loading historical data:', error);
        alert('Не удалось загрузить исторические данные');
    }
}

// Process events data
function processEvents(events) {
    // Filter out events without proper location data
    return events.filter(event => {
        return event.location && 
               (typeof event.location === 'object' && event.location.lat && event.location.lng) || 
               (typeof event.location === 'string');
    });
}

// Initialize filter options based on data
function initializeFilters() {
    // Get unique categories
    const categories = [...new Set(historicalEvents.map(event => event.category))].sort();
    
    // Populate category filter
    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        categoryFilter.appendChild(option);
    });
    
    // Get century ranges from dates
    const centuries = new Set();
    historicalEvents.forEach(event => {
        const year = extractYearFromDate(event.date);
        if (year) {
            const century = Math.ceil(year / 100);
            centuries.add(century);
        }
    });
    
    // Populate century filter
    Array.from(centuries).sort((a, b) => a - b).forEach(century => {
        const option = document.createElement('option');
        option.value = century;
        option.textContent = `${century} век`;
        centuryFilter.appendChild(option);
    });
}

// Extract year from various date formats
function extractYearFromDate(dateStr) {
    if (!dateStr) return null;
    
    // Try extracting 4-digit year
    const yearMatch = dateStr.match(/\b(\d{3,4})\b/);
    if (yearMatch) {
        return parseInt(yearMatch[1]);
    }
    
    return null;
}

// Apply filters to events
function applyFilters() {
    const selectedCategory = categoryFilter.value;
    const selectedCentury = centuryFilter.value;
    
    // Filter events based on selections
    filteredEvents = historicalEvents.filter(event => {
        // Category filter
        if (selectedCategory !== 'all' && event.category !== selectedCategory) {
            return false;
        }
        
        // Century filter
        if (selectedCentury !== 'all') {
            const year = extractYearFromDate(event.date);
            if (!year || Math.ceil(year / 100) != selectedCentury) {
                return false;
            }
        }
        
        return true;
    });
    
    // Update markers
    updateMarkers();
}

// Update map markers based on filtered events
function updateMarkers() {
    // Clear existing markers
    markerCluster.clearLayers();
    markers = [];
    
    // Add new markers
    filteredEvents.forEach(event => {
        let lat, lng;
        
        if (typeof event.location === 'object' && event.location.lat && event.location.lng) {
            lat = event.location.lat;
            lng = event.location.lng;
        } else if (typeof event.location === 'string') {
            // Skip events with string locations that don't have coordinates
            return;
        }
        
        // Skip if coordinates are invalid
        if (isNaN(lat) || isNaN(lng) || !isFinite(lat) || !isFinite(lng)) {
            return;
        }
        
        // Create marker
        const marker = L.marker([lat, lng]);
        
        // Add popup with basic info
        marker.bindPopup(`<b>${event.title}</b><br>${event.date}`);
        
        // Add click handler for detailed view
        marker.on('click', () => showEventDetails(event));
        
        // Add to marker cluster
        markerCluster.addLayer(marker);
        markers.push(marker);
    });
    
    // If there are markers, fit bounds to show all markers
    if (markers.length > 0) {
        const group = L.featureGroup(markers);
        map.fitBounds(group.getBounds(), { padding: [30, 30] });
    }
}

// Show detailed event information
function showEventDetails(event) {
    eventTitle.textContent = event.title;
    eventDate.textContent = event.date;
    eventCategory.textContent = event.category;
    eventDescription.textContent = event.description;
    eventDetails.classList.remove('hidden');
}

// Event Listeners
categoryFilter.addEventListener('change', applyFilters);
centuryFilter.addEventListener('change', applyFilters);
resetFiltersBtn.addEventListener('click', () => {
    categoryFilter.value = 'all';
    centuryFilter.value = 'all';
    applyFilters();
});
closeDetailsBtn.addEventListener('click', () => {
    eventDetails.classList.add('hidden');
});

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    initAdminPanel();
});

// Инициализация админ-панели
function initAdminPanel() {
    const adminButton = document.getElementById('admin-button');
    const adminPanel = document.getElementById('admin-panel');
    const closeAdminPanel = document.getElementById('close-admin-panel');
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Привязка событий для кнопок вкладок
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Убираем активный класс со всех кнопок и содержимого вкладок
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));
            
            // Добавляем активный класс нажатой кнопке
            button.classList.add('active');
            
            // Отображаем содержимое выбранной вкладки
            const tabId = button.getAttribute('data-tab');
            document.getElementById(`${tabId}-tab`).classList.add('active');
            
            // Загружаем данные при переключении на вкладку
            loadTabData(tabId);
        });
    });
    
    // Открытие админ-панели
    adminButton.addEventListener('click', () => {
        adminPanel.classList.remove('hidden');
        // Загружаем данные активной вкладки
        const activeTab = document.querySelector('.tab-button.active');
        if (activeTab) {
            loadTabData(activeTab.getAttribute('data-tab'));
        } else {
            // По умолчанию загружаем статистику
            loadTabData('stats');
        }
    });
    
    // Закрытие админ-панели
    closeAdminPanel.addEventListener('click', () => {
        adminPanel.classList.add('hidden');
    });
    
    // Привязка событий для кнопок в админ-панели
    document.getElementById('refresh-stats').addEventListener('click', () => loadTabData('stats'));
    document.getElementById('show-user-stats').addEventListener('click', loadUserStats);
    document.getElementById('show-system-info').addEventListener('click', loadSystemInfo);
    
    document.getElementById('add-regular-admin').addEventListener('click', () => addAdmin(false));
    document.getElementById('add-super-admin').addEventListener('click', () => addAdmin(true));
    document.getElementById('refresh-admins').addEventListener('click', () => loadTabData('admins'));
    
    document.getElementById('refresh-logs').addEventListener('click', refreshLogs);
    document.getElementById('clear-logs').addEventListener('click', clearLogs);
    document.getElementById('logs-level').addEventListener('change', refreshLogs);
    
    document.getElementById('save-settings').addEventListener('click', saveSettings);
    document.getElementById('reset-settings').addEventListener('click', () => loadTabData('settings'));
    
    document.getElementById('clear-cache').addEventListener('click', clearCache);
    document.getElementById('create-backup').addEventListener('click', createBackup);
    document.getElementById('update-api').addEventListener('click', updateApiData);
    document.getElementById('restart-bot').addEventListener('click', confirmRestartBot);
}

// Загрузка данных для активной вкладки
function loadTabData(tabId) {
    switch (tabId) {
        case 'stats':
            loadStats();
            break;
        case 'admins':
            loadAdmins();
            break;
        case 'logs':
            loadLogs();
            break;
        case 'settings':
            loadSettings();
            break;
        // Для вкладки maintenance не требуется предварительная загрузка данных
    }
}

// Функции для вкладки статистики
function loadStats() {
    const statsContent = document.getElementById('stats-content');
    statsContent.innerHTML = '<p>Загрузка статистики...</p>';
    
    fetch('/api/admin/stats')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                statsContent.innerHTML = `<p class="error">Ошибка: ${data.error}</p>`;
                return;
            }
            
            statsContent.innerHTML = `
                <div class="stats-box">
                    <h4>Общая статистика</h4>
                    <p>👥 Уникальных пользователей: ${data.user_count}</p>
                    <p>💬 Всего сообщений: ${data.message_count}</p>
                    <p>⏱️ Время работы: ${data.uptime}</p>
                </div>
                
                <div class="stats-box">
                    <h4>Активность за последние 24 часа</h4>
                    <p>🔄 Запусков бота: ${data.bot_starts}</p>
                    <p>📝 Запросов тем: ${data.topic_requests}</p>
                    <p>✅ Пройдено тестов: ${data.completed_tests}</p>
                </div>
            `;
        })
        .catch(error => {
            statsContent.innerHTML = `<p class="error">Ошибка загрузки статистики: ${error.message}</p>`;
        });
}

function loadUserStats() {
    const statsContent = document.getElementById('stats-content');
    statsContent.innerHTML = '<p>Загрузка подробной статистики пользователей...</p>';
    
    fetch('/api/admin/user-stats')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                statsContent.innerHTML = `<p class="error">Ошибка: ${data.error}</p>`;
                return;
            }
            
            let daysStats = '';
            data.daily_users.days.forEach((day, index) => {
                daysStats += `<p>${day}: ${data.daily_users.counts[index]} пользователей</p>`;
            });
            
            let hoursStats = '';
            data.hourly_users.hours.forEach((hour, index) => {
                hoursStats += `<p>${hour}: ${data.hourly_users.counts[index]} пользователей</p>`;
            });
            
            statsContent.innerHTML = `
                <div class="stats-box">
                    <h4>Активность по дням недели</h4>
                    ${daysStats}
                </div>
                
                <div class="stats-box">
                    <h4>Активность по времени суток</h4>
                    ${hoursStats}
                </div>
                
                <div class="stats-box">
                    <h4>Статистика тестов</h4>
                    <p>Средний балл: ${data.test_stats.avg_score}%</p>
                    <p>Пройдено тестов: ${data.test_stats.completed_tests}</p>
                    <p>Не завершено: ${data.test_stats.abandoned_tests}</p>
                </div>
                
                <button id="back-to-stats" class="back-button">Вернуться к общей статистике</button>
            `;
            
            document.getElementById('back-to-stats').addEventListener('click', loadStats);
        })
        .catch(error => {
            statsContent.innerHTML = `<p class="error">Ошибка загрузки подробной статистики: ${error.message}</p>`;
        });
}

function loadSystemInfo() {
    const statsContent = document.getElementById('stats-content');
    statsContent.innerHTML = '<p>Загрузка информации о системе...</p>';
    
    fetch('/api/admin/system-info')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                statsContent.innerHTML = `<p class="error">Ошибка: ${data.error}</p>`;
                return;
            }
            
            let processesInfo = '';
            if (data.python_processes && data.python_processes.length > 0) {
                data.python_processes.forEach((proc, index) => {
                    processesInfo += `<p>${index + 1}. PID: ${proc.pid}, Память: ${proc.memory_mb} МБ (${proc.memory_percent.toFixed(2)}%)</p>`;
                });
            } else {
                processesInfo = '<p>Нет активных Python процессов</p>';
            }
            
            statsContent.innerHTML = `
                <div class="stats-box">
                    <h4>Процессор</h4>
                    <p>Загрузка CPU: ${data.cpu.percent}%</p>
                </div>
                
                <div class="stats-box">
                    <h4>Память</h4>
                    <p>Всего: ${data.memory.total_gb} ГБ</p>
                    <p>Используется: ${data.memory.used_gb} ГБ (${data.memory.percent}%)</p>
                    <p>Свободно: ${data.memory.free_gb} ГБ</p>
                </div>
                
                <div class="stats-box">
                    <h4>Диск</h4>
                    <p>Всего: ${data.disk.total_gb} ГБ</p>
                    <p>Используется: ${data.disk.used_gb} ГБ (${data.disk.percent}%)</p>
                    <p>Свободно: ${data.disk.free_gb} ГБ</p>
                </div>
                
                <div class="stats-box">
                    <h4>Python процессы (топ 5)</h4>
                    ${processesInfo}
                </div>
                
                <button id="back-to-stats" class="back-button">Вернуться к общей статистике</button>
            `;
            
            document.getElementById('back-to-stats').addEventListener('click', loadStats);
        })
        .catch(error => {
            statsContent.innerHTML = `<p class="error">Ошибка загрузки информации о системе: ${error.message}</p>`;
        });
}

// Функции для вкладки управления администраторами
function loadAdmins() {
    const adminsContent = document.getElementById('admins-content');
    adminsContent.innerHTML = '<p>Загрузка списка администраторов...</p>';
    
    fetch('/api/admin/admins')
        .then(response => response.json())
        .then(data => {
            let adminsList = '';
            
            if (data.super_admin_ids && data.super_admin_ids.length > 0) {
                adminsList += '<h4>Супер-администраторы:</h4><ul>';
                data.super_admin_ids.forEach((adminId, index) => {
                    adminsList += `<li>
                        ID: ${adminId} 
                        <button class="remove-admin-btn" data-id="${adminId}">Удалить</button>
                    </li>`;
                });
                adminsList += '</ul>';
            } else {
                adminsList += '<h4>Супер-администраторы:</h4><p>Нет супер-администраторов</p>';
            }
            
            if (data.admin_ids && data.admin_ids.length > 0) {
                adminsList += '<h4>Администраторы:</h4><ul>';
                data.admin_ids.forEach((adminId, index) => {
                    adminsList += `<li>
                        ID: ${adminId} 
                        <button class="remove-admin-btn" data-id="${adminId}">Удалить</button>
                    </li>`;
                });
                adminsList += '</ul>';
            } else {
                adminsList += '<h4>Администраторы:</h4><p>Нет администраторов</p>';
            }
            
            adminsContent.innerHTML = adminsList;
            
            // Добавляем обработчики событий для кнопок удаления
            document.querySelectorAll('.remove-admin-btn').forEach(button => {
                button.addEventListener('click', function() {
                    const adminId = this.getAttribute('data-id');
                    removeAdmin(adminId);
                });
            });
        })
        .catch(error => {
            adminsContent.innerHTML = `<p class="error">Ошибка загрузки списка администраторов: ${error.message}</p>`;
        });
}

function addAdmin(isSuper) {
    const adminIdInput = document.getElementById('new-admin-id');
    const adminId = Number(adminIdInput.value.trim());
    
    if (!adminId || isNaN(adminId)) {
        alert('Пожалуйста, введите корректный ID пользователя');
        return;
    }
    
    fetch('/api/admin/admins', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: 'add',
            user_id: adminId,
            is_super: isSuper
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(`Ошибка: ${data.error}`);
            return;
        }
        
        alert(`${isSuper ? 'Супер-а' : 'А'}дминистратор успешно добавлен!`);
        adminIdInput.value = '';
        loadAdmins();
    })
    .catch(error => {
        alert(`Ошибка при добавлении администратора: ${error.message}`);
    });
}

function removeAdmin(adminId) {
    if (!confirm(`Вы уверены, что хотите удалить администратора с ID ${adminId}?`)) {
        return;
    }
    
    fetch('/api/admin/admins', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            action: 'remove',
            user_id: Number(adminId)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(`Ошибка: ${data.error}`);
            return;
        }
        
        alert('Администратор успешно удален!');
        loadAdmins();
    })
    .catch(error => {
        alert(`Ошибка при удалении администратора: ${error.message}`);
    });
}

// Функции для вкладки логов
function loadLogs() {
    const level = document.getElementById('logs-level').value;
    refreshLogs();
}

function refreshLogs() {
    const logsContent = document.getElementById('logs-content');
    logsContent.innerHTML = '<p>Загрузка логов...</p>';
    
    const level = document.getElementById('logs-level').value;
    
    fetch(`/api/admin/logs?level=${level}&limit=100`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                logsContent.innerHTML = `<p class="error">Ошибка: ${data.error}</p>`;
                return;
            }
            
            if (!data.logs || data.logs.length === 0) {
                logsContent.innerHTML = '<p>Логи отсутствуют</p>';
                return;
            }
            
            logsContent.innerHTML = '';
            data.logs.forEach(log => {
                const logLine = document.createElement('div');
                logLine.className = 'log-line';
                
                // Выделяем цветом уровни логирования
                if (log.includes(' - ERROR - ')) {
                    logLine.classList.add('log-error');
                } else if (log.includes(' - WARNING - ')) {
                    logLine.classList.add('log-warning');
                } else if (log.includes(' - INFO - ')) {
                    logLine.classList.add('log-info');
                } else if (log.includes(' - DEBUG - ')) {
                    logLine.classList.add('log-debug');
                }
                
                logLine.textContent = log;
                logsContent.appendChild(logLine);
            });
        })
        .catch(error => {
            logsContent.innerHTML = `<p class="error">Ошибка загрузки логов: ${error.message}</p>`;
        });
}

function clearLogs() {
    if (!confirm('Вы уверены, что хотите очистить старые лог-файлы? Это действие нельзя отменить.')) {
        return;
    }
    
    fetch('/api/admin/clean-logs', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(`Ошибка: ${data.error}`);
            return;
        }
        
        let message = 'Очистка логов завершена. ';
        
        if (data.deleted_count > 0) {
            message += `Удалено ${data.deleted_count} старых лог-файлов. `;
        } else {
            message += 'Не найдено старых лог-файлов для удаления. ';
        }
        
        if (data.truncated) {
            message += 'Текущий лог-файл был усечен из-за большого размера.';
        }
        
        alert(message);
        refreshLogs();
    })
    .catch(error => {
        alert(`Ошибка при очистке логов: ${error.message}`);
    });
}

// Функции для вкладки настроек
function loadSettings() {
    fetch('/api/admin/settings')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(`Ошибка загрузки настроек: ${data.error}`);
                return;
            }
            
            document.getElementById('setting-auto-update').checked = data.auto_update_topics;
            document.getElementById('setting-statistics').checked = data.collect_statistics;
            document.getElementById('setting-dev-mode').checked = data.developer_mode;
            document.getElementById('setting-private-mode').checked = data.private_mode;
            document.getElementById('setting-notifications').checked = data.notification_enabled;
            
            const logLevelSelect = document.getElementById('setting-log-level');
            for (let i = 0; i < logLevelSelect.options.length; i++) {
                if (logLevelSelect.options[i].value === data.log_level) {
                    logLevelSelect.selectedIndex = i;
                    break;
                }
            }
            
            document.getElementById('setting-max-messages').value = data.max_messages_per_user;
        })
        .catch(error => {
            alert(`Ошибка загрузки настроек: ${error.message}`);
        });
}

function saveSettings() {
    const settings = {
        auto_update_topics: document.getElementById('setting-auto-update').checked,
        collect_statistics: document.getElementById('setting-statistics').checked,
        developer_mode: document.getElementById('setting-dev-mode').checked,
        private_mode: document.getElementById('setting-private-mode').checked,
        notification_enabled: document.getElementById('setting-notifications').checked,
        log_level: document.getElementById('setting-log-level').value,
        max_messages_per_user: Number(document.getElementById('setting-max-messages').value)
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
            alert(`Ошибка: ${data.error}`);
            return;
        }
        
        alert('Настройки успешно сохранены!');
    })
    .catch(error => {
        alert(`Ошибка при сохранении настроек: ${error.message}`);
    });
}

// Функции для вкладки технического обслуживания
function clearCache() {
    if (!confirm('Вы уверены, что хотите очистить кэш API? Это может временно снизить производительность бота.')) {
        return;
    }
    
    fetch('/api/admin/clear-cache', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(`Ошибка: ${data.error}`);
            return;
        }
        
        if (data.cache_cleared) {
            alert('Кэш API успешно очищен!');
        } else {
            alert('Файл кэша API не найден или не может быть удален.');
        }
    })
    .catch(error => {
        alert(`Ошибка при очистке кэша: ${error.message}`);
    });
}

function createBackup() {
    fetch('/api/admin/backup', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(`Ошибка: ${data.error}`);
            return;
        }
        
        if (data.backup_files && data.backup_files.length > 0) {
            let message = 'Резервное копирование завершено. Созданы следующие резервные копии:\n\n';
            
            data.backup_files.forEach(file => {
                message += `• ${file.original} → ${file.backup}\n`;
            });
            
            alert(message);
        } else {
            alert('Не удалось создать ни одной резервной копии.');
        }
    })
    .catch(error => {
        alert(`Ошибка при создании резервной копии: ${error.message}`);
    });
}

function updateApiData() {
    alert('Функция обновления данных API временно недоступна в веб-интерфейсе.');
}

function confirmRestartBot() {
    if (confirm('Вы уверены, что хотите перезапустить бота? Это приведет к кратковременной недоступности сервиса.')) {
        fetch('/api/admin/restart', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(`Ошибка: ${data.error}`);
                return;
            }
            
            alert('Команда на перезапуск бота отправлена. Бот будет перезапущен в течение нескольких секунд.');
        })
        .catch(error => {
            alert(`Ошибка при перезапуске бота: ${error.message}`);
        });
    }
}

// Функция для отображения модального окна
function showModal(title, message, confirmCallback) {
    // Проверяем, существует ли уже модальное окно
    let modalOverlay = document.querySelector('.modal-overlay');
    
    if (!modalOverlay) {
        // Создаем элементы модального окна
        modalOverlay = document.createElement('div');
        modalOverlay.className = 'modal-overlay';
        
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-content';
        
        const modalTitle = document.createElement('h3');
        modalTitle.textContent = title;
        
        const modalMessage = document.createElement('p');
        modalMessage.textContent = message;
        
        const modalButtons = document.createElement('div');
        modalButtons.className = 'modal-buttons';
        
        const confirmButton = document.createElement('button');
        confirmButton.className = 'confirm';
        confirmButton.textContent = 'Подтвердить';
        confirmButton.addEventListener('click', () => {
            confirmCallback();
            document.body.removeChild(modalOverlay);
        });
        
        const cancelButton = document.createElement('button');
        cancelButton.className = 'cancel';
        cancelButton.textContent = 'Отмена';
        cancelButton.addEventListener('click', () => {
            document.body.removeChild(modalOverlay);
        });
        
        modalButtons.appendChild(cancelButton);
        modalButtons.appendChild(confirmButton);
        
        modalContent.appendChild(modalTitle);
        modalContent.appendChild(modalMessage);
        modalContent.appendChild(modalButtons);
        
        modalOverlay.appendChild(modalContent);
        
        document.body.appendChild(modalOverlay);
    } else {
        // Обновляем содержимое существующего модального окна
        const modalTitle = modalOverlay.querySelector('h3');
        modalTitle.textContent = title;
        
        const modalMessage = modalOverlay.querySelector('p');
        modalMessage.textContent = message;
        
        const confirmButton = modalOverlay.querySelector('.confirm');
        confirmButton.onclick = () => {
            confirmCallback();
            document.body.removeChild(modalOverlay);
        };
    }
}
