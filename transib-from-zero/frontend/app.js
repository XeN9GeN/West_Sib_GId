const map = L.map('map').setView([55.0, 78.0], 6);

L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap'
}).addTo(map);


const markerLayer = L.layerGroup().addTo(map);

let allPlaces = [];//all downloaded place
let searchQuery = "";
let highlightedPlaceId = null;

const hiddenTypes = {
    type1: new Set(),
    type2: new Set()
};

const type1Labels = {human: "Искусственный", nature: "Природные" };
const type2Labels = {
    museum: "Музеи", monument: "Памятники", architecture: "Архитектура",
    theater: "Театры", temple: "Храмы", lake: "Озера",
    river: "Реки", reserve: "Заповедники", forest: "Леса",
    historic_nature: "Истор. природа"
};



function initLegend(){
    const type1Container = document.getElementById('type1-list');//<ul id="type1-list"></ul>
    const type2Container = document.getElementById('type2-list');

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


function renderMarkers() {
    markerLayer.clearLayers();

    allPlaces.forEach(p => {
        //скрыт ли type1 и type2
        const isType1Hidden = hiddenTypes.type1.has(p.type1);
        const isType2Hidden = hiddenTypes.type2.has(p.type2);

        const matchesSearch = p.name.toLowerCase().includes(searchQuery);


        //Если оба типа включены - рисуем маркер
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
            
            L.marker([p.lat, p.lon], { icon: icon }).bindPopup(`<b>${p.name}</b>`).addTo(markerLayer);
        }
    });
}



async function loadPlaces(){
    const bounds = map.getBounds();

    const bbox = `${bounds.getWest()},${bounds.getSouth()},${bounds.getEast()},${bounds.getNorth()}`;//взять границы карты на экране

    const response = await fetch(`/api/culture_places?bbox=${bbox}`);//формирует шттп запрос и передаёт сетевому стеку ОС, оно отправляет в loclhost:8000
    allPlaces  = await response.json();

    renderMarkers();
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
                    const latlng = layer.getLatLng();
                    if (latlng.lat === foundPlace.lat && latlng.lng === foundPlace.lon) {
                        layer.openPopup();
                    }
                });
            });
        } else {
            alert("Объект с таким названием не найден на текущей карте.");
        }
    }
});


document.getElementById('search-input').addEventListener('input', (e) => {
    searchQuery = e.target.value.trim().toLowerCase();
    renderMarkers();
});

document.getElementById('legend-btn').onclick = () => {
    document.getElementById('legend-panel').classList.toggle('active');
};


loadPlaces();
map.on('moveend',loadPlaces);
initLegend();