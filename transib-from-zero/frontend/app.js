const map = L.map('map').setView([55.0, 78.0], 6);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
}).addTo(map);

const markerLayer = L.markerClusterGroup().addTo(map);

let allPlaces = [];
let searchQuery = "";
let highlightedPlaceId = null;

const hiddenTypes = {
    type1: new Set(),
    type2: new Set()
};

const type1Labels = { human: "Искусственный", nature: "Природные" };
const type2Labels = {
    museum: "Музеи", monument: "Памятники", architecture: "Архитектура",
    theater: "Театры", temple: "Храмы", lake: "Озера",
    river: "Реки", reserve: "Заповедники", forest: "Леса",
    historic_nature: "Истор. природа"
};
const type2DescriptionLabels = {
    museum: "Музей",
    monument: "Памятник",
    architecture: "Архитектурный объект",
    theater: "Театр",
    temple: "Храм",
    lake: "Озеро",
    river: "Река",
    reserve: "Заповедник",
    forest: "Лес",
    historic_nature: "Природный объект с историческим значением"
};

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
    const description = [place.history, place.short_description, place.ai_summary]
        .find(value => typeof value === 'string' && value.trim());
    return description
        ? description.trim()
        : type2DescriptionLabels[place.type2] || 'Объект культуры';
}

function getAiSummarySourcesHtml(place) {
    const sources = Array.isArray(place.ai_summary_sources)
        ? place.ai_summary_sources
        : [];
    const hasExistingDescription = [place.history, place.short_description]
        .some(value => typeof value === 'string' && value.trim());
    if (hasExistingDescription || !place.ai_summary || !sources.length) return '';

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


function initLegend() {
    const type1Container = document.getElementById('type1-list');
    const type2Container = document.getElementById('type2-list');
    
    const railwayContainer = document.getElementById('railway-list');
    const railwayDiv = document.createElement('div');
    railwayDiv.className = 'legend-item';
    railwayDiv.innerHTML = `<span>Транссиб</span><span class="flag on" id="flag-railway">+</span>`;
    railwayDiv.onclick = toggleRailway;
    railwayContainer.appendChild(railwayDiv);

    Object.keys(type1Labels).forEach(key => {
        const div = document.createElement('div');
        div.className = 'legend-item';
        div.innerHTML = `<span>${type1Labels[key]}</span><span class="flag on" id="flag-t1-${key}">+</span>`;
        div.onclick = () => toggleFilter('type1', key, `flag-t1-${key}`);
        type1Container.appendChild(div);
    });

    Object.keys(type2Labels).forEach(key => {
        const div = document.createElement('div');
        div.className = 'legend-item';
        div.innerHTML = `<span>${type2Labels[key]}</span><span class="flag on" id="flag-t2-${key}">+</span>`;
        div.onclick = () => toggleFilter('type2', key, `flag-t2-${key}`);
        type2Container.appendChild(div);
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
    const fieldsHtml = `<div class="popup-fields">
        <h3>${escapeHtml(p.name)}</h3>
        <div><b>Тип:</b> ${escapeHtml(type1Labels[p.type1] || p.type1)} • ${escapeHtml(type2Labels[p.type2] || p.type2)}</div>
        <div><b>Координаты:</b> ${p.lat.toFixed(4)}, ${p.lon.toFixed(4)}${dateStr}</div>
    </div>`;

    const descHtml = `<div class="popup-description">
        ${escapeHtml(getPlaceDescription(p))}
    </div>`;
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
        const isType1Hidden = hiddenTypes.type1.has(p.type1);
        const isType2Hidden = hiddenTypes.type2.has(p.type2);
        const matchesSearch = p.name.toLowerCase().includes(searchQuery);

        if (!isType1Hidden && !isType2Hidden && matchesSearch) {
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

    const response = await fetch(`/api/culture_places?bbox=${bbox}`);
    if (!response.ok) throw new Error(`Не удалось загрузить объекты культуры: ${response.status}`);
    allPlaces = await response.json();
    if (!Array.isArray(allPlaces)) throw new Error('API вернул некорректный список объектов культуры.');

    renderMarkers();
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
loadPlaces();
map.on('moveend', loadPlaces);
map.on('zoomend', loadRailway);
initLegend();