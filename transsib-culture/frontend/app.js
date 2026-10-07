// ---------- карта ----------
const map = L.map('map', {
  center: [55.1, 78.0],
  zoom: 6,
  zoomControl: false,
  worldCopyJump: true,
});
L.control.zoom({ position: 'bottomright' }).addTo(map);

L.tileLayer('https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png', {
  attribution: '© Stadia Maps, © OpenMapTiles, © OpenStreetMap',
  maxZoom: 20,
}).addTo(map);

const cluster = L.markerClusterGroup({
  maxClusterRadius: 50,
  spiderfyOnMaxZoom: true,
  showCoverageOnHover: false,
});
map.addLayer(cluster);

let railwayLayer = null;
let trainCoordsLayer = L.layerGroup().addTo(map);
let currentPlaceId = null;

// ---------- загрузка ЖД ----------
async function loadRailway() {
  const res = await fetch('/api/railway');
  const data = await res.json();
  data.forEach(r => {
    const layer = L.geoJSON(r.geojson, {
      style: { color: '#ffd166', weight: 4, opacity: 0.9 },
    }).addTo(map);
    if (!railwayLayer) railwayLayer = layer;
  });
}

// ---------- загрузка train_coord (опционально, круги) ----------
async function loadTrainCoords() {
  const res = await fetch('/api/train_coords');
  const data = await res.json();
  data.forEach(t => {
    L.circle([t.lat, t.lon], {
      radius: t.search_radius_m,
      color: '#3b82f6', weight: 1, fillOpacity: 0.05,
    }).addTo(trainCoordsLayer);
  });
}

// ---------- загрузка культурных мест (динамически по bbox/zoom) ----------
let lastKey = '';
async function loadPlaces() {
  const b = map.getBounds();
  const zoom = map.getZoom();
  const bbox = `${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`;
  const key = `${bbox}|${zoom}|${currentFilters.type1}|${currentFilters.type2}|${currentFilters.q}`;
  if (key === lastKey) return;
  lastKey = key;

  const params = new URLSearchParams({ bbox, zoom });
  if (currentFilters.type1) params.append('type1', currentFilters.type1);
  if (currentFilters.type2) params.append('type2', currentFilters.type2);
  if (currentFilters.q)    params.append('q', currentFilters.q);

  const res = await fetch(`/api/culture_places?${params}`);
  const places = await res.json();

  cluster.clearLayers();
  places.forEach(p => cluster.addLayer(makeMarker(p)));
}

function makeMarker(p) {
  const baseSize = 26;
  const size = Math.max(16, Math.min(48, baseSize * p.size_priority));

  const iconHtml = `
    <div class="marker-pin" style="background:${p.marker.color};width:${size}px;height:${size}px;">
      <i class="fa-solid ${p.marker.icon}" style="font-size:${size*0.45}px;"></i>
    </div>`;

  const icon = L.divIcon({
    html: iconHtml,
    className: '',
    iconSize: [size, size],
    iconAnchor: [size/2, size],
  });

  const marker = L.marker([p.lat, p.lon], { icon });
  marker.on('click', () => openCard(p, marker));
  return marker;
}

// ---------- карточка ----------
const card = document.getElementById('popup-card');
function openCard(p, marker) {
  currentPlaceId = p.id;
  document.getElementById('card-icon').innerHTML =
    `<i class="fa-solid ${p.marker.icon}" style="color:${p.marker.color}"></i>`;
  document.getElementById('card-name').textContent = p.name;
  document.getElementById('card-meta').textContent =
    `${p.type1 === 'human' ? 'Создано человеком' : 'Природа'} · ${p.type2}` +
    (p.creation_date ? ` · ${p.creation_date}` : '') +
    (p.rarity ? ` · ${p.rarity}` : '');
  document.getElementById('card-short').textContent = p.short_description;
  card.classList.remove('hidden');

  const pt = map.latLngToContainerPoint([p.lat, p.lon]);
  card.style.left = pt.x + 'px';
  card.style.top  = pt.y + 'px';
}
document.getElementById('close-card').onclick = () => card.classList.add('hidden');

// ---------- боковая панель ----------
document.getElementById('card-more').onclick = async () => {
  if (!currentPlaceId) return;
  const res = await fetch(`/api/culture_places/${currentPlaceId}`);
  const p = await res.json();
  document.getElementById('panel-name').textContent = p.name;
  document.getElementById('panel-meta').textContent =
    `${p.type1 === 'human' ? 'Создано человеком' : 'Природа'} · ${p.type2}` +
    (p.creation_date ? ` · ${p.creation_date}` : '');
  document.getElementById('panel-history').textContent = p.history || '—';
  const src = document.getElementById('panel-sources');
  src.innerHTML = (p.sources || []).map(s => `<li><a href="${s}" target="_blank">${s}</a></li>`).join('') || '<li>—</li>';
  document.getElementById('side-panel').classList.remove('hidden');
  card.classList.add('hidden');
};
document.getElementById('close-panel').onclick = () =>
  document.getElementById('side-panel').classList.add('hidden');

// ---------- легенда ----------
const LEGEND = [
  ['museum','#8e44ad','fa-landmark','Музей'],
  ['monument','#c0392b','fa-monument','Памятник'],
  ['architecture','#2980b9','fa-building','Архитектура'],
  ['theater','#e67e22','fa-masks-theater','Театр'],
  ['temple','#d4af37','fa-church','Храм'],
  ['lake','#1abc9c','fa-water','Озеро'],
  ['river','#16a085','fa-water','Река'],
  ['mountain','#7f8c8d','fa-mountain','Гора'],
  ['reserve','#27ae60','fa-tree','Заповедник'],
  ['forest','#2ecc71','fa-tree','Лес'],
  ['historic_nature','#f39c12','fa-scroll','Историческая природа'],
];
document.getElementById('legend-items').innerHTML = LEGEND.map(([_,c,i,n]) =>
  `<div class="legend-item"><span class="legend-dot" style="background:${c}"><i class="fa-solid ${i}"></i></span>${n}</div>`
).join('');
document.getElementById('legend-btn').onclick = () =>
  document.getElementById('legend-panel').classList.toggle('hidden');

// ---------- фильтры ----------
const currentFilters = { type1: '', type2: '', q: '' };
document.getElementById('filter-btn').onclick = () =>
  document.getElementById('filter-panel').classList.toggle('hidden');
document.getElementById('apply-filter').onclick = () => {
  currentFilters.type1 = document.getElementById('f-type1').value;
  currentFilters.type2 = document.getElementById('f-type2').value;
  lastKey = '';
  loadPlaces();
  document.getElementById('filter-panel').classList.add('hidden');
};

// ---------- поиск ----------
let searchTimer = null;
document.getElementById('search-input').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    currentFilters.q = e.target.value.trim();
    lastKey = '';
    loadPlaces();
  }, 300);
});

// ---------- реакция на движение карты ----------
map.on('moveend', () => { lastKey = ''; loadPlaces(); });

// ---------- старт ----------
loadRailway();
loadTrainCoords();
loadPlaces();