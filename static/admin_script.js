
document.addEventListener('DOMContentLoaded', function() {
    // Переменные для отслеживания свайпа
    let touchStartX = 0;
    let touchEndX = 0;
    
    // Проверяем, поддерживаются ли сенсорные события
    if ('ontouchstart' in window) {
        document.addEventListener('touchstart', function(e) {
            touchStartX = e.changedTouches[0].screenX;
        }, {passive: true});
        
        document.addEventListener('touchend', function(e) {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        }, {passive: true});
    }
    
    // Функция для скачивания документации
    window.downloadDoc = function(docPath, fileName) {
        // Показываем уведомление о начале загрузки
        showNotification(`Загрузка документа ${fileName}...`, 'info');

        // Проверяем, начинается ли путь с static/docs
        let fetchUrl;
        if (docPath.startsWith('static/docs/')) {
            // Для документов в папке static/docs можно использовать публичный маршрут
            const docName = docPath.replace('static/docs/', '');
            fetchUrl = '/neadmin/' + encodeURIComponent(docName);

            // Создаем прямую ссылку для скачивания
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = fetchUrl;
            a.download = fileName;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);

            showNotification(`Документ ${fileName} скачивается`, 'success');
            return;
        } else {
            // Для других документов используем оригинальный маршрут с авторизацией
            fetchUrl = '/api/admin/get-doc?path=' + encodeURIComponent(docPath);
        }

        // Создаем ссылку для скачивания через API
        fetch(fetchUrl)
            .then(response => {
                if (response.ok) {
                    return response.blob();
                }
                // Если получили ошибку, пытаемся прочитать детали ошибки
                if (response.status === 404) {
                    throw new Error(`Файл не найден (404): ${docPath}`);
                }
                return response.json().then(data => {
                    throw new Error(data.error || `Ошибка ${response.status}`);
                });
            })
            .then(blob => {
                // Создаем ссылку для скачивания
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = fileName;
                document.body.appendChild(a);
                a.click();

                // Очищаем ресурсы
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);

                showNotification(`Документ ${fileName} успешно загружен`, 'success');
            })
            .catch(error => {
                console.error('Ошибка при скачивании документа:', error);
                showNotification(`Ошибка при скачивании документа: ${error.message}`, 'error');

                // Предлагаем открыть документ для просмотра как альтернативу
                setTimeout(() => {
                    if (confirm(`Не удалось скачать документ. Попробовать открыть его для просмотра?`)) {
                        viewDoc(docPath);
                    }
                }, 1000);
            });
    }

    // Функция просмотра документа
    window.viewDoc = function(docPath) {
        const modal = document.createElement('div');
        modal.className = 'doc-viewer-modal';
        modal.innerHTML = `
            <div class="doc-viewer-content">
                <div class="doc-viewer-header">
                    <h2>Просмотр документации</h2>
                    <button class="doc-viewer-close">&times;</button>
                </div>
                <div class="doc-viewer-body">
                    <iframe src="/api/admin/view-doc?path=${encodeURIComponent(docPath)}" width="100%" height="100%" frameborder="0"></iframe>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Обработчик закрытия
        modal.querySelector('.doc-viewer-close').addEventListener('click', function() {
            document.body.removeChild(modal);
        });
        
        // Закрытие по клику вне контента
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }

    function showNotification(message, type) {
        const notificationsContainer = document.getElementById('notifications-container');
        
        if (!notificationsContainer) {
            console.error('Контейнер уведомлений не найден');
            console.log(`Уведомление: ${message} (${type})`);
            return;
        }
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        let iconClass = 'fa-info-circle';
        if (type === 'success') iconClass = 'fa-check-circle';
        if (type === 'error') iconClass = 'fa-exclamation-circle';
        if (type === 'warning') iconClass = 'fa-exclamation-triangle';
        
        notification.innerHTML = `
            <div class="notification-icon">
                <i class="fas ${iconClass}"></i>
            </div>
            <div class="notification-content">
                <div class="notification-message">${message}</div>
            </div>
            <button class="notification-close">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        notificationsContainer.appendChild(notification);
        
        // Удаление уведомления по клику на кнопку закрытия
        notification.querySelector('.notification-close').addEventListener('click', function() {
            notificationsContainer.removeChild(notification);
        });
        
        // Автоматическое удаление через 5 секунд
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    function handleSwipe() {
        // Определяем минимальное расстояние для регистрации свайпа (в пикселях)
        const swipeThreshold = 70;
        // Определяем максимальное расстояние от левого края экрана для начала свайпа
        const edgeThreshold = 30;
        
        // Проверяем, был ли свайп справа налево от края экрана
        if (touchStartX < edgeThreshold && (touchEndX - touchStartX) > swipeThreshold) {
            // Свайп справа налево от края экрана - открываем меню
            const sidebar = document.querySelector('.sidebar');
            const sidebarOverlay = document.querySelector('.sidebar-overlay');
            const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
            
            if (sidebar && sidebarOverlay) {
                sidebar.classList.add('visible');
                sidebarOverlay.classList.add('visible');
                document.body.classList.add('menu-open');
                
                // Меняем иконку меню
                if (mobileMenuToggle && mobileMenuToggle.querySelector('i')) {
                    mobileMenuToggle.querySelector('i').className = 'fas fa-times';
                }
            }
        } else if ((touchStartX - touchEndX) > swipeThreshold) {
            // Свайп слева направо - закрываем меню
            const sidebar = document.querySelector('.sidebar');
            const sidebarOverlay = document.querySelector('.sidebar-overlay');
            const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
            
            if (sidebar && sidebar.classList.contains('visible')) {
                sidebar.classList.remove('visible');
                if (sidebarOverlay) sidebarOverlay.classList.remove('visible');
                document.body.classList.remove('menu-open');
                
                // Меняем иконку меню
                if (mobileMenuToggle && mobileMenuToggle.querySelector('i')) {
                    mobileMenuToggle.querySelector('i').className = 'fas fa-bars';
                }
            }
        }
    }

    // Инициализация бокового меню
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const content = document.querySelector('.content');
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    const swipeIndicator = document.getElementById('swipe-indicator');

    // Инициализация выпадающего меню сверху
    const topMenuToggle = document.getElementById('top-menu-toggle');
    const topDropdownMenu = document.getElementById('top-dropdown-menu');
    const closeDropdown = document.getElementById('close-dropdown');
    const dropdownNavItems = document.querySelectorAll('.dropdown-nav-item');
    const dropdownDocsButton = document.getElementById('dropdown-docs-button');
    const dropdownLogoutButton = document.getElementById('dropdown-logout-button');
    
    // Создаем оверлей для выпадающего меню если его нет
    let topDropdownOverlay = document.querySelector('.top-dropdown-overlay');
    if (!topDropdownOverlay) {
        topDropdownOverlay = document.createElement('div');
        topDropdownOverlay.className = 'top-dropdown-overlay';
        document.body.appendChild(topDropdownOverlay);
    }

    // Функция для переключения выпадающего меню
    function toggleTopMenu(show) {
        if (!topDropdownMenu) return;
        
        const isOpen = topDropdownMenu.classList.contains('open');
        
        if (show === undefined) {
            show = !isOpen;
        }
        
        if (show) {
            topDropdownMenu.classList.add('open');
            topDropdownOverlay.classList.add('visible');
            document.body.classList.add('menu-open');
        } else {
            topDropdownMenu.classList.remove('open');
            topDropdownOverlay.classList.remove('visible');
            document.body.classList.remove('menu-open');
        }
    }
    
    // Обработчики для выпадающего меню сверху
    if (topMenuToggle) {
        topMenuToggle.addEventListener('click', function() {
            toggleTopMenu();
        });
    }
    
    if (closeDropdown) {
        closeDropdown.addEventListener('click', function() {
            toggleTopMenu(false);
        });
    }
    
    // Обработчик для оверлея выпадающего меню
    if (topDropdownOverlay) {
        topDropdownOverlay.addEventListener('click', function() {
            toggleTopMenu(false);
        });
    }
    
    // Обработчики для пунктов меню в выпадающем меню
    if (dropdownNavItems) {
        dropdownNavItems.forEach(item => {
            item.addEventListener('click', function() {
                // Переключаем активный класс
                dropdownNavItems.forEach(el => el.classList.remove('active'));
                this.classList.add('active');
                
                // Закрываем меню после выбора
                toggleTopMenu(false);
                
                // Дополнительные действия по необходимости
                const pageName = this.getAttribute('data-page');
                // Можно добавить код для переключения страниц здесь
            });
        });
    }
    
    // Обработчики для кнопок в футере выпадающего меню
    if (dropdownDocsButton) {
        dropdownDocsButton.addEventListener('click', function() {
            // Эмулируем клик по оригинальной кнопке документации
            const originalDocsButton = document.getElementById('docs-button');
            if (originalDocsButton) {
                originalDocsButton.click();
            }
            toggleTopMenu(false);
        });
    }
    
    if (dropdownLogoutButton) {
        dropdownLogoutButton.addEventListener('click', function() {
            // Эмулируем клик по оригинальной кнопке выхода
            const originalLogoutButton = document.getElementById('logout-button');
            if (originalLogoutButton) {
                originalLogoutButton.click();
            }
            toggleTopMenu(false);
        });
    }

    if(sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            content.classList.toggle('expanded');
        });
    }

    // Обработчики для мобильного меню
    if(mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', function() {
            toggleMobileMenu();
        });
    }

    // Обработчик для затемнения при открытом меню
    if(sidebarOverlay) {
        sidebarOverlay.addEventListener('click', function() {
            toggleMobileMenu(false);
        });
    }

    // Функция для переключения мобильного меню
    function toggleMobileMenu(show) {
        if (!sidebar) return;
        
        const isVisible = sidebar.classList.contains('visible');

        // Если show не определен, инвертируем текущее состояние
        if (show === undefined) {
            show = !isVisible;
        }

        if (show) {
            sidebar.classList.add('visible');
            if (sidebarOverlay) sidebarOverlay.classList.add('visible');
            document.body.classList.add('menu-open');

            // Меняем иконку на крестик
            if (mobileMenuToggle && mobileMenuToggle.querySelector('i')) {
                mobileMenuToggle.querySelector('i').className = 'fas fa-times';
            }

            // Скрываем индикатор свайпа
            if (swipeIndicator) {
                swipeIndicator.classList.remove('visible');
            }
        } else {
            sidebar.classList.remove('visible');
            if (sidebarOverlay) sidebarOverlay.classList.remove('visible');
            document.body.classList.remove('menu-open');

            // Возвращаем иконку меню
            if (mobileMenuToggle && mobileMenuToggle.querySelector('i')) {
                mobileMenuToggle.querySelector('i').className = 'fas fa-bars';
            }
        }
    }

    // Показываем индикатор свайпа, если пользователь долго не открывал меню
    if (swipeIndicator && window.innerWidth <= 768) {
        setTimeout(() => {
            if (!sidebar || !sidebar.classList.contains('visible')) {
                swipeIndicator.classList.add('visible');

                // Скрываем индикатор через 5 секунд
                setTimeout(() => {
                    swipeIndicator.classList.remove('visible');
                }, 5000);
            }
        }, 3000);
    }
    
    // Добавляем поддержку жестов свайпа для мобильного меню
    // Выполняется автоматически через обработчики touchstart/touchend добавленные выше
});
