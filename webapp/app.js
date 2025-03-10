// Initialize Telegram WebApp
const tgApp = window.Telegram.WebApp;
tgApp.expand();

// Apply Telegram theme
document.documentElement.className = tgApp.colorScheme === 'dark' ? 'dark-theme' : '';

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
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    // Проверяем наличие кнопки администрирования
    const adminButton = document.getElementById('admin-button');
    if (adminButton) {
        adminButton.style.display = 'block';
        console.log('Кнопка администрирования найдена и отображена');
    }
});