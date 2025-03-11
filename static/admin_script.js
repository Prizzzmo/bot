<!DOCTYPE html>
<html>
<head>
<title>Admin Panel</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" integrity="sha512-9usAa10IRO0HhonpyAIVpjrylPvoDwiPUiKdWk5t3PyolY1cOd4DSE0Ga+ri4AuTroPR5aQvXU9xC6qOPnzFeg==" crossorigin="anonymous" referrerpolicy="no-referrer" />
<style>
body {
    margin: 0;
    font-family: sans-serif;
}
.sidebar {
    background-color: #f0f0f0;
    width: 250px;
    height: 100vh;
    position: fixed;
    top: 0;
    left: 0;
    overflow-y: auto;
    transition: transform 0.3s ease-in-out;
    z-index: 1000;
}
.sidebar.collapsed {
    transform: translateX(-100%);
}
.sidebar.visible {
    transform: translateX(0);
}
.content {
    margin-left: 250px;
    transition: margin-left 0.3s ease-in-out;
}
.content.expanded {
    margin-left: 0;
}
#sidebar-toggle {
    position: fixed;
    top: 10px;
    left: 10px;
    z-index: 1001;
    cursor: pointer;
}
#mobile-menu-toggle {
    display: none; /* Hide on larger screens */
    position: fixed;
    top: 10px;
    left: 10px;
    z-index: 1001;
    cursor: pointer;
}
#sidebar-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 999;
    display: none;
    transition: opacity 0.3s ease-in-out;
}
#sidebar-overlay.visible {
    display: block;
}
.menu-open {
    overflow: hidden;
}
#swipe-indicator {
    position: fixed;
    top: 50%;
    left: 10px;
    transform: translateY(-50%);
    z-index: 1002;
    display: none;
    color: #fff;
    font-size: 16px;
}
#swipe-indicator.visible {
    display: block;
}
@media (max-width: 768px) {
    .sidebar {
        transform: translateX(-100%);
    }
    .sidebar.visible {
        transform: translateX(0);
    }
    .content {
        margin-left: 0;
    }
    #sidebar-toggle {
        display: none;
    }
    #mobile-menu-toggle {
        display: block;
    }
}
</style>
</head>
<body>
<div id="sidebar-overlay"></div>
<div id="swipe-indicator"><i class="fas fa-chevron-left"></i> Swipe to close</div>
<div class="sidebar">
    <ul>
        <li><a href="#">Dashboard</a></li>
        <li><a href="#">Users</a></li>
        <li><a href="#">Settings</a></li>
        <li><a href="#" onclick="downloadDoc('static/docs/example.pdf', 'example.pdf')">Download PDF</a></li>
        <li><a href="#" onclick="downloadDoc('static/docs/another.txt', 'another.txt')">Download TXT</a></li>
        </ul>
</div>
<div class="content">
    <h1>Admin Panel</h1>
</div>
<button id="sidebar-toggle"><i class="fas fa-bars"></i></button>
<button id="mobile-menu-toggle"><i class="fas fa-bars"></i></button>

<script>
// Функция для скачивания документации
function downloadDoc(docPath, fileName) {
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

function showNotification(message, type) {
    // Placeholder for notification function.  Replace with your actual notification logic.
    console.log(`Notification: ${message} (${type})`);
}

function viewDoc(docPath) {
    // Placeholder for viewDoc function. Replace with your actual viewDoc logic
    console.log(`Viewing document: ${docPath}`);
}


document.addEventListener('DOMContentLoaded', function() {
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
    topDropdownOverlay.addEventListener('click', function() {
        toggleTopMenu(false);
    });
    
    // Обработчики для пунктов меню в выпадающем меню
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
        const isVisible = sidebar.classList.contains('visible');

        // Если show не определен, инвертируем текущее состояние
        if (show === undefined) {
            show = !isVisible;
        }

        if (show) {
            sidebar.classList.add('visible');
            sidebarOverlay.classList.add('visible');
            document.body.classList.add('menu-open');

            // Меняем иконку на крестик
            if (mobileMenuToggle.querySelector('i')) {
                mobileMenuToggle.querySelector('i').className = 'fas fa-times';
            }

            // Скрываем индикатор свайпа
            if (swipeIndicator) {
                swipeIndicator.classList.remove('visible');
            }
        } else {
            sidebar.classList.remove('visible');
            sidebarOverlay.classList.remove('visible');
            document.body.classList.remove('menu-open');

            // Возвращаем иконку меню
            if (mobileMenuToggle.querySelector('i')) {
                mobileMenuToggle.querySelector('i').className = 'fas fa-bars';
            }
        }
    }

    // Показываем индикатор свайпа, если пользователь долго не открывал меню
    setTimeout(() => {
        if (swipeIndicator && window.innerWidth <= 768 && !sidebar.classList.contains('visible')) {
            swipeIndicator.classList.add('visible');

            // Скрываем индикатор через 5 секунд
            setTimeout(() => {
                swipeIndicator.classList.remove('visible');
            }, 5000);
        }
    }, 3000);
});
</script>
</body>
</html>