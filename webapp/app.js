
// Инициализация Telegram WebApp
let tg = window.Telegram.WebApp;
tg.expand();

// Применяем темную тему, если она установлена в Telegram
if (tg.colorScheme === 'dark') {
    document.body.classList.add('dark-theme');
}

// Глобальные переменные
let map;
let markers = [];
let events = [];
let categories = [];
let currentPeriod = '';

// DOM элементы
const mapContainer = document.getElementById('map');
const loadingOverlay = document.getElementById('loadingOverlay');
const categorySelect = document.getElementById('categorySelect');
const searchInput = document.getElementById('searchInput');
const searchButton = document.getElementById('searchButton');
const eventList = document.getElementById('eventList');
const periodButtons = document.querySelectorAll('.period-button');
const eventDetailsPanel = document.getElementById('eventDetailsPanel');
const eventDetailsContent = document.getElementById('eventDetailsContent');
const closeEventDetails = document.getElementById('closeEventDetails');
const backToBot = document.getElementById('backToBot');

// Инициализация карты
function initMap() {
    showLoading();
    
    // Создаем карту с центром в России
    map = L.map('map').setView([55.751244, 37.618423], 4);
    
    // Добавляем тайлы OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    hideLoading();
    
    // Загружаем данные
    loadCategories();
    loadEvents();
}

// Функции для управления индикатором загрузки
function showLoading() {
    loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    loadingOverlay.style.display = 'none';
}

// Загружаем категории
function loadCategories() {
    fetch('/api/categories')
        .then(response => response.json())
        .then(data => {
            categories = data;
            console.log('Загружено категорий из API:', categories.length);
            
            // Очищаем текущие опции
            while (categorySelect.options.length > 1) {
                categorySelect.remove(1);
            }
            
            // Добавляем новые категории
            categories.forEach(category => {
                console.log('Добавлена категория:', category);
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                categorySelect.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Ошибка при загрузке категорий:', error);
        });
}

// Загружаем события
function loadEvents() {
    showLoading();
    
    fetch('/api/events')
        .then(response => response.json())
        .then(data => {
            events = data;
            console.log('Загружено событий из API:', events.length);
            hideLoading();
            
            // Проверяем URL-параметры для фильтрации
            const urlParams = new URLSearchParams(window.location.search);
            const eventId = urlParams.get('event');
            const periodParam = urlParams.get('period');
            const categoryParam = urlParams.get('category');
            const searchParam = urlParams.get('search');
            
            // Применяем фильтры из URL
            if (eventId) {
                showEventDetails(events.find(e => e.id === eventId));
            }
            if (periodParam) {
                setPeriod(periodParam);
            }
            if (categoryParam) {
                categorySelect.value = categoryParam;
            }
            if (searchParam) {
                searchInput.value = searchParam;
            }
            
            // Фильтруем и отображаем события
            filterAndDisplayEvents();
        })
        .catch(error => {
            console.error('Ошибка при загрузке событий:', error);
            hideLoading();
        });
}

// Фильтрация и отображение событий
function filterAndDisplayEvents() {
    showLoading();
    
    // Получаем значения фильтров
    const selectedCategory = categorySelect.value;
    const searchTerm = searchInput.value.toLowerCase();
    
    // Фильтруем события
    const filteredEvents = events.filter(event => {
        // Фильтр по категории
        if (selectedCategory && event.category !== selectedCategory) {
            return false;
        }
        
        // Фильтр по периоду
        if (currentPeriod) {
            switch (currentPeriod) {
                case 'ancient':
                    if (event.year > 1300) return false;
                    break;
                case 'middle':
                    if (event.year < 1300 || event.year > 1700) return false;
                    break;
                case 'empire':
                    if (event.year < 1700 || event.year > 1917) return false;
                    break;
                case 'soviet':
                    if (event.year < 1917 || event.year > 1991) return false;
                    break;
                case 'modern':
                    if (event.year < 1991) return false;
                    break;
            }
        }
        
        // Фильтр по поисковому запросу
        if (searchTerm && !event.name.toLowerCase().includes(searchTerm) && 
            !event.description.toLowerCase().includes(searchTerm)) {
            return false;
        }
        
        return true;
    });
    
    // Очищаем текущие маркеры
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
    
    // Обновляем список событий
    updateEventList(filteredEvents);
    
    // Добавляем маркеры на карту
    filteredEvents.forEach(event => {
        if (event.coordinates && event.coordinates.length === 2) {
            const marker = L.marker(event.coordinates)
                .addTo(map)
                .bindPopup(`<b>${event.name}</b><br>${event.year}`);
                
            marker.on('click', () => {
                showEventDetails(event);
            });
            
            markers.push(marker);
        }
    });
    
    // Если есть маркеры, подгоняем карту под них
    if (markers.length > 0) {
        const group = new L.featureGroup(markers);
        map.fitBounds(group.getBounds(), { padding: [50, 50] });
    }
    
    hideLoading();
}

// Обновляем список событий
function updateEventList(filteredEvents) {
    eventList.innerHTML = '';
    
    if (filteredEvents.length === 0) {
        const placeholder = document.createElement('p');
        placeholder.className = 'placeholder-text';
        placeholder.textContent = 'События не найдены. Попробуйте изменить параметры поиска.';
        eventList.appendChild(placeholder);
        return;
    }
    
    filteredEvents.forEach(event => {
        const eventItem = document.createElement('div');
        eventItem.className = 'event-item';
        eventItem.innerHTML = `
            <div class="event-title">${event.name}</div>
            <div class="event-date">${event.year}</div>
        `;
        
        eventItem.addEventListener('click', () => {
            showEventDetails(event);
            
            // Если есть координаты, находим нужный маркер и открываем его
            if (event.coordinates && event.coordinates.length === 2) {
                const foundMarker = markers.find(marker => {
                    const latLng = marker.getLatLng();
                    return latLng.lat === event.coordinates[0] && latLng.lng === event.coordinates[1];
                });
                
                if (foundMarker) {
                    map.setView(foundMarker.getLatLng(), 8);
                    foundMarker.openPopup();
                }
            }
        });
        
        eventList.appendChild(eventItem);
    });
}

// Показываем детали события
function showEventDetails(event) {
    if (!event) return;
    
    eventDetailsContent.innerHTML = `
        <h2 class="event-details-title">${event.name}</h2>
        <div class="event-details-date">${event.year}</div>
        <div class="event-details-description">${event.description}</div>
    `;
    
    eventDetailsPanel.style.display = 'block';
}

// Устанавливаем активный период
function setPeriod(period) {
    currentPeriod = period;
    
    // Обновляем активные кнопки
    periodButtons.forEach(button => {
        if (button.dataset.period === period) {
            button.classList.add('active');
        } else {
            button.classList.remove('active');
        }
    });
    
    // Фильтруем события
    filterAndDisplayEvents();
}

// Инициализация событий
document.addEventListener('DOMContentLoaded', () => {
    // Инициализируем карту
    initMap();
    
    // Слушатели событий для фильтров
    categorySelect.addEventListener('change', filterAndDisplayEvents);
    searchButton.addEventListener('click', filterAndDisplayEvents);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            filterAndDisplayEvents();
        }
    });
    
    // Слушатели для кнопок периодов
    periodButtons.forEach(button => {
        button.addEventListener('click', () => {
            setPeriod(button.dataset.period);
        });
    });
    
    // Кнопка закрытия панели деталей
    closeEventDetails.addEventListener('click', () => {
        eventDetailsPanel.style.display = 'none';
    });
    
    // Кнопка возврата в бота
    backToBot.addEventListener('click', () => {
        tg.close();
    });
});

// Обработка сообщений от бота
window.addEventListener('message', (event) => {
    if (event.data && event.data.action) {
        switch (event.data.action) {
            case 'showEvent':
                if (event.data.eventId) {
                    const foundEvent = events.find(e => e.id === event.data.eventId);
                    if (foundEvent) {
                        showEventDetails(foundEvent);
                    }
                }
                break;
            case 'setPeriod':
                if (event.data.period) {
                    setPeriod(event.data.period);
                }
                break;
        }
    }
});
