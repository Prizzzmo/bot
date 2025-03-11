/**
 * JavaScript для функциональности панели администратора
 */

document.addEventListener('DOMContentLoaded', function() {
    // Глобальные переменные
    let adminId = null;
    let isSuperAdmin = false;
    let currentPage = 'dashboard';
    let darkMode = localStorage.getItem('dark_mode') === 'true';
    let autoRefreshEnabled = localStorage.getItem('auto_refresh') === 'true' || true;
    let autoRefreshInterval = null;
    let autoRefreshTime = 60000; // 60 секунд

    // Инициализация состояния темы
    if (darkMode) {
        document.body.classList.add('dark-theme');
        document.getElementById('theme-toggle').innerHTML = '<i class="fas fa-sun"></i>';
    }

    // Проверка авторизации при загрузке страницы
    checkAuth();

    // Установка обработчиков событий
    setupEventListeners();

    // Инициализация обновления данных
    setupAutoRefresh();

    /**
     * Проверка авторизации пользователя
     */
    async function checkAuth() {
        try {
            const response = await fetch('/api/admin/check-auth');
            const data = await response.json();

            if (data.authenticated) {
                // Пользователь авторизован, показываем интерфейс админа
                document.getElementById('login-container').style.display = 'none';
                document.getElementById('admin-panel').style.display = 'block';

                // Сохраняем информацию о пользователе
                currentUser = data.user;

                // Если пользователь не супер-админ, скрываем некоторые функции
                if (!currentUser.is_super_admin) {
                    document.querySelectorAll('.super-admin-only').forEach(el => {
                        el.style.display = 'none';
                    });
                }

                // Выводим информацию о текущем пользователе
                if (document.getElementById('current-user-info')) {
                    document.getElementById('current-user-info').textContent = `ID: ${currentUser.id}`;
                }

                // Загружаем данные для админ-панели
                loadAdminData();
            } else {
                // Пользователь не авторизован, показываем форму входа
                document.getElementById('login-container').style.display = 'flex';
                document.getElementById('admin-panel').style.display = 'none';
            }
        } catch (error) {
            console.error('Ошибка при проверке авторизации:', error);
            showMessage('error', 'Ошибка при проверке авторизации');

            // Показываем форму входа при ошибке
            document.getElementById('login-container').style.display = 'flex';
            document.getElementById('admin-panel').style.display = 'none';
        }
    }


    /**
     * Отображение формы входа
     */
    function showLoginForm() {
        // Создаем модальное окно для входа
        const modalContent = `
            <div class="modal-header">
                <h2><i class="fas fa-lock"></i> Вход в панель администратора</h2>
                <button class="modal-close" id="login-modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <form id="login-form" class="login-form">
                    <div class="login-tabs">
                        <button type="button" class="login-tab active" data-tab="admin-id">Вход по ID</button>
                        <button type="button" class="login-tab" data-tab="admin-password">Вход по паролю</button>
                    </div>

                    <div class="login-tab-content active" id="admin-id-tab">
                        <div class="form-group">
                            <label for="admin-id">ID администратора</label>
                            <input type="number" id="admin-id" placeholder="Введите ваш ID" required>
                            <small class="form-help">Введите ID администратора из Telegram</small>
                        </div>
                    </div>

                    <div class="login-tab-content" id="admin-password-tab">
                        <div class="form-group">
                            <label for="admin-password">Пароль администратора</label>
                            <input type="password" id="admin-password" placeholder="Введите пароль" required>
                            <small class="form-help">Введите пароль (для супер-администратора)</small>
                        </div>
                    </div>

                    <div class="login-status" id="login-status"></div>

                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary login-btn">
                            <i class="fas fa-sign-in-alt"></i> Войти
                        </button>
                    </div>
                </form>
            </div>
        `;

        // Отображаем модальное окно
        const modalOverlay = document.getElementById('modal-overlay');
        const modalContainer = document.getElementById('modal-container');

        modalContainer.innerHTML = modalContent;
        modalOverlay.classList.add('active');

        // Настраиваем переключение вкладок
        const loginTabs = document.querySelectorAll('.login-tab');
        loginTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                // Удаляем активный класс у всех вкладок
                loginTabs.forEach(t => t.classList.remove('active'));
                // Скрываем все содержимое вкладок
                document.querySelectorAll('.login-tab-content').forEach(c => c.classList.remove('active'));

                // Добавляем активный класс выбранной вкладке
                this.classList.add('active');
                // Показываем содержимое выбранной вкладки
                document.getElementById(`${this.dataset.tab}-tab`).classList.add('active');

                // Очищаем статус логина при переключении вкладок
                document.getElementById('login-status').innerHTML = '';
            });
        });

        // Обработчик для закрытия модального окна
        document.getElementById('login-modal-close').addEventListener('click', function() {
            modalOverlay.classList.remove('active');
        });

        // Обработчик отправки формы логина
        const loginForm = document.getElementById('login-form');
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const activeTab = document.querySelector('.login-tab.active').dataset.tab;
            let loginData = {};

            if (activeTab === 'admin-id') {
                const adminIdInput = document.getElementById('admin-id');
                const adminId = adminIdInput.value.trim();

                if (!adminId) {
                    document.getElementById('login-status').innerHTML = '<div class="error-message">Введите ID администратора</div>';
                    adminIdInput.focus();
                    return;
                }

                loginData = { admin_id: parseInt(adminId) };
                console.log('Отправка данных для входа по ID:', loginData);
            } else {
                const adminPasswordInput = document.getElementById('admin-password');
                const adminPassword = adminPasswordInput.value.trim();

                if (!adminPassword) {
                    document.getElementById('login-status').innerHTML = '<div class="error-message">Введите пароль</div>';
                    adminPasswordInput.focus();
                    return;
                }

                loginData = { admin_password: adminPassword };
                console.log('Отправка данных для входа по паролю:', loginData);
            }

            // Отправляем запрос на авторизацию
            await loginUser(loginData);
        });

        // Фокус на первом поле ввода
        document.getElementById('admin-id').focus();
    }

    /**
     * Авторизация пользователя
     */
    async function loginUser(loginData) {
        // Показываем индикатор загрузки
        const loginBtn = document.querySelector('.login-btn');
        const originalText = loginBtn.innerHTML;
        loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Вход...';
        loginBtn.disabled = true;

        console.log('Отправка данных для авторизации:', loginData);

        try {
            const response = await fetch('/api/admin/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(loginData)
            });
            const data = await response.json();
            console.log('Данные авторизации:', data);

            // Восстанавливаем кнопку
            loginBtn.innerHTML = originalText;
            loginBtn.disabled = false;

            if (data.success) {
                console.log('Успешная авторизация. ID:', data.user.id);

                // Закрываем модальное окно
                document.getElementById('modal-overlay').classList.remove('active');

                // Обновляем данные пользователя
                adminId = data.user.id;
                isSuperAdmin = data.user.is_super_admin;

                // Обновляем интерфейс
                document.getElementById('user-name').textContent = `ID: ${adminId}`;
                document.getElementById('user-role').textContent = isSuperAdmin ? 'Супер-администратор' : 'Администратор';

                // Скрытие элементов для не-супер-админов
                if (!isSuperAdmin) {
                    document.querySelectorAll('.super-admin-only').forEach(el => {
                        el.style.display = 'none';
                    });
                } else {
                    document.querySelectorAll('.super-admin-only').forEach(el => {
                        el.style.display = '';
                    });
                }

                // Загружаем данные панели с небольшой задержкой для завершения авторизации
                setTimeout(() => {
                    loadDashboardData();
                }, 300);

                showNotification('Вы успешно вошли в систему', 'success');
            } else {
                showNotification(data.message || 'Ошибка при входе', 'error');
                console.error('Ошибка авторизации:', data.message);
            }
        } catch (error) {
            console.error('Ошибка при входе:', error);
            showNotification('Ошибка при входе в систему', 'error');

            // Восстанавливаем кнопку
            loginBtn.innerHTML = originalText;
            loginBtn.disabled = false;
        }
    }

    /**
     * Выход пользователя
     */
    function logoutUser() {
        fetch('/api/admin/logout', {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Сбрасываем данные пользователя
                adminId = null;
                isSuperAdmin = false;

                // Показываем форму входа
                showLoginForm();

                showNotification('Вы успешно вышли из системы', 'info');
            }
        })
        .catch(error => {
            console.error('Ошибка при выходе:', error);
            showNotification('Ошибка при выходе из системы', 'error');
        });
    }

    /**
     * Загрузка данных для страницы обзора
     */
    function loadDashboardData() {
        // Загружаем общую статистику
        fetch('/api/admin/stats')
            .then(response => response.json())
            .then(data => {
                // Обновляем счетчики
                document.getElementById('user-count').textContent = data.user_count || 0;
                document.getElementById('message-count').textContent = data.message_count || 0;
                document.getElementById('events-count').textContent = data.completed_tests || 0;
                document.getElementById('uptime').textContent = data.uptime || '00:00:00';

                // Обновляем изменения (простой плюсовый процент для примера)
                document.getElementById('user-change').textContent = '+5%';
                document.getElementById('message-change').textContent = '+12%';
                document.getElementById('events-change').textContent = '+3%';

                // Обновляем статистику запросов
                const queryStats = document.querySelectorAll('#queries-stats .stat-value');
                queryStats[0].textContent = data.bot_starts || 0;
                queryStats[1].textContent = data.topic_requests || 0;
                queryStats[2].textContent = Math.round((data.topic_requests || 0) / 60) || 0;
                queryStats[3].textContent = '250 мс';

                // Обновляем список последних действий
                updateRecentActivities();

                // Обновляем системную информацию
                const sysInfo = document.querySelectorAll('#system-info .info-value');
                sysInfo[1].textContent = 'Активны';
                sysInfo[2].textContent = '250 МБ';
                sysInfo[3].textContent = 'Только что';

                // Обновляем график активности
                document.getElementById('activity-chart').src = `/api/chart/daily_activity?t=${new Date().getTime()}`;
            })
            .catch(error => {
                console.error('Ошибка при загрузке статистики:', error);
                showNotification('Ошибка при загрузке статистики', 'error');
            });
    }

    /**
     * Обновление списка последних действий
     */
    function updateRecentActivities() {
        // Пример данных о последних действиях
        const activities = [
            { time: '12:45', action: 'Пользователь ID: 123456 запросил тему "Великая Отечественная война"' },
            { time: '12:30', action: 'Пользователь ID: 789012 выполнил тест по теме "Древняя Русь"' },
            { time: '11:15', action: 'Администратор добавил новое событие в базу данных' },
            { time: '10:20', action: 'Система выполнила плановое резервное копирование' },
            { time: '09:05', action: 'Пользователь ID: 456789 задал вопрос о периоде правления Екатерины II' }
        ];

        // Формируем HTML для списка действий
        let activitiesHTML = '';
        activities.forEach(activity => {
            activitiesHTML += `
                <li class="activity-item">
                    <div class="activity-time">${activity.time}</div>
                    <div class="activity-description">${activity.description || activity.action}</div>
                </li>
            `;
        });

        // Обновляем список в DOM
        const activitiesList = document.getElementById('recent-activities');
        if (activitiesList) {
            activitiesList.innerHTML = activitiesHTML;
        }
    }

    /**
     * Загрузка списка администраторов
     */
    function loadAdminsList() {
        fetch('/api/admin/admins')
            .then(response => response.json())
            .then(data => {
                // Обновляем списки администраторов
                const superAdminList = document.getElementById('super-admin-list');
                const adminList = document.getElementById('admin-list');
                const adminToRemove = document.getElementById('admin-to-remove');

                if (superAdminList && adminList) {
                    // Очищаем текущие списки
                    superAdminList.innerHTML = '';
                    adminList.innerHTML = '';

                    if (adminToRemove) {
                        // Очищаем и добавляем пустое значение
                        adminToRemove.innerHTML = '<option value="">Выберите администратора</option>';
                    }

                    // Заполняем списки
                    data.admins.forEach(admin => {
                        const adminItem = `
                            <li class="admin-item">
                                <div class="admin-info">
                                    <div class="admin-avatar">
                                        <i class="fas fa-user-shield"></i>
                                    </div>
                                    <div class="admin-details">
                                        <div class="admin-id">${admin.id}</div>
                                        <div class="admin-type">${admin.type}</div>
                                    </div>
                                </div>
                            </li>
                        `;

                        if (admin.is_super) {
                            superAdminList.innerHTML += adminItem;

                            // Добавляем в выпадающий список для удаления, если это не текущий пользователь
                            if (adminToRemove && admin.id !== adminId) {
                                adminToRemove.innerHTML += `<option value="${admin.id}">Супер-админ: ${admin.id}</option>`;
                            }
                        } else {
                            adminList.innerHTML += adminItem;

                            // Добавляем в выпадающий список для удаления
                            if (adminToRemove) {
                                adminToRemove.innerHTML += `<option value="${admin.id}">Админ: ${admin.id}</option>`;
                            }
                        }
                    });
                }
            })
            .catch(error => {
                console.error('Ошибка при загрузке списка администраторов:', error);
                showNotification('Ошибка при загрузке списка администраторов', 'error');
            });
    }

    /**
     * Загрузка исторических событий
     */
    function loadHistoricalEvents() {
        // Получаем параметры фильтрации
        const category = document.getElementById('event-category-filter').value;
        const century = document.getElementById('event-century-filter').value;
        const search = document.getElementById('event-search').value;
        const limit = document.getElementById('events-per-page').value;
        const offset = 0; // Для первой страницы

        // Формируем URL с параметрами
        let url = `/api/admin/historical-events?limit=${limit}&offset=${offset}`;
        if (category && category !== 'all') url += `&category=${encodeURIComponent(category)}`;
        if (century && century !== 'all') url += `&century=${encodeURIComponent(century)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        // Загружаем список событий
        fetch(url)
            .then(response => response.json())
            .then(data => {
                // Обновляем таблицу событий
                const eventsTableBody = document.getElementById('events-table-body');
                eventsTableBody.innerHTML = '';

                // Заполняем таблицу
                data.events.forEach(event => {
                    const locationStr = event.location && event.location.lat ? 
                        `${event.location.lat}, ${event.location.lng}` : 'Н/Д';

                    const row = `
                        <tr>
                            <td>${event.id}</td>
                            <td>
                                <div class="event-title">${event.title}</div>
                                <div class="event-description">${event.description.substring(0, 100)}...</div>
                            </td>
                            <td>${event.date}</td>
                            <td>${event.category || 'Н/Д'}</td>
                            <td>${locationStr}</td>
                            <td>
                                <div class="actions">
                                    <button class="btn-icon edit-event" data-id="${event.id}" title="Редактировать">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn-icon delete-event" data-id="${event.id}" title="Удалить">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;

                    eventsTableBody.innerHTML += row;
                });

                // Обновляем пагинацию
                updatePagination(data.total, limit, offset, 'events-pagination');

                // Добавляем обработчики для кнопок редактирования и удаления
                setupEventButtons();
            })
            .catch(error => {
                console.error('Ошибка при загрузке исторических событий:', error);
                showNotification('Ошибка при загрузке исторических событий', 'error');
            });

        // Загружаем список категорий
        fetch('/api/admin/categories')
            .then(response => response.json())
            .then(categories => {
                console.log("Загружено категорий из API:", categories.length);

                // Обновляем выпадающий список категорий
                const categoryFilter = document.getElementById('event-category-filter');

                // Сохраняем текущее значение
                const currentValue = categoryFilter.value;

                // Очищаем список кроме первой опции
                categoryFilter.innerHTML = '<option value="all">Все категории</option>';

                // Заполняем список категориями
                categories.forEach(category => {
                    console.log("Добавлена категория:", category);
                    categoryFilter.innerHTML += `<option value="${category}">${category}</option>`;
                });

                // Восстанавливаем выбранное значение
                categoryFilter.value = currentValue;
            })
            .catch(error => {
                console.error('Ошибка при загрузке категорий:', error);
            });
    }

    /**
     * Загрузка пользователей системы
     */
    function loadUsers() {
        // Получаем параметры фильтрации
        const status = document.getElementById('user-status-filter').value;
        const activity = document.getElementById('user-activity-filter').value;
        const search = document.getElementById('user-search').value;
        const limit = document.getElementById('users-per-page').value;
        const offset = 0; // Для первой страницы

        // Формируем URL с параметрами
        let url = `/api/admin/users?limit=${limit}&offset=${offset}`;
        if (status && status !== 'all') url += `&status=${encodeURIComponent(status)}`;
        if (activity && activity !== 'all') url += `&activity=${encodeURIComponent(activity)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        // Загружаем список пользователей
        fetch(url)
            .then(response => response.json())
            .then(users => {
                // Обновляем таблицу пользователей
                const usersTableBody = document.getElementById('users-table-body');
                usersTableBody.innerHTML = '';

                // Заполняем таблицу
                users.forEach(user => {
                    const statusBadge = `<span class="badge ${user.status}">${getStatusText(user.status)}</span>`;

                    const row = `
                        <tr>
                            <td>${user.id}</td>
                            <td>${user.name || 'Не указано'}</td>
                            <td>${statusBadge}</td>
                            <td>${user.last_activity || 'Не указано'}</td>
                            <td>${user.messages}</td>
                            <td>
                                <div class="actions">
                                    <button class="btn-icon view-user" data-id="${user.id}" title="Просмотр">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                    ${user.status === 'blocked' ? 
                                        `<button class="btn-icon unblock-user" data-id="${user.id}" title="Разблокировать">
                                            <i class="fas fa-unlock"></i>
                                        </button>` : 
                                        `<button class="btn-icon block-user" data-id="${user.id}" title="Заблокировать">
                                            <i class="fas fa-ban"></i>
                                        </button>`
                                    }
                                </div>
                            </td>
                        </tr>
                    `;

                    usersTableBody.innerHTML += row;
                });

                // Добавляем обработчики для кнопок
                setupUserButtons();
            })
            .catch(error => {
                console.error('Ошибка при загрузке списка пользователей:', error);
                showNotification('Ошибка при загрузке списка пользователей', 'error');
            });
    }

    /**
     * Получение текстового представления статуса
     */
    function getStatusText(status) {
        switch(status) {
            case 'active': return 'Активен';
            case 'inactive': return 'Неактивен';
            case 'blocked': return 'Заблокирован';
            default: return 'Неизвестно';
        }
    }

    /**
     * Загрузка логов системы
     */
    function loadLogs() {
        // Получаем параметры
        const level = document.getElementById('log-level').value;
        const component = document.getElementById('log-component').value;
        const limit = document.getElementById('log-limit').value;

        // Формируем URL с параметрами
        let url = `/api/admin/logs?limit=${limit}`;
        if (level && level !== 'all') url += `&level=${encodeURIComponent(level)}`;
        if (component && component !== 'all') url += `&component=${encodeURIComponent(component)}`;

        // Загружаем логи
        fetch(url)
            .then(response => response.json())
            .then(logs => {
                // Обновляем контейнер логов
                const logsContainer = document.getElementById('logs-container');
                logsContainer.innerHTML = '';

                // Заполняем логи с подсветкой уровней
                logs.forEach(log => {
                    // Определяем уровень лога по содержимому строки
                    let logClass = '';
                    if (log.includes(' - ERROR - ')) logClass = 'error';
                    else if (log.includes(' - WARNING - ')) logClass = 'warning';
                    else if (log.includes(' - INFO - ')) logClass = 'info';
                    else if (log.includes(' - DEBUG - ')) logClass = 'debug';

                    // Добавляем строку лога с соответствующим классом
                    logsContainer.innerHTML += `<div class="log-line ${logClass}">${log}</div>`;
                });

                // Обновляем информацию о количестве загруженных строк
                document.getElementById('log-stats').textContent = `Загружено строк: ${logs.length}`;

                // Прокручиваем к концу, если включена автопрокрутка
                if (document.getElementById('auto-scroll').classList.contains('active')) {
                    logsContainer.scrollTop = logsContainer.scrollHeight;
                }
            })
            .catch(error => {
                console.error('Ошибка при загрузке логов:', error);
                showNotification('Ошибка при загрузке логов', 'error');
            });
    }

    /**
     * Загрузка настроек бота
     */
    function loadSettings() {
        fetch('/api/admin/settings')
            .then(response => response.json())
            .then(settings => {
                // Обновляем значения настроек
                document.getElementById('auto-update-topics').checked = settings.auto_update_topics !== false;
                document.getElementById('collect-statistics').checked = settings.collect_statistics !== false;
                document.getElementById('developer-mode').checked = settings.developer_mode === true;
                document.getElementById('private-mode').checked = settings.private_mode === true;

                // Обновляем API настройки
                if (document.getElementById('api-request-limit')) {
                    document.getElementById('api-request-limit').value = settings.api_request_limit || 100;
                    document.getElementById('api-request-limit-range').value = settings.api_request_limit || 100;
                }

                if (document.getElementById('cache-duration')) {
                    document.getElementById('cache-duration').value = settings.cache_duration || 24;
                    document.getElementById('cache-duration-range').value = settings.cache_duration || 24;
                }

                if (document.getElementById('api-model')) {
                    document.getElementById('api-model').value = settings.api_model || 'gemini-pro';
                }

                // Загружаем настройки уведомлений
                if (document.getElementById('notification-level')) {
                    document.getElementById('notification-level').value = settings.notification_level || 'all';
                }

                if (document.getElementById('notification-channel')) {
                    document.getElementById('notification-channel').value = settings.notification_channel || 'telegram';
                }

                if (document.getElementById('notification-schedule')) {
                    document.getElementById('notification-schedule').value = settings.notification_schedule || 'daily';
                }
            })
            .catch(error => {
                console.error('Ошибка при загрузке настроек:', error);
                showNotification('Ошибка при загрузке настроек', 'error');
            });
    }

    /**
     * Обновление пагинации
     */
    function updatePagination(total, limit, offset, paginationId) {
        const pagination = document.getElementById(paginationId);
        if (!pagination) return;

        // Рассчитываем количество страниц
        const pageCount = Math.ceil(total / limit);
        const currentPage = Math.floor(offset / limit) + 1;

        // Создаем пагинацию
        let paginationHTML = '';

        // Кнопка "Предыдущая"
        paginationHTML += `
            <button class="pagination-button ${currentPage === 1 ? 'disabled' : ''}" 
                    data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
                <i class="fas fa-chevron-left"></i>
            </button>
        `;

        // Номера страниц
        const maxVisiblePages = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(pageCount, startPage + maxVisiblePages - 1);

        // Корректируем startPage, если endPage близок к pageCount
        if (endPage === pageCount) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }

        // Добавляем первую страницу и многоточие, если startPage > 1
        if (startPage > 1) {
            paginationHTML += `
                <button class="pagination-button" data-page="1">1</button>
            `;

            if (startPage > 2) {
                paginationHTML += `<span class="pagination-ellipsis">...</span>`;
            }
        }

        // Добавляем номера страниц
        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <button class="pagination-button ${i === currentPage ? 'active' : ''}" 
                        data-page="${i}">
                    ${i}
                </button>
            `;
        }

        // Добавляем многоточие и последнюю страницу, если endPage < pageCount
        if (endPage < pageCount) {
            if (endPage < pageCount - 1) {
                paginationHTML += `<span class="pagination-ellipsis">...</span>`;
            }

            paginationHTML += `
                <button class="pagination-button" data-page="${pageCount}">${pageCount}</button>
            `;
        }

        // Кнопка "Следующая"
        paginationHTML += `
            <button class="pagination-button ${currentPage === pageCount ? 'disabled' : ''}" 
                    data-page="${currentPage + 1}" ${currentPage === pageCount ? 'disabled' : ''}>
                <i class="fas fa-chevron-right"></i>
            </button>
        `;

        // Обновляем DOM
        pagination.innerHTML = paginationHTML;

        // Добавляем обработчики для кнопок пагинации
        pagination.querySelectorAll('.pagination-button').forEach(button => {
            if (!button.disabled) {
                button.addEventListener('click', function() {
                    const page = parseInt(this.dataset.page);
                    // Рассчитываем новый offset
                    const newOffset = (page - 1) * limit;

                    // Загружаем данные для новой страницы
                    if (paginationId === 'events-pagination') {
                        loadHistoricalEventsPage(newOffset);
                    } else if (paginationId === 'users-pagination') {
                        loadUsersPage(newOffset);
                    }
                });
            }
        });
    }

    /**
     * Загрузка страницы исторических событий с указанным смещением
     */
    function loadHistoricalEventsPage(offset) {
        // Получаем параметры фильтрации
        const category = document.getElementById('event-category-filter').value;
        const century = document.getElementById('event-century-filter').value;
        const search = document.getElementById('event-search').value;
        const limit = document.getElementById('events-per-page').value;

        // Формируем URL с параметрами
        let url = `/api/admin/historical-events?limit=${limit}&offset=${offset}`;
        if (category && category !== 'all') url += `&category=${encodeURIComponent(category)}`;
        if (century && century !== 'all') url += `&century=${encodeURIComponent(century)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        // Загружаем список событий
        fetch(url)
            .then(response => response.json())
            .then(data => {
                // Обновляем таблицу событий
                const eventsTableBody = document.getElementById('events-table-body');
                eventsTableBody.innerHTML = '';

                // Заполняем таблицу
                data.events.forEach(event => {
                    const locationStr = event.location && event.location.lat ? 
                        `${event.location.lat}, ${event.location.lng}` : 'Н/Д';

                    const row = `
                        <tr>
                            <td>${event.id}</td>
                            <td>
                                <div class="event-title">${event.title}</div>
                                <div class="event-description">${event.description.substring(0, 100)}...</div>
                            </td>
                            <td>${event.date}</td>
                            <td>${event.category || 'Н/Д'}</td>
                            <td>${locationStr}</td>
                            <td>
                                <div class="actions">
                                    <button class="btn-icon edit-event" data-id="${event.id}" title="Редактировать">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="btn-icon delete-event" data-id="${event.id}" title="Удалить">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </td>
                        </tr>
                    `;

                    eventsTableBody.innerHTML += row;
                });

                // Обновляем пагинацию
                updatePagination(data.total, limit, offset, 'events-pagination');

                // Добавляем обработчики для кнопок редактирования и удаления
                setupEventButtons();
            })
            .catch(error => {
                console.error('Ошибка при загрузке исторических событий:', error);
                showNotification('Ошибка при загрузке исторических событий', 'error');
            });
    }

    /**
     * Загрузка страницы пользователей с указанным смещением
     */
    function loadUsersPage(offset) {
        // Получаем параметры фильтрации
        const status = document.getElementById('user-status-filter').value;
        const activity = document.getElementById('user-activity-filter').value;
        const search = document.getElementById('user-search').value;
        const limit = document.getElementById('users-per-page').value;

        // Формируем URL с параметрами
        let url = `/api/admin/users?limit=${limit}&offset=${offset}`;
        if (status && status !== 'all') url += `&status=${encodeURIComponent(status)}`;
        if (activity && activity !== 'all') url += `&activity=${encodeURIComponent(activity)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        // Загружаем список пользователей
        fetch(url)
            .then(response => response.json())
            .then(users => {
                // Обновляем таблицу пользователей
                const usersTableBody = document.getElementById('users-table-body');
                usersTableBody.innerHTML = '';

                // Заполняем таблицу
                users.forEach(user => {
                    const statusBadge = `<span class="badge ${user.status}">${getStatusText(user.status)}</span>`;

                    const row = `
                        <tr>
                            <td>${user.id}</td>
                            <td>${user.name || 'Не указано'}</td>
                            <td>${statusBadge}</td>
                            <td>${user.last_activity || 'Не указано'}</td>
                            <td>${user.messages}</td>
                            <td>
                                <div class="actions">
                                    <button class="btn-icon view-user" data-id="${user.id}" title="Просмотр">
                                        <i class="fas fa-eye"></i>
                                    </button>
                                    ${user.status === 'blocked' ? 
                                        `<button class="btn-icon unblock-user" data-id="${user.id}" title="Разблокировать">
                                            <i class="fas fa-unlock"></i>
                                        </button>` : 
                                        `<button class="btn-icon block-user" data-id="${user.id}" title="Заблокировать">
                                            <i class="fas fa-ban"></i>
                                        </button>`
                                    }
                                </div>
                            </td>
                        </tr>
                    `;

                    usersTableBody.innerHTML += row;
                });

                // Добавляем обработчики для кнопок
                setupUserButtons();
            })
            .catch(error => {
                console.error('Ошибка при загрузке списка пользователей:', error);
                showNotification('Ошибка при загрузке списка пользователей', 'error');
            });
    }

    /**
     * Настройка обработчиков событий
     */
    function setupEventListeners() {
        // Навигация по страницам
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                const page = this.dataset.page;
                switchPage(page);
            });
        });

        // Мобильная навигация
        document.getElementById('mobile-menu-toggle').addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('visible');
            document.getElementById('sidebar-overlay').classList.toggle('visible');
            document.body.classList.toggle('menu-open');

            // Меняем иконку
            if (this.querySelector('i').classList.contains('fa-bars')) {
                this.querySelector('i').classList.remove('fa-bars');
                this.querySelector('i').classList.add('fa-times');
            } else {
                this.querySelector('i').classList.remove('fa-times');
                this.querySelector('i').classList.add('fa-bars');
            }
        });

        // Затемнение для закрытия мобильного меню
        document.getElementById('sidebar-overlay').addEventListener('click', function() {
            document.querySelector('.sidebar').classList.remove('visible');
            document.getElementById('sidebar-overlay').classList.remove('visible');
            document.body.classList.remove('menu-open');

            // Меняем иконку
            const mobileToggle = document.getElementById('mobile-menu-toggle');
            if (mobileToggle.querySelector('i').classList.contains('fa-times')) {
                mobileToggle.querySelector('i').classList.remove('fa-times');
                mobileToggle.querySelector('i').classList.add('fa-bars');
            }
        });

        // Сворачивание/разворачивание боковой панели
        document.getElementById('sidebar-toggle').addEventListener('click', function() {
            document.querySelector('.sidebar').classList.toggle('collapsed');
            document.querySelector('.content').classList.toggle('expanded');
        });

        // Верхнее меню для мобильных устройств
        document.getElementById('top-menu-toggle').addEventListener('click', function() {
            document.getElementById('top-dropdown-menu').classList.toggle('active');
        });

        // Закрытие верхнего меню
        document.getElementById('close-dropdown').addEventListener('click', function() {
            document.getElementById('top-dropdown-menu').classList.remove('active');
        });

        // Навигация из верхнего меню
        document.querySelectorAll('.dropdown-nav-item').forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                const page = this.dataset.page;
                switchPage(page);
                document.getElementById('top-dropdown-menu').classList.remove('active');
            });
        });

        // Переключение темы
        document.getElementById('theme-toggle').addEventListener('click', function() {
            document.body.classList.toggle('dark-theme');

            // Обновляем иконку
            if (document.body.classList.contains('dark-theme')) {
                this.innerHTML = '<i class="fas fa-sun"></i>';
                localStorage.setItem('dark_mode', 'true');
            } else {
                this.innerHTML = '<i class="fas fa-moon"></i>';
                localStorage.setItem('dark_mode', 'false');
            }
        });

        // Полноэкранный режим
        document.getElementById('fullscreen-toggle').addEventListener('click', function() {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen();
                this.innerHTML = '<i class="fas fa-compress"></i>';
            } else {
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                    this.innerHTML = '<i class="fas fa-expand"></i>';
                }
            }
        });

        // Обновление данных
        document.getElementById('refresh-data').addEventListener('click', function() {
            refreshCurrentPage();
            showNotification('Данные успешно обновлены', 'success');
        });

        // Автоматическое обновление
        document.getElementById('auto-scroll').addEventListener('click', function() {
            this.classList.toggle('active');

            // Если активно, прокручиваем к концу логов
            if (this.classList.contains('active')) {
                document.getElementById('logs-container').scrollTop = document.getElementById('logs-container').scrollHeight;
            }
        });

        // Копирование логов
        document.getElementById('copy-logs').addEventListener('click', function() {
            const logsText = document.getElementById('logs-container').textContent;

            navigator.clipboard.writeText(logsText)
                .then(() => {
                    showNotification('Логи скопированы в буфер обмена', 'success');
                })
                .catch(err => {
                    console.error('Ошибка при копировании логов:', err);
                    showNotification('Ошибка при копировании логов', 'error');
                });
        });

        // Развертывание логов на весь экран
        document.getElementById('expand-logs').addEventListener('click', function() {
            const logsTerminal = document.querySelector('.logs-terminal');
            logsTerminal.classList.toggle('expanded');

            // Обновляем иконку
            if (logsTerminal.classList.contains('expanded')) {
                this.innerHTML = '<i class="fas fa-compress-alt"></i>';
            } else {
                this.innerHTML = '<i class="fas fa-expand-alt"></i>';
            }
        });

        // Обработчики для страницы исторических событий
        if (document.getElementById('filter-apply')) {
            document.getElementById('filter-apply').addEventListener('click', function() {
                loadHistoricalEvents();
            });
        }

        if (document.getElementById('filter-reset')) {
            document.getElementById('filter-reset').addEventListener('click', function() {
                // Сбрасываем фильтры
                document.getElementById('event-search').value = '';
                document.getElementById('event-category-filter').value = 'all';
                document.getElementById('event-century-filter').value = 'all';

                // Загружаем события без фильтров
                loadHistoricalEvents();
            });
        }

        if (document.getElementById('add-new-event')) {
            document.getElementById('add-new-event').addEventListener('click', function() {
                showAddEventForm();
            });
        }

        // Обработчики для страницы пользователей
        if (document.getElementById('users-filter-apply')) {
            document.getElementById('users-filter-apply').addEventListener('click', function() {
                loadUsers();
            });
        }

        if (document.getElementById('users-filter-reset')) {
            document.getElementById('users-filter-reset').addEventListener('click', function() {
                // Сбрасываем фильтры
                document.getElementById('user-search').value = '';
                document.getElementById('user-status-filter').value = 'all';
                document.getElementById('user-activity-filter').value = 'all';

                // Загружаем пользователей без фильтров
                loadUsers();
            });
        }

        // Экспорт пользователей
        if (document.getElementById('export-users')) {
            document.getElementById('export-users').addEventListener('click', function() {
                // Подготавливаем параметры экспорта
                const status = document.getElementById('user-status-filter').value;
                const activity = document.getElementById('user-activity-filter').value;
                const search = document.getElementById('user-search').value;

                // Формируем URL с параметрами
                let url = `/api/admin/export-users?format=csv`;
                if (status && status !== 'all') url += `&status=${encodeURIComponent(status)}`;
                if (activity && activity !== 'all') url += `&activity=${encodeURIComponent(activity)}`;
                if (search) url += `&search=${encodeURIComponent(search)}`;

                // Открываем URL для скачивания
                window.open(url, '_blank');
            });
        }

        // Обработчики для страницы администраторов
        if (document.getElementById('add-admin-form')) {
            document.getElementById('add-admin-form').addEventListener('submit', function(e) {
                e.preventDefault();

                const adminId = document.getElementById('new-admin-id').value;
                const isSuper = document.getElementById('is-super-admin').checked;

                // Отправляем запрос на добавление администратора
                fetch('/api/admin/add-admin', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        admin_id: parseInt(adminId),
                        is_super: isSuper
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification('Администратор успешно добавлен', 'success');
                        // Сбрасываем форму
                        document.getElementById('add-admin-form').reset();
                        // Обновляем списки администраторов
                        loadAdminsList();
                    } else {
                        showNotification(data.message || 'Ошибка при добавлении администратора', 'error');
                    }
                })
                .catch(error => {
                    console.error('Ошибка при добавлении администратора:', error);
                    showNotification('Ошибка при добавлении администратора', 'error');
                });
            });
        }

        if (document.getElementById('remove-admin-form')) {
            document.getElementById('remove-admin-form').addEventListener('submit', function(e) {
                e.preventDefault();

                const adminId = document.getElementById('admin-to-remove').value;

                if (!adminId) {
                    showNotification('Выберите администратора для удаления', 'warning');
                    return;
                }

                // Подтверждение удаления
                if (!confirm(`Вы уверены, что хотите удалить администратора с ID ${adminId}?`)) {
                    return;
                }

                // Отправляем запрос на удаление администратора
                fetch('/api/admin/remove-admin', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        admin_id: parseInt(adminId)
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        showNotification('Администратор успешно удален', 'success');
                        // Сбрасываем форму
                        document.getElementById('remove-admin-form').reset();
                        // Обновляем списки администраторов
                        loadAdminsList();
                    } else {
                        showNotification(data.message || 'Ошибка при удалении администратора', 'error');
                    }
                })
                .catch(error => {
                    console.error('Ошибка при удалении администратора:', error);
                    showNotification('Ошибка при удалении администратора', 'error');
                });
            });
        }

        // Обработчики для страницы логов
        if (document.getElementById('refresh-logs')) {
            document.getElementById('refresh-logs').addEventListener('click', function() {
                loadLogs();
            });
        }

        if (document.getElementById('export-logs')) {
            document.getElementById('export-logs').addEventListener('click', function() {
                // Подготавливаем параметры экспорта
                const level = document.getElementById('log-level').value;
                const limit = document.getElementById('log-limit').value;

                // Формируем URL с параметрами
                let url = `/api/admin/export-logs?format=txt`;
                if (level && level !== 'all') url += `&level=${encodeURIComponent(level)}`;
                if (limit) url += `&limit=${encodeURIComponent(limit)}`;

                // Открываем URL для скачивания
                window.open(url, '_blank');
            });
        }

        // Обработчики для страницы настроек
        if (document.getElementById('settings-form')) {
            document.getElementById('settings-form').addEventListener('submit', function(e) {
                e.preventDefault();

                // Собираем настройки из формы
                const settings = {
                    auto_update_topics: document.getElementById('auto-update-topics').checked,
                    collect_statistics: document.getElementById('collect-statistics').checked,
                    developer_mode: document.getElementById('developer-mode').checked,
                    private_mode: document.getElementById('private-mode').checked
                };

                // Добавляем API настройки, если они есть
                if (document.getElementById('api-request-limit')) {
                    settings.api_request_limit = parseInt(document.getElementById('api-request-limit').value);
                }

                if (document.getElementById('cache-duration')) {
                    settings.cache_duration = parseInt(document.getElementById('cache-duration').value);
                }

                if (document.getElementById('api-model')) {
                    settings.api_model = document.getElementById('api-model').value;
                }

                if (document.getElementById('api-key')) {
                    settings.api_key = document.getElementById('api-key').value;
                }

                // Добавляем настройки уведомлений
                if (document.getElementById('notification-level')) {
                    settings.notification_level = document.getElementById('notification-level').value;
                }

                if (document.getElementById('notification-channel')) {
                    settings.notification_channel = document.getElementById('notification-channel').value;
                }

                if (document.getElementById('notification-schedule')) {
                    settings.notification_schedule = document.getElementById('notification-schedule').value;
                }

                // Отправляем настройки на сервер
                fetch('/api/admin/save-settings', {
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
                        showNotification(data.message || 'Ошибка при сохранении настроек', 'error');
                    }
                })
                .catch(error => {
                    console.error('Ошибка при сохранении настроек:', error);
                    showNotification('Ошибка при сохранении настроек', 'error');
                });
            });
        }

        // Обработчик для показа панели документации
        document.getElementById('docs-button').addEventListener('click', function() {
            document.getElementById('docs-modal').classList.add('active');
            document.getElementById('docs-modal-overlay').classList.add('active');
        });

        document.getElementById('dropdown-docs-button').addEventListener('click', function() {
            document.getElementById('docs-modal').classList.add('active');
            document.getElementById('docs-modal-overlay').classList.add('active');
            document.getElementById('top-dropdown-menu').classList.remove('active');
        });

        // Закрытие панели документации
        document.getElementById('docs-modal-close').addEventListener('click', function() {
            document.getElementById('docs-modal').classList.remove('active');
            document.getElementById('docs-modal-overlay').classList.remove('active');
        });

        document.getElementById('docs-modal-overlay').addEventListener('click', function() {
            document.getElementById('docs-modal').classList.remove('active');
            document.getElementById('docs-modal-overlay').classList.remove('active');
        });

        // Выход из системы
        document.getElementById('logout-button').addEventListener('click', function() {
            if (confirm('Вы уверены, что хотите выйти из системы?')) {
                logoutUser();
            }
        });

        document.getElementById('dropdown-logout-button').addEventListener('click', function() {
            if (confirm('Вы уверены, что хотите выйти из системы?')) {
                logoutUser();
                document.getElementById('top-dropdown-menu').classList.remove('active');
            }
        });

        // Обработчики для технического обслуживания
        document.querySelectorAll('.maintenance-action').forEach(button => {
            button.addEventListener('click', function() {
                const action = this.dataset.action;
                performMaintenanceAction(action);
            });
        });

        // Синхронизация range и number input
        if (document.getElementById('api-request-limit-range')) {
            document.getElementById('api-request-limit-range').addEventListener('input', function() {
                document.getElementById('api-request-limit').value = this.value;
            });

            document.getElementById('api-request-limit').addEventListener('input', function() {
                document.getElementById('api-request-limit-range').value = this.value;
            });
        }

        if (document.getElementById('cache-duration-range')) {
            document.getElementById('cache-duration-range').addEventListener('input', function() {
                document.getElementById('cache-duration').value = this.value;
            });

            document.getElementById('cache-duration').addEventListener('input', function() {
                document.getElementById('cache-duration-range').value = this.value;
            });
        }

        // Переключатель видимости API ключа
        if (document.getElementById('toggle-api-key')) {
            document.getElementById('toggle-api-key').addEventListener('click', function() {
                const apiKeyInput = document.getElementById('api-key');

                if (apiKeyInput.type === 'password') {
                    apiKeyInput.type = 'text';
                    this.innerHTML = '<i class="fas fa-eye-slash"></i>';
                } else {
                    apiKeyInput.type = 'password';
                    this.innerHTML = '<i class="fas fa-eye"></i>';
                }
            });
        }
    }

    /**
     * Настройка автоматического обновления данных
     */
    function setupAutoRefresh() {
        if (autoRefreshEnabled) {
            autoRefreshInterval = setInterval(() => {
                if (document.hasFocus()) {
                    refreshCurrentPage(true);
                }
            }, autoRefreshTime);
        }
    }

    /**
     * Обновление текущей страницы
     */
    function refreshCurrentPage(silent = false) {
        switch (currentPage) {
            case 'dashboard':
                loadDashboardData();
                break;
            case 'events':
                loadHistoricalEvents();
                break;
            case 'users':
                loadUsers();
                break;
            case 'admins':
                loadAdminsList();
                break;
            case 'logs':
                loadLogs();
                break;
            case 'settings':
                loadSettings();
                break;
        }

        if (!silent) {
            showNotification('Данные успешно обновлены', 'success');
        }
    }

    /**
     * Переключение страницы
     */
    function switchPage(page) {
        // Скрываем все страницы
        document.querySelectorAll('.page').forEach(p => {
            p.classList.remove('active');
        });

        // Показываем выбранную страницу
        document.getElementById(`${page}-page`).classList.add('active');

        // Обновляем активный элемент навигации
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelectorAll(`.nav-item[data-page="${page}"]`).forEach(item => {
            item.classList.add('active');
        });

        document.querySelectorAll('.dropdown-nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelectorAll(`.dropdown-nav-item[data-page="${page}"]`).forEach(item => {
            item.classList.add('active');
        });

        // Обновляем заголовок текущего раздела
        const sectionIcon = document.querySelector(`.nav-item[data-page="${page}"] i`);
        const sectionName = document.querySelector(`.nav-item[data-page="${page}"] span`);

        if (sectionIcon && sectionName) {
            document.getElementById('current-section-icon').className = sectionIcon.className;
            document.getElementById('current-section-name').textContent = sectionName.textContent;
        }

        // Сохраняем текущую страницу
        currentPage = page;

        // Загружаем данные для страницы
        switch (page) {
            case 'dashboard':
                loadDashboardData();
                break;
            case 'events':
                loadHistoricalEvents();
                break;
            case 'users':
                loadUsers();
                break;
            case 'admins':
                loadAdminsList();
                break;
            case 'logs':
                loadLogs();
                break;
            case 'settings':
                loadSettings();
                break;
        }

        // Закрываем мобильное меню, если оно открыто
        document.querySelector('.sidebar').classList.remove('visible');
        document.getElementById('sidebar-overlay').classList.remove('visible');
        document.body.classList.remove('menu-open');

        // Меняем иконку мобильного меню
        const mobileToggle = document.getElementById('mobile-menu-toggle');
        if (mobileToggle.querySelector('i').classList.contains('fa-times')) {
            mobileToggle.querySelector('i').classList.remove('fa-times');
            mobileToggle.querySelector('i').classList.add('fa-bars');
        }
    }

    /**
     * Отображение уведомления
     */
    function showNotification(message, type = 'info') {
        const notificationId = 'notification-' + Date.now();
        const notificationHTML = `
            <div class="notification ${type}" id="${notificationId}">
                <div class="notification-icon">
                    <i class="fas ${getNotificationIcon(type)}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${getNotificationTitle(type)}</div>
                    <div class="notification-message">${message}</div>
                </div>
                <button class="notification-close" onclick="document.getElementById('${notificationId}').remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        const container = document.getElementById('notifications-container');
        container.insertAdjacentHTML('afterbegin', notificationHTML);

        // Автоматическое удаление уведомления через 5 секунд
        setTimeout(() => {
            const notification = document.getElementById(notificationId);
            if (notification) {
                notification.classList.add('notification-hiding');
                setTimeout(() => {
                    if (notification) {
                        notification.remove();
                    }
                }, 500);
            }
        }, 5000);
    }

    /**
     * Получение иконки для уведомления
     */
    function getNotificationIcon(type) {
        switch (type) {
            case 'success': return 'fa-check-circle';
            case 'error': return 'fa-exclamation-circle';
            case 'warning': return 'fa-exclamation-triangle';
            case 'info':
            default: return 'fa-info-circle';
        }
    }

    /**
     * Получение заголовка для уведомления
     */
    function getNotificationTitle(type) {
        switch (type) {
            case 'success': return 'Успешно';
            case 'error': return 'Ошибка';
            case 'warning': return 'Предупреждение';
            case 'info':
            default: return 'Информация';
        }
    }

    /**
     * Выполнение действия технического обслуживания
     */
    function performMaintenanceAction(action) {
        // Подтверждение перед выполнением потенциально опасных действий
        const dangerousActions = ['restart', 'clean-logs'];
        if (dangerousActions.includes(action)) {
            if (!confirm('Вы уверены, что хотите выполнить это действие? Это может привести к временной недоступности системы.')) {
                return;
            }
        }

        // Отображаем индикатор выполнения для некоторых действий
        if (action === 'update-api') {
            const progressBar = document.getElementById('api-progress');
            const progressText = progressBar.nextElementSibling;

            // Анимация прогресса
            let progress = 0;
            const progressInterval = setInterval(() => {
                progress += 5;
                if (progress > 100) {
                    clearInterval(progressInterval);
                    return;
                }

                progressBar.style.width = progress + '%';
                progressText.textContent = progress + '%';
            }, 300);
        }

        // Отправляем запрос на выполнение действия
        fetch('/api/admin/maintenance', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message || 'Операция успешно выполнена', 'success');

                // Обновляем информацию о резервной копии, если это создание бэкапа
                if (action === 'create_backup' && document.getElementById('last-backup-time')) {
                    document.getElementById('last-backup-time').textContent = data.backup_time || 'Только что';
                }

                // Обновляем размер логов, если это очистка логов
                if (action === 'clean_logs' && document.getElementById('logs-size')) {
                    document.getElementById('logs-size').textContent = '0 КБ';
                }

                // Сбрасываем прогресс для обновления API
                if (action === 'update-api') {
                    document.getElementById('api-progress').style.width = '100%';
                    document.getElementById('api-progress').nextElementSibling.textContent = '100%';

                    // Обновляем статус
                    const statusElements = document.querySelectorAll('.maintenance-card:nth-child(3) .status-value');
                    if (statusElements.length > 0) {
                        statusElements[0].textContent = 'Завершено успешно';
                    }
                }
            } else {
                showNotification(data.message || 'Ошибка при выполнении операции', 'error');

                // Сбрасываем прогресс для обновления API в случае ошибки
                if (action === 'update-api') {
                    document.getElementById('api-progress').style.width = '0%';
                    document.getElementById('api-progress').nextElementSibling.textContent = '0%';

                    // Обновляем статус
                    const statusElements = document.querySelectorAll('.maintenance-card:nth-child(3) .status-value');
                    if (statusElements.length > 0) {
                        statusElements[0].textContent = 'Ошибка';
                    }
                }
            }
        })
        .catch(error => {
            console.error('Ошибка при выполнении операции:', error);
            showNotification('Ошибка при выполнении операции', 'error');

            // Сбрасываем прогресс для обновления API в случае ошибки
            if (action === 'update-api') {
                document.getElementById('api-progress').style.width = '0%';
                document.getElementById('api-progress').nextElementSibling.textContent = '0%';

                // Обновляем статус
                const statusElements = document.querySelectorAll('.maintenance-card:nth-child(3) .status-value');
                if (statusElements.length > 0) {
                    statusElements[0].textContent = 'Ошибка';
                }
            }
        });
    }

    /**
     * Показ формы добавления исторического события
     */
    function showAddEventForm() {
        // Создаем модальное окно для добавления события
        const modalContent = `
            <div class="modal-header">
                <h2><i class="fas fa-plus"></i> Добавление исторического события</h2>
                <button class="modal-close" id="event-modal-close">&times;</button>
            </div>
            <div class="modal-body">
                <form id="add-event-form" class="event-form">
                    <div class="form-group">
                        <label for="event-title">Название события</label>
                        <input type="text" id="event-title" placeholder="Введите название события" required>
                    </div>

                    <div class="form-group">
                        <label for="event-date">Дата</label>
                        <input type="text" id="event-date" placeholder="Например: 1812 год или 25 октября 1917 года">
                    </div>

                    <div class="form-group">
                        <label for="event-category">Категория</label>
                        <select id="event-category">
                            <option value="">Выберите категорию</option>
                            <!-- Заполняется из JS -->
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="event-description">Описание</label>
                        <textarea id="event-description" rows="5" placeholder="Подробное описание события"></textarea>
                    </div>

                    <div class="form-group">
                        <label>Координаты (если применимо)</label>
                        <div class="location-inputs">
                            <input type="text" id="event-lat" placeholder="Широта">
                            <input type="text" id="event-lng" placeholder="Долгота">
                        </div>
                    </div>

                    <div class="form-actions">
                        <button type="submit" class="btn btn-success">
                            <i class="fas fa-save"></i> Сохранить
                        </button>
                        <button type="button" class="btn btn-outline" id="event-form-cancel">
                            <i class="fas fa-times"></i> Отмена
                        </button>
                    </div>
                </form>
            </div>
        `;

        // Отображаем модальное окно
        const modalOverlay = document.getElementById('modal-overlay');
        const modalContainer = document.getElementById('modal-container');

        modalContainer.innerHTML = modalContent;
        modalOverlay.classList.add('active');

        // Загружаем категории
        fetch('/api/admin/categories')
            .then(response => response.json())
            .then(categories => {
                const categorySelect = document.getElementById('event-category');

                categories.forEach(category => {
                    categorySelect.innerHTML += `<option value="${category}">${category}</option>`;
                });
            })
            .catch(error => {
                console.error('Ошибка при загрузке категорий:', error);
            });

        // Обработчик для закрытия модального окна
        document.getElementById('event-modal-close').addEventListener('click', function() {
            modalOverlay.classList.remove('active');
        });

        document.getElementById('event-form-cancel').addEventListener('click', function() {
            modalOverlay.classList.remove('active');
        });

        // Обработчик отправки формы
        const addEventForm = document.getElementById('add-event-form');
        addEventForm.addEventListener('submit', function(e) {
            e.preventDefault();

            // Собираем данные формы
            const eventData = {
                title: document.getElementById('event-title').value,
                date: document.getElementById('event-date').value,
                category: document.getElementById('event-category').value,
                description: document.getElementById('event-description').value,
                location: {}
            };

            // Добавляем координаты, если они указаны
            const lat = document.getElementById('event-lat').value;
            const lng = document.getElementById('event-lng').value;

            if (lat && lng) {
                eventData.location = {
                    lat: parseFloat(lat),
                    lng: parseFloat(lng)
                };
            }

            // Отправляем запрос на добавление события
            fetch('/api/admin/historical-event', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(eventData)
            })
            .then(response => response.json())
            .then(data =>{
                if (data.success) {
                    showNotification('Событие успешно добавлено', 'success');
                    modalOverlay.classList.remove('active');

                    // Обновляем список событий
                    loadHistoricalEvents();
                } else {
                    showNotification(data.message || 'Ошибка при добавлении события', 'error');
                }
            })
            .catch(error => {
                console.error('Ошибка при добавлении события:', error);
                showNotification('Ошибка при добавлении события', 'error');
            });
        });
    }

    /**
     * Настройка обработчиков для кнопок редактирования и удаления событий
     */
    function setupEventButtons() {
        // Кнопки редактирования
        document.querySelectorAll('.edit-event').forEach(button => {
            button.addEventListener('click', function() {
                const eventId = this.dataset.id;
                showEditEventForm(eventId);
            });
        });

        // Кнопки удаления
        document.querySelectorAll('.delete-event').forEach(button => {
            button.addEventListener('click', function() {
                const eventId = this.dataset.id;

                if (confirm('Вы уверены, что хотите удалить это событие?')) {
                    deleteHistoricalEvent(eventId);
                }
            });
        });
    }

    /**
     * Показ формы редактирования исторического события
     */
    function showEditEventForm(eventId) {
        // Загружаем данные о событии
        fetch(`/api/admin/historical-event/${eventId}`)
            .then(response => response.json())
            .then(event => {
                // Создаем модальное окно для редактирования события
                const modalContent = `
                    <div class="modal-header">
                        <h2><i class="fas fa-edit"></i> Редактирование исторического события</h2>
                        <button class="modal-close" id="edit-event-modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <form id="edit-event-form" class="event-form" data-id="${event.id}">
                            <div class="form-group">
                                <label for="edit-event-title">Название события</label>
                                <input type="text" id="edit-event-title" placeholder="Введите название события" required value="${event.title || ''}">
                            </div>

                            <div class="form-group">
                                <label for="edit-event-date">Дата</label>
                                <input type="text" id="edit-event-date" placeholder="Например: 1812 год или 25 октября 1917 года" value="${event.date || ''}">
                            </div>

                            <div class="form-group">
                                <label for="edit-event-category">Категория</label>
                                <select id="edit-event-category">
                                    <option value="">Выберите категорию</option>
                                    <!-- Заполняется из JS -->
                                </select>
                            </div>

                            <div class="form-group">
                                <label for="edit-event-description">Описание</label>
                                <textarea id="edit-event-description" rows="5" placeholder="Подробное описание события">${event.description || ''}</textarea>
                            </div>

                            <div class="form-group">
                                <label>Координаты (если применимо)</label>
                                <div class="location-inputs">
                                    <input type="text" id="edit-event-lat" placeholder="Широта" value="${event.location && event.location.lat ? event.location.lat : ''}">
                                    <input type="text" id="edit-event-lng" placeholder="Долгота" value="${event.location && event.location.lng ? event.location.lng : ''}">
                                </div>
                            </div>

                            <div class="form-actions">
                                <button type="submit" class="btn btn-success">
                                    <i class="fas fa-save"></i> Сохранить
                                </button>
                                <button type="button" class="btn btn-outline" id="edit-event-form-cancel">
                                    <i class="fas fa-times"></i> Отмена
                                </button>
                            </div>
                        </form>
                    </div>
                `;

                // Отображаем модальное окно
                const modalOverlay = document.getElementById('modal-overlay');
                const modalContainer = document.getElementById('modal-container');

                modalContainer.innerHTML = modalContent;
                modalOverlay.classList.add('active');

                // Загружаем категории
                fetch('/api/admin/categories')
                    .then(response => response.json())
                    .then(categories => {
                        const categorySelect = document.getElementById('edit-event-category');

                        categories.forEach(category => {
                            const option = document.createElement('option');
                            option.value = category;
                            option.textContent = category;
                            option.selected = category === event.category;
                            categorySelect.appendChild(option);
                        });
                    })
                    .catch(error => {
                        console.error('Ошибка при загрузке категорий:', error);
                    });

                // Обработчик для закрытия модального окна
                document.getElementById('edit-event-modal-close').addEventListener('click', function() {
                    modalOverlay.classList.remove('active');
                });

                document.getElementById('edit-event-form-cancel').addEventListener('click', function() {
                    modalOverlay.classList.remove('active');
                });

                // Обработчик отправки формы
                const editEventForm = document.getElementById('edit-event-form');
                editEventForm.addEventListener('submit', function(e) {
                    e.preventDefault();

                    // Собираем данные формы
                    const eventData = {
                        id: event.id,
                        title: document.getElementById('edit-event-title').value,
                        date: document.getElementById('edit-event-date').value,
                        category: document.getElementById('edit-event-category').value,
                        description: document.getElementById('edit-event-description').value,
                        location: {}
                    };

                    // Добавляем координаты, если они указаны
                    const lat = document.getElementById('edit-event-lat').value;
                    const lng = document.getElementById('edit-event-lng').value;

                    if (lat && lng) {
                        eventData.location = {
                            lat: parseFloat(lat),
                            lng: parseFloat(lng)
                        };
                    }

                    // Отправляем запрос на обновление события
                    fetch(`/api/admin/historical-event/${event.id}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(eventData)
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            showNotification('Событие успешно обновлено', 'success');
                            modalOverlay.classList.remove('active');

                            // Обновляем список событий
                            loadHistoricalEvents();
                        } else {
                            showNotification(data.message || 'Ошибка при обновлении события', 'error');
                        }
                    })
                    .catch(error => {
                        console.error('Ошибка при обновлении события:', error);
                        showNotification('Ошибка при обновлении события', 'error');
                    });
                });
            })
            .catch(error => {
                console.error('Ошибка при загрузке данных о событии:', error);
                showNotification('Ошибка при загрузке данных о событии', 'error');
            });
    }

    /**
     * Удаление исторического события
     */
    function deleteHistoricalEvent(eventId) {
        fetch(`/api/admin/historical-event/${eventId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Событие успешно удалено', 'success');

                // Обновляем список событий
                loadHistoricalEvents();
            } else {
                showNotification(data.message || 'Ошибка при удалении события', 'error');
            }
        })
        .catch(error => {
            console.error('Ошибка при удалении события:', error);
            showNotification('Ошибка при удалении события', 'error');
        });
    }

    /**
     * Настройка обработчиков для кнопок на странице пользователей
     */
    function setupUserButtons() {
        // Кнопки просмотра пользователя
        document.querySelectorAll('.view-user').forEach(button => {
            button.addEventListener('click', function() {
                const userId = this.dataset.id;
                showUserDetails(userId);
            });
        });

        // Кнопки блокировки пользователя
        document.querySelectorAll('.block-user').forEach(button => {
            button.addEventListener('click', function() {
                const userId = this.dataset.id;

                if (confirm(`Вы уверены, что хотите заблокировать пользователя с ID ${userId}?`)) {
                    blockUser(userId);
                }
            });
        });

        // Кнопки разблокировки пользователя
        document.querySelectorAll('.unblock-user').forEach(button => {
            button.addEventListener('click', function() {
                const userId = this.dataset.id;

                if (confirm(`Вы уверены, что хотите разблокировать пользователя с ID ${userId}?`)) {
                    unblockUser(userId);
                }
            });
        });
    }

    /**
     * Показ подробной информации о пользователе
     */
    function showUserDetails(userId) {
        fetch(`/api/admin/user/${userId}`)
            .then(response => response.json())
            .then(user => {
                // Создаем модальное окно для просмотра информации о пользователе
                const modalContent = `
                    <div class="modal-header">
                        <h2><i class="fas fa-user"></i> Информация о пользователе</h2>
                        <button class="modal-close" id="user-modal-close">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="user-details-container">
                            <div class="user-details-header">
                                <div class="user-avatar large">
                                    <i class="fas fa-user"></i>
                                </div>
                                <div class="user-info">
                                    <h3>${user.name || 'Имя не указано'}</h3>
                                    <div class="user-id">ID: ${user.id}</div>
                                    <div class="user-status">
                                        <span class="badge ${user.status}">${getStatusText(user.status)}</span>
                                    </div>
                                </div>
                            </div>

                            <div class="user-stats">
                                <div class="stat-block">
                                    <div class="stat-label">Регистрация</div>
                                    <div class="stat-value">${user.registration_date || 'Не указано'}</div>
                                </div>
                                <div class="stat-block">
                                    <div class="stat-label">Последняя активность</div>
                                    <div class="stat-value">${user.last_activity || 'Не указано'}</div>
                                </div>
                                <div class="stat-block">
                                    <div class="stat-label">Всего сообщений</div>
                                    <div class="stat-value">${user.messages}</div>
                                </div>
                                <div class="stat-block">
                                    <div class="stat-label">Пройдено тестов</div>
                                    <div class="stat-value">${user.tests_completed || 0}</div>
                                </div>
                            </div>

                            <div class="user-section">
                                <h4>Избранные темы</h4>
                                <div class="user-topics">
                                    ${user.favorite_topics && user.favorite_topics.length > 0 ?
                                        user.favorite_topics.map(topic => `<span class="user-topic-badge">${topic}</span>`).join('') :
                                        '<span class="empty-data">Нет избранных тем</span>'
                                    }
                                </div>
                            </div>

                            <div class="user-actions">
                                ${user.status === 'blocked' ?
                                    `<button class="btn btn-success" id="modal-unblock-user" data-id="${user.id}">
                                        <i class="fas fa-unlock"></i> Разблокировать
                                    </button>` :
                                    `<button class="btn btn-danger" id="modal-block-user" data-id="${user.id}">
                                        <i class="fas fa-ban"></i> Заблокировать
                                    </button>`
                                }
                            </div>
                        </div>
                    </div>
                `;

                // Отображаем модальное окно
                const modalOverlay = document.getElementById('modal-overlay');
                const modalContainer = document.getElementById('modal-container');

                modalContainer.innerHTML = modalContent;
                modalOverlay.classList.add('active');

                // Обработчик для закрытия модального окна
                document.getElementById('user-modal-close').addEventListener('click', function() {
                    modalOverlay.classList.remove('active');
                });

                // Обработчик для кнопки блокировки
                if (user.status !== 'blocked') {
                    document.getElementById('modal-block-user').addEventListener('click', function() {
                        const userId = this.dataset.id;

                        if (confirm(`Вы уверены, что хотите заблокировать пользователя с ID ${userId}?`)) {
                            blockUser(userId);
                            modalOverlay.classList.remove('active');
                        }
                    });
                }

                // Обработчик для кнопки разблокировки
                if (user.status === 'blocked') {
                    document.getElementById('modal-unblock-user').addEventListener('click', function() {
                        const userId = this.dataset.id;

                        if (confirm(`Вы уверены, что хотите разблокировать пользователя с ID ${userId}?`)) {
                            unblockUser(userId);
                            modalOverlay.classList.remove('active');
                        }
                    });
                }
            })
            .catch(error => {
                console.error('Ошибка при загрузке данных о пользователе:', error);
                showNotification('Ошибка при загрузке данных о пользователе', 'error');
            });
    }

    /**
     * Блокировка пользователя
     */
    function blockUser(userId) {
        fetch(`/api/admin/user/${userId}/block`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Пользователь успешно заблокирован', 'success');

                // Обновляем список пользователей
                loadUsers();
            } else {
                showNotification(data.message || 'Ошибка при блокировке пользователя', 'error');
            }
        })
        .catch(error => {
            console.error('Ошибка при блокировке пользователя:', error);
            showNotification('Ошибка при блокировке пользователя', 'error');
        });
    }

    /**
     * Разблокировка пользователя
     */
    function unblockUser(userId) {
        fetch(`/api/admin/user/${userId}/unblock`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Пользователь успешно разблокирован', 'success');

                // Обновляем список пользователей
                loadUsers();
            } else {
                showNotification(data.message || 'Ошибка при разблокировке пользователя', 'error');
            }
        })
        .catch(error => {
            console.error('Ошибка при разблокировке пользователя:', error);
            showNotification('Ошибка при разблокировке пользователя', 'error');
        });
    }

    // Функция авторизации через ID
    async function loginWithId() {
        const adminId = document.getElementById('admin-id').value;
        if (!adminId) {
            showMessage('error', 'Введите ID администратора');
            return;
        }

        try {
            const response = await fetch('/api/admin/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ admin_id: parseInt(adminId) })
            });

            const result = await response.json();

            if (result.success) {
                showMessage('success', 'Авторизация успешна');
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showMessage('error', result.message || 'Ошибка авторизации');
            }
        } catch (error) {
            console.error('Ошибка при авторизации:', error);
            showMessage('error', 'Ошибка при выполнении запроса');
        }
    }

});