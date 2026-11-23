const map = L.map('map').setView([55.0, 78.0], 6);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
}).addTo(map);

const markerLayer = L.markerClusterGroup().addTo(map);

let allPlaces = [];
let searchQuery = "";
let highlightedPlaceId = null;

let taxonomy = null;
const hiddenTypes = {
    category: new Set(),
    object_class: new Set()
};
let placeLoadTimer = null;
let placeLoadController = null;

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    })[character]);
}

function safeHttpUrl(value) {
    if (!value) return null;
    try {
        const url = new URL(value, window.location.origin);
        return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
    } catch {
        return null;
    }
}

function getPlaceDescription(place) {
    return typeof place.effective_description === 'string'
        && place.effective_description.trim()
        ? place.effective_description.trim()
        : null;
}

function getAiSummarySourcesHtml(place) {
    if (place.effective_description_source !== 'ai_summary') return '';
    const sources = Array.isArray(place.ai_summary_sources)
        ? place.ai_summary_sources
        : [];
    if (!sources.length) return '';

    const links = sources.map(source => {
        const url = safeHttpUrl(source.url);
        if (!url) return '';
        const label = source.title || new URL(url).hostname.replace(/^www\./, '');
        return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
    }).filter(Boolean).join('<br>');
    return links
        ? `<div class="popup-sources"><b>Источники сводки:</b><br>${links}</div>`
        : '';
}

function getSubcategoryLabel(subcategoryId) {
    if (!taxonomy || !subcategoryId) return null;
    for (const category of taxonomy.categories) {
        for (const subcategory of category.subcategories) {
            if (subcategory.id === subcategoryId) return subcategory.label;
        }
    }
    return null;
}

function getObjectClassLabel(objectClassId) {
    if (!taxonomy || !objectClassId) return null;
    const objectClass = taxonomy.object_classes.find(item => item.id === objectClassId);
    return objectClass ? objectClass.label : null;
}


function initLegend() {
    if (!taxonomy) return;
    const classContainer = document.getElementById('object-class-list');
    const categoryContainer = document.getElementById('category-list');

    const railwayContainer = document.getElementById('railway-list');
    const railwayDiv = document.createElement('div');
    railwayDiv.className = 'legend-item';
    railwayDiv.innerHTML = `<span>Транссиб</span><span class="flag on" id="flag-railway">+</span>`;
    railwayDiv.onclick = toggleRailway;
    railwayContainer.appendChild(railwayDiv);

    taxonomy.object_classes.forEach(objectClass => {
        const div = document.createElement('div');
        div.className = 'legend-item';
        const flagId = `flag-class-${objectClass.id}`;
        div.innerHTML = `<span>${escapeHtml(objectClass.label)}</span><span class="flag on" id="${flagId}">+</span>`;
        div.onclick = () => toggleFilter('object_class', objectClass.id, flagId);
        classContainer.appendChild(div);
    });

    taxonomy.categories.forEach(category => {
        const div = document.createElement('div');
        div.className = 'legend-item';
        const flagId = `flag-category-${category.id}`;
        div.innerHTML = `<span>${escapeHtml(category.label)}</span><span class="flag on" id="${flagId}">+</span>`;
        div.onclick = () => toggleFilter('category', category.id, flagId);
        categoryContainer.appendChild(div);

        category.subcategories.forEach(subcategory => {
            const subDiv = document.createElement('div');
            subDiv.className = 'legend-subcategory';
            subDiv.innerHTML = `<span class="legend-subcategory-mark" style="background:${escapeHtml(subcategory.marker.color)}"></span>${escapeHtml(subcategory.label)}`;
            categoryContainer.appendChild(subDiv);
        });
    });
}

function toggleFilter(typeCategory, typeValue, flagId) {
    const set = hiddenTypes[typeCategory];
    const flagEl = document.getElementById(flagId);

    if (set.has(typeValue)) {
        set.delete(typeValue);
        flagEl.textContent = '+';
        flagEl.className = 'flag on';
    } else {
        set.add(typeValue);
        flagEl.textContent = '-';
        flagEl.className = 'flag off';
    }

    renderMarkers();
}

function getPopupContent(p) {
    const iconHtml = `<div class="popup-icon-box" style="color:${p.marker.color}">
        <i class="fa-solid ${p.marker.icon}"></i>
    </div>`;

    const photoUrl = safeHttpUrl(p.photo_url);
    const imageHtml = `<div class="popup-image-box">
        ${photoUrl ? `<img src="${escapeHtml(photoUrl)}" alt="${escapeHtml(p.name)}">` : 'Нет фото'}
    </div>`;
    const attributionHtml = p.photo_attribution
        ? `<div class="popup-photo-attribution">${escapeHtml(p.photo_attribution)}</div>`
        : '';

    const dateStr = p.creation_date ? ` • Год: ${p.creation_date}` : '';
    const subcategory = getSubcategoryLabel(p.subcategory);
    const objectClass = getObjectClassLabel(p.object_class);
    const demoHtml = p.origin === 'demo'
        ? '<div><b>Демонстрационный объект</b></div>'
        : '';
    const fieldsHtml = `<div class="popup-fields">
        <h3>${escapeHtml(p.name)}</h3>
        <div><b>Подкатегория:</b> ${escapeHtml(subcategory || p.subcategory || 'Не указана')}</div>
        <div><b>Класс:</b> ${escapeHtml(objectClass || p.object_class || 'Не указан')}</div>
        ${demoHtml}
        <div><b>Координаты:</b> ${p.lat.toFixed(4)}, ${p.lon.toFixed(4)}${dateStr}</div>
    </div>`;

    const effectiveDescription = getPlaceDescription(p);
    const descHtml = effectiveDescription
        ? `<div class="popup-description">${escapeHtml(effectiveDescription)}</div>`
        : `<div class="popup-subcategory-label">${escapeHtml(subcategory || 'Подкатегория не указана')}</div>`;
    const aiSourcesHtml = getAiSummarySourcesHtml(p);

    let sourcesHtml = '';
    if (p.sources && p.sources.length > 0) {
        const links = p.sources.map(source => {
            const url = safeHttpUrl(source);
            if (!url) return '';
            const label = new URL(url).hostname.replace(/^www\./, '');
            return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`;
        }).filter(Boolean).join('');
        sourcesHtml = `<div class="popup-sources"><b>Источники:</b><br>${links}</div>`;
    }

    return `<div class="popup-card">
        <div class="popup-header">${iconHtml}${imageHtml}</div>
        ${attributionHtml}
        ${fieldsHtml}
        ${descHtml}
        ${aiSourcesHtml}
        ${sourcesHtml}
    </div>`;
}

const markerRegistry = {}; 
function renderMarkers() {
    markerLayer.clearLayers();

    for (let key in markerRegistry) delete markerRegistry[key]; 

    allPlaces.forEach(p => {
        const isCategoryHidden = hiddenTypes.category.has(p.category);
        const isObjectClassHidden = hiddenTypes.object_class.has(p.object_class);
        const matchesSearch = p.name.toLowerCase().includes(searchQuery);

        if (!isCategoryHidden && !isObjectClassHidden && matchesSearch) {
            const isHighlighted = (p.id === highlightedPlaceId);
            
            const size = isHighlighted ? 36 : 20;
            const anchor = size / 2;
            const border = isHighlighted ? '3px solid #f1c40f' : '2px solid white';

            const icon = L.divIcon({
                html: `<div style="
                    background:${p.marker.color}; 
                    width: ${size}px; 
                    height: ${size}px; 
                    border-radius: 50%; 
                    border: ${border}; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.6);
                    transition: all 0.3s ease;
                "></div>`,
                className: '', 
                iconSize: [size, size],
                iconAnchor: [anchor, anchor]
            });
            
            const marker = L.marker([p.lat, p.lon], { icon: icon }).addTo(markerLayer);
            marker.placeId = p.id;
    
            marker.bindPopup(getPopupContent(p), {
                className: 'custom-popup',
                maxWidth: 350,
                minWidth: 350,
                autoPanPadding: [50, 50]
            });

            markerRegistry[p.id] = marker;
        }
    });
    renderSidebar();
}
function renderSidebar() {
    const listContainer = document.getElementById('places-list');
    listContainer.innerHTML = '';

    allPlaces.forEach(place => {
        const marker = markerRegistry[place.id];
        if (!marker) return;

        const li = document.createElement('li');
        li.innerHTML = `<span style="display:inline-block; width:10px; height:10px; background:${place.marker.color}; border-radius:50%; margin-right:8px;"></span> ${escapeHtml(place.name)}`;
        
        li.onclick = () => {
            map.flyTo([place.lat, place.lon], 15, { duration: 1 });
            map.once('moveend', () => marker.openPopup());
        };
        
        listContainer.appendChild(li);
    });
}


async function loadPlaces() {
    const bounds = map.getBounds();
    const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;
    if (placeLoadController) placeLoadController.abort();
    placeLoadController = new AbortController();

    const params = new URLSearchParams({
        bbox,
        zoom: String(map.getZoom())
    });
    const statusElement = document.getElementById('load-status');
    try {
        const response = await fetch(`/api/culture_places?${params}`, {
            signal: placeLoadController.signal
        });
        if (!response.ok) throw new Error(`Не удалось загрузить объекты культуры: ${response.status}`);
        const places = await response.json();
        if (!Array.isArray(places)) throw new Error('API вернул некорректный список объектов культуры.');

        allPlaces = places;
        if (statusElement) {
            if (response.headers.get('X-Truncated') === 'true') {
                statusElement.textContent = 'Показана неполная выборка объектов.';
            } else {
                statusElement.textContent = '';
            }
        }
        renderMarkers();
    } catch (error) {
        if (error.name === 'AbortError') return;
        allPlaces = [];
        renderMarkers();
        if (statusElement) statusElement.textContent = escapeHtml(error.message);
    }
}

function schedulePlaceLoad() {
    if (placeLoadTimer) window.clearTimeout(placeLoadTimer);
    placeLoadTimer = window.setTimeout(loadPlaces, 250);
}

async function loadTaxonomy() {
    const statusElement = document.getElementById('load-status');
    try {
        const response = await fetch('/api/taxonomy');
        if (!response.ok) throw new Error(`Не удалось загрузить легенду: ${response.status}`);
        const data = await response.json();
        if (!Array.isArray(data.categories) || !Array.isArray(data.object_classes)) {
            throw new Error('API вернул некорректную схему таксономии.');
        }
        taxonomy = data;
        initLegend();
        if (statusElement) statusElement.textContent = '';
    } catch (error) {
        taxonomy = null;
        allPlaces = [];
        renderMarkers();
        if (statusElement) {
            statusElement.textContent = `Ошибка загрузки легенды: ${escapeHtml(error.message)}`;
        }
    }
}

let railwayLayer = null;
let showRailway = true;
let railwayDetailLevel = null;
const railwayGeometryCache = new Map();

function getRailwayDetailLevel(zoom) {
    return Math.max(4, Math.min(18, Math.floor(zoom / 2) * 2));
}

async function loadRailway() {
    const detailLevel = getRailwayDetailLevel(map.getZoom());
    if (detailLevel === railwayDetailLevel) return;

    let geometry = railwayGeometryCache.get(detailLevel);
    if (!geometry) {
        const response = await fetch(`/api/railway?zoom=${map.getZoom()}`);
        if (!response.ok) throw new Error(`Не удалось загрузить линию ЖД: ${response.status}`);
        const data = await response.json();
        geometry = data.geometry;
        if (geometry) railwayGeometryCache.set(detailLevel, geometry);
    }

    if (detailLevel !== getRailwayDetailLevel(map.getZoom())) return;

    railwayDetailLevel = detailLevel;
    if (railwayLayer) map.removeLayer(railwayLayer);

    if (geometry) {
        railwayLayer = L.geoJSON(geometry, {
            style: {
                color: '#2c3e50',
                weight: 4,
                dashArray: '10, 10',
                opacity: 0.8
            }
        });
        
        if (showRailway) {
            railwayLayer.addTo(map);
        }
    } else {
        railwayLayer = null;
    }
}

function toggleRailway() {
    showRailway = !showRailway;
    const flagEl = document.getElementById('flag-railway');
    
    if (showRailway) {
        flagEl.textContent = '+';
        flagEl.className = 'flag on';
        if (railwayLayer) railwayLayer.addTo(map);
    } else {
        flagEl.textContent = '-';
        flagEl.className = 'flag off';
        if (railwayLayer) map.removeLayer(railwayLayer);
    }
}



const searchInput = document.getElementById('search-input');

searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value.trim().toLowerCase();
    
    if (searchQuery === "") {
        highlightedPlaceId = null;
    }
    
    renderMarkers();
});

searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        if (searchQuery === "") return;

        const foundPlace = allPlaces.find(p => 
            p.name.toLowerCase().includes(searchQuery)
        );

        if (foundPlace) {
            highlightedPlaceId = foundPlace.id;
            renderMarkers();

            map.flyTo([foundPlace.lat, foundPlace.lon], 14, {
                duration: 1.5
            });

            map.once('moveend', () => {
                markerLayer.eachLayer(layer => {
                    if (layer.placeId === foundPlace.id) {
                        layer.openPopup();
                    }
                });
            });
        } else {
            alert("Объект с таким названием не найден на текущей карте.");
        }
    }
});

document.getElementById('legend-btn').onclick = () => {
    document.getElementById('legend-panel').classList.toggle('active');
};

loadRailway();
loadTaxonomy().then(schedulePlaceLoad);
map.on('moveend', schedulePlaceLoad);
map.on('zoomend', loadRailway);