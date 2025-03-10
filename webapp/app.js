// Инициализация Telegram WebApp
let tg = window.Telegram.WebApp;
tg.expand();

// Переменные для работы с картой
let map;
let markers;
let allEvents = [];
let filteredEvents = [];

// DOM Elements from original code
const categoryFilter = document.getElementById('category-filter');
const centuryFilter = document.getElementById('century-filter');
const resetFiltersBtn = document.getElementById('reset-filters');
const eventDetails = document.getElementById('event-details');
const closeDetailsBtn = document.getElementById('close-details');
const eventTitle = document.getElementById('event-title');
const eventDate = document.getElementById('event-date');
const eventCategory = document.getElementById('event-category');
const eventDescription = document.getElementById('event-description');


// Инициализация карты после загрузки страницы
document.addEventListener('DOMContentLoaded', () => {
    // Создание карты с центром на России
    map = L.map('map').setView([61.5240, 105.3188], 4);

    // Добавление базового слоя карты
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Создание группы кластеров для маркеров
    markers = L.markerClusterGroup();

    // Загрузка исторических событий
    loadHistoricalEvents();

    // Обработчики событий для фильтров from original code
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
    document.getElementById('apply-filters').addEventListener('click', applyFilters);
    document.getElementById('reset-filters').addEventListener('click', resetFilters);

});

// Загрузка исторических событий с сервера
async function loadHistoricalEvents() {
    try {
        // Отображение индикатора загрузки
        const loadingMessage = document.createElement('div');
        loadingMessage.className = 'loading-message';
        loadingMessage.textContent = 'Загрузка исторических данных...';
        document.body.appendChild(loadingMessage);

        // Загрузка данных из JSON файла
        const response = await fetch('/api/events');
        const data = await response.json();

        // Сохранение загруженных событий
        allEvents = data.events || [];

        // Удаление индикатора загрузки
        document.body.removeChild(loadingMessage);

        // Отображение всех событий на карте
        displayEvents(allEvents);

    } catch (error) {
        console.error('Ошибка при загрузке исторических данных:', error);
        alert('Не удалось загрузить исторические данные. Попробуйте обновить страницу.');
    }
}

// Отображение событий на карте
function displayEvents(events) {
    // Очистка существующих маркеров
    markers.clearLayers();

    // Добавление новых маркеров для каждого события с координатами
    events.forEach(event => {
        if (event.location && event.location.lat && event.location.lng) {
            try {
                const lat = parseFloat(event.location.lat);
                const lng = parseFloat(event.location.lng);

                // Проверка валидности координат
                if (!isNaN(lat) && !isNaN(lng) && lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180) {
                    // Определение цвета маркера по категории
                    const colorMap = {
                        'Война': 'red',
                        'Политика': 'blue',
                        'Культура': 'green',
                        'Наука': 'purple',
                        'Экономика': 'orange',
                        'Религия': 'darkblue'
                    };

                    const color = colorMap[event.category] || 'gray';

                    // Создание HTML для всплывающего окна
                    const popupContent = `
                        <div class="event-popup">
                            <h3>${event.title || 'Без названия'}</h3>
                            <p><strong>Дата:</strong> ${event.date || 'Неизвестно'}</p>
                            <p><strong>Категория:</strong> ${event.category || 'Не указана'}</p>
                            <p>${event.description ? event.description.substring(0, 200) + '...' : 'Нет описания'}</p>
                        </div>
                    `;

                    // Создание маркера
                    const marker = L.marker([lat, lng], {
                        icon: L.icon({
                            iconUrl: `https://cdn.jsdelivr.net/npm/leaflet@1.7.1/dist/images/marker-icon.png`,
                            shadowUrl: `https://cdn.jsdelivr.net/npm/leaflet@1.7.1/dist/images/marker-shadow.png`,
                            iconSize: [25, 41],
                            iconAnchor: [12, 41],
                            popupAnchor: [1, -34],
                            shadowSize: [41, 41]
                        })
                    }).bindPopup(popupContent);

                    // Добавление маркера в группу кластеров
                    markers.addLayer(marker);
                }
            } catch (e) {
                console.error('Ошибка при создании маркера:', e, event);
            }
        }
    });

    // Добавление группы кластеров на карту
    map.addLayer(markers);

    // Перерисовка карты для корректного отображения
    map.invalidateSize();
}

// Применение фильтров к событиям
function applyFilters() {
    const categoryFilterValue = categoryFilter.value;
    const centuryFilterValue = centuryFilter.value;
    const startYear = parseInt(document.getElementById('start-year').value) || 800;
    const endYear = parseInt(document.getElementById('end-year').value) || 2023;

    // Фильтрация событий по выбранным критериям
    filteredEvents = allEvents.filter(event => {
        // Фильтр по категории
        if (categoryFilterValue !== 'all' && event.category !== categoryFilterValue) {
            return false;
        }

        // Фильтр по веку
        if (centuryFilterValue !== 'all') {
            const year = extractYearFromDate(event.date);
            if (!year || Math.ceil(year / 100) != centuryFilterValue) {
                return false;
            }
        }

        // Фильтр по году
        const eventYear = extractYearFromDate(event.date);
        if (eventYear && (eventYear < startYear || eventYear > endYear)) {
            return false;
        }

        return true;
    });

    // Отображение отфильтрованных событий
    displayEvents(filteredEvents);
}

// Сброс всех фильтров
function resetFilters() {
    document.getElementById('category-filter').value = 'all';
    document.getElementById('century-filter').value = 'all';
    document.getElementById('start-year').value = '';
    document.getElementById('end-year').value = '';

    // Отображение всех событий
    displayEvents(allEvents);
}

// Извлечение года из строки с датой
function extractYearFromDate(dateStr) {
    if (!dateStr) return null;

    // Поиск 3-4 значного числа в строке даты
    const yearMatch = dateStr.match(/\b(\d{3,4})\b/);
    return yearMatch ? parseInt(yearMatch[1]) : null;
}

// Show detailed event information from original code
function showEventDetails(event) {
    eventTitle.textContent = event.title;
    eventDate.textContent = event.date;
    eventCategory.textContent = event.category;
    eventDescription.textContent = event.description;
    eventDetails.classList.remove('hidden');
}