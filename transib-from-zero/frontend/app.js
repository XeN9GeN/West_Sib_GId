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

    const imageHtml = `<div class="popup-image-box">
        ${p.photo_url ? `<img src="${p.photo_url}" alt="${p.name}">` : 'Нет фото'}
    </div>`;

    const dateStr = p.creation_date ? ` • Год: ${p.creation_date}` : '';
    const fieldsHtml = `<div class="popup-fields">
        <h3>${p.name}</h3>
        <div><b>Тип:</b> ${type1Labels[p.type1]} • ${type2Labels[p.type2]}</div>
        <div><b>Координаты:</b> ${p.lat.toFixed(4)}, ${p.lon.toFixed(4)}${dateStr}</div>
    </div>`;

    const descHtml = `<div class="popup-description">
        ${p.history || p.short_description || 'Описание отсутствует.'}
    </div>`;

    let sourcesHtml = '';
    if (p.sources && p.sources.length > 0) {
        const links = p.sources.map(url => `<a href="${url}" target="_blank">${url}</a>`).join('');
        sourcesHtml = `<div class="popup-sources"><b>Источники:</b><br>${links}</div>`;
    }

    return `<div class="popup-card">
        <div class="popup-header">${iconHtml}${imageHtml}</div>
        ${fieldsHtml}
        ${descHtml}
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
        li.innerHTML = `<span style="display:inline-block; width:10px; height:10px; background:${place.marker.color}; border-radius:50%; margin-right:8px;"></span> ${place.name}`;
        
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
    allPlaces = await response.json();

    renderMarkers();
}

let railwayLayer = null;
let showRailway = true;
async function loadRailway() {
    const response = await fetch('/api/railway');
    const data = await response.json();
    
    if (data.geometry) {
        railwayLayer = L.geoJSON(data.geometry, {
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
initLegend();