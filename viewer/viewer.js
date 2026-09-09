// QS Quantification Engine — Interactive CAD & Takeoff Viewer
// Blueprint Section 36 & 43: High-Performance Canvas with Professional BOQ View & Evidence Audit

let drawingData = null;
let canvas, ctx;
let scale = 0.08;
let panX = 150, panY = 400;
let isDragging = false;
let startX, startY;
let dragDist = 0;
let selectedRoom = null;
let hoveredRoom = null;
let activeLayers = new Set();
let currentTab = 'summary'; // 'summary' | 'pricing' | 'rooms'
let currentTradeFilter = 'all'; // 'all' | 'flooring' | 'partitions' | 'doors' | 'ceilings' | 'fixtures'
let activeFinishFilter = null; // e.g. 'FL-01' or null
let searchQuery = '';
let currentDrawingId = null;
let currentFileName = "";
let sampleProjectsList = [];

// Commercial Fitout Unit Standards (All Areas in SQFT, Lengths in RFT)
const SQM_TO_SQFT = 10.7639104;
const M_TO_RFT = 3.2808399;

function formatQuantityAndUnit(rawQty, rawUnit) {
  let q = typeof rawQty === 'number' ? rawQty : (parseFloat(rawQty) || 0);
  const u = (rawUnit || '').toLowerCase().trim();
  if (u === 'sqm' || u === 'm²' || u === 'sq.m' || u === 'sq m') {
    const sqft = q * SQM_TO_SQFT;
    return {
      qty: (sqft >= 100 ? sqft.toFixed(0) : sqft.toFixed(1)),
      unit: 'sqft',
      rawQty: sqft
    };
  }
  if (u === 'm' || u === 'rm' || u === 'rmt' || u === 'meter' || u === 'meters') {
    const rft = q * M_TO_RFT;
    return {
      qty: (rft >= 100 ? rft.toFixed(0) : rft.toFixed(1)),
      unit: 'Rft',
      rawQty: rft
    };
  }
  return {
    qty: (q % 1 === 0 ? q.toFixed(0) : q.toFixed(1)),
    unit: rawUnit || 'nos',
    rawQty: q
  };
}

const TRADE_COLOR_MAP = {
  walls: { color: "#0f172a", width: 2.6, dash: [] },
  glazing: { color: "#0284c7", width: 2.0, dash: [] },
  doors: { color: "#ea580c", width: 1.8, dash: [] },
  ceilings: { color: "#7c3aed", width: 1.4, dash: [5, 4] },
  furniture: { color: "#d97706", width: 1.3, dash: [] },
  fixtures: { color: "#b45309", width: 1.5, dash: [] },
  plumbing: { color: "#0d9488", width: 1.6, dash: [] },
  annotations: { color: "#64748b", width: 1.0, dash: [] },
  default: { color: "#475569", width: 1.2, dash: [] }
};

function getLayerStyle(layerName) {
  if (!layerName) return TRADE_COLOR_MAP.default;
  const l = layerName.toUpperCase();
  if (l.includes("GLAZ") || l.includes("GLASS") || l.includes("STOREFRONT")) {
    return TRADE_COLOR_MAP.glazing;
  }
  if (l.includes("WALL") || l.includes("PARTITION") || l.includes("STUD") || l.includes("BLOCK") || l.includes("LEAD") || l.startsWith("A-WALL")) {
    return TRADE_COLOR_MAP.walls;
  }
  if (l.includes("DOOR") || l.includes("SWING") || l.includes("SLIDER") || l.includes("FITTING") || l.startsWith("A-DOOR")) {
    return TRADE_COLOR_MAP.doors;
  }
  if (l.includes("CEIL") || l.includes("COFFER") || l.includes("SOFFIT")) {
    return TRADE_COLOR_MAP.ceilings;
  }
  if (l.includes("FURN") || l.includes("MILLWORK") || l.includes("BANQUETTE") || l.includes("WORKSTATION")) {
    return TRADE_COLOR_MAP.furniture;
  }
  if (l.includes("ELEC") || l.includes("LIGHT") || l.includes("FIXTURE")) {
    return TRADE_COLOR_MAP.fixtures;
  }
  if (l.includes("PLUMB") || l.includes("SANITARY") || l.includes("WET")) {
    return TRADE_COLOR_MAP.plumbing;
  }
  if (l.includes("ANNO") || l.includes("DIM") || l.includes("TEXT") || l.startsWith("A-ANNO")) {
    return TRADE_COLOR_MAP.annotations;
  }
  return TRADE_COLOR_MAP.default;
}

// Color Palette for Floor Finishes (IS 1200 / POMI Interior Takeoffs)
const FINISH_PALETTE = {
  "FL-01": { fill: "rgba(2, 132, 199, 0.12)", stroke: "#0284c7", name: "Italian Marble / Vitrified Tile" },
  "FL-02": { fill: "rgba(124, 58, 237, 0.12)", stroke: "#7c3aed", name: "Acoustic Carpet Tile" },
  "FL-03": { fill: "rgba(5, 150, 105, 0.12)", stroke: "#059669", name: "Antibacterial Seamless Vinyl" },
  "FL-04": { fill: "rgba(234, 88, 12, 0.12)", stroke: "#ea580c", name: "Anti-Skid Vitrified Tile" },
  "FL-05": { fill: "rgba(219, 39, 119, 0.12)", stroke: "#db2777", name: "Anti-Static Raised Access Floor" }
};

function getRoomFinishStyle(room) {
  const code = (room.finish_code || "").trim();
  if (FINISH_PALETTE[code]) return FINISH_PALETTE[code];

  // Professional architectural heuristics for commercial office fitouts
  const name = (room.name || "").toUpperCase();
  if (name.includes("SERVER") || name.includes("UPS") || name.includes("BATTERY")) {
    return FINISH_PALETTE["FL-05"];
  }
  if (name.includes("LIVING") || name.includes("FOYER") || name.includes("LOBBY") || name.includes("RECEPTION") || name.includes("PANTRY") || name.includes("CAFETERIA") || name.includes("BREAKOUT") || name.includes("PASSAGE")) {
    return FINISH_PALETTE["FL-01"];
  }
  if (name.includes("CONF") || name.includes("BOARD") || name.includes("OFFICE") || name.includes("CHAMBER") || name.includes("STUDIO") || name.includes("WORKSTATION") || name.includes("CABIN") || name.includes("MEETING") || name.includes("ASSOCIATE")) {
    return FINISH_PALETTE["FL-02"];
  }
  if (name.includes("CLINIC") || name.includes("SURGERY") || name.includes("LAB") || name.includes("DENTAL")) {
    return FINISH_PALETTE["FL-03"];
  }
  return { fill: "rgba(15, 23, 42, 0.04)", stroke: "rgba(15, 23, 42, 0.2)", name: "Standard Floor" };
}

window.addEventListener('DOMContentLoaded', init);

async function init() {
  canvas = document.getElementById('cadCanvas');
  ctx = canvas.getContext('2d');
  resizeCanvas();
  window.addEventListener('resize', resizeCanvas);

  setupTabControls();
  setupTradeFilterControls();
  setupSearchAndQuickFilters();
  setupInteractions();
  await loadSampleProjectsCatalog();

  // Clean start: Ready for user drawing upload (no dummy project preloaded)
  setupUI();
  render();
}

function resizeCanvas() {
  const container = canvas.parentElement;
  canvas.width = container.clientWidth;
  canvas.height = container.clientHeight;
  render();
}

function updateZoomDisplay() {
  const info = document.getElementById('zoomLevelInfo');
  if (info) {
    info.innerText = `${Math.round(scale * 1000)}%`;
  }
}

async function loadSampleProjectsCatalog() {
  try {
    const res = await fetch('/v1/samples');
    if (res.ok) {
      sampleProjectsList = await res.json();
      const select = document.getElementById('sampleSelect');
      if (select) {
        select.innerHTML = '';
        const defaultOpt = document.createElement('option');
        defaultOpt.value = "";
        defaultOpt.disabled = true;
        defaultOpt.selected = true;
        defaultOpt.textContent = "📁 Sample Benchmarks ▾";
        select.appendChild(defaultOpt);

        const optGroupInterior = document.createElement('optgroup');
        optGroupInterior.label = "🌟 Specialized Interior Fit-Out Projects";
        const optGroupGeneral = document.createElement('optgroup');
        optGroupGeneral.label = "📐 Standard Architectural Benchmarks";

        sampleProjectsList.forEach(p => {
          const opt = document.createElement('option');
          opt.value = p.filename;
          opt.textContent = `${p.title} (${p.format})`;
          if (p.filename.includes("PROJECT_2") || p.filename.includes("PROJECT_30")) {
            optGroupInterior.appendChild(opt);
          } else {
            optGroupGeneral.appendChild(opt);
          }
        });

        if (optGroupInterior.children.length > 0) select.appendChild(optGroupInterior);
        if (optGroupGeneral.children.length > 0) select.appendChild(optGroupGeneral);

        select.onchange = async (e) => {
          const fname = e.target.value;
          if (fname) {
            await loadSampleDrawingByName(fname);
          }
        };
      }
    }
  } catch (err) {
    console.error("Failed to load sample projects catalog:", err);
  }
}

async function loadSampleDrawingByName(filename) {
  const metaBadge = document.getElementById('drawingMeta');
  const statusBadge = document.getElementById('engineStatusBadge');

  metaBadge.innerText = `Loading ${filename}...`;
  statusBadge.innerText = "Loading Layout...";
  statusBadge.className = "badge";

  try {
    const res = await fetch(`/v1/samples/${encodeURIComponent(filename)}/load`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Could not load sample: ${res.statusText}`);
    const uploadData = await res.json();
    currentDrawingId = uploadData.drawing_id;
    currentFileName = filename;

    await runTakeoff(currentDrawingId, currentFileName);
  } catch (err) {
    console.error("Error loading sample drawing:", err);
    statusBadge.innerText = "Sample Load Error";
    statusBadge.className = "badge";
    alert(`Could not load project: ${err.message}`);
  }
}

function setupTradeFilterControls() {
  const bar = document.getElementById('tradeFilterBar');
  if (!bar) return;

  bar.querySelectorAll('.trade-btn').forEach(btn => {
    btn.onclick = () => {
      bar.querySelectorAll('.trade-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentTradeFilter = btn.getAttribute('data-trade') || 'all';
      applyTradeFilter(currentTradeFilter);
    };
  });
}

function applyTradeFilter(trade) {
  if (!drawingData) return;

  activeLayers.clear();
  const allLayers = drawingData.layers || [];

  if (trade === 'all') {
    allLayers.forEach(l => activeLayers.add(l));
    activeLayers.add("ROOM_OVERLAYS");
    if (drawingData.fixtures && drawingData.fixtures.length > 0) activeLayers.add("LIGHTING_FIXTURES");
  } else if (trade === 'flooring') {
    // Isolate rooms and floor boundaries
    activeLayers.add("ROOM_OVERLAYS");
    allLayers.forEach(l => {
      const u = l.toUpperCase();
      if (u.includes("WALL") || u.includes("PARTITION") || u.includes("BORDER") || u.includes("ANNO")) {
        activeLayers.add(l);
      }
    });
  } else if (trade === 'partitions') {
    // Isolate walls and glass partitions
    allLayers.forEach(l => {
      const u = l.toUpperCase();
      if (u.includes("WALL") || u.includes("PARTITION") || u.includes("STUD") || u.includes("GLAZ") || u.includes("GLASS") || u.includes("BLOCK") || u.startsWith("A-WALL")) {
        activeLayers.add(l);
      }
    });
    activeLayers.add("ROOM_OVERLAYS");
  } else if (trade === 'doors') {
    // Isolate door swings, pocket sliders, and wall frames
    allLayers.forEach(l => {
      const u = l.toUpperCase();
      if (u.includes("DOOR") || u.includes("SWING") || u.includes("SLIDER") || u.includes("FITTING") || u.includes("WALL") || u.startsWith("A-DOOR") || u.startsWith("A-WALL")) {
        activeLayers.add(l);
      }
    });
  } else if (trade === 'ceilings') {
    // Isolate false ceilings, coffer drops, and rooms
    allLayers.forEach(l => {
      const u = l.toUpperCase();
      if (u.includes("CEIL") || u.includes("COFFER") || u.includes("SOFFIT") || u.includes("WALL")) {
        activeLayers.add(l);
      }
    });
    activeLayers.add("ROOM_OVERLAYS");
  } else if (trade === 'fixtures') {
    // Isolate lighting, workstations, furniture
    allLayers.forEach(l => {
      const u = l.toUpperCase();
      if (u.includes("FURN") || u.includes("WORKSTATION") || u.includes("SEATING") || u.includes("DESK") || u.includes("TABLE") || u.includes("CHAIR") || u.includes("ELEC") || u.includes("LIGHT")) {
        activeLayers.add(l);
      }
    });
    if (drawingData.fixtures && drawingData.fixtures.length > 0) activeLayers.add("LIGHTING_FIXTURES");
    activeLayers.add("ROOM_OVERLAYS");
  } else if (trade === 'joinery') {
    // Isolate millwork, storages, consoles, planters, ledge seating
    allLayers.forEach(l => {
      const u = l.toUpperCase();
      if (u.includes("MILLWORK") || u.includes("STORAGE") || u.includes("CONSOLE") || u.includes("PLANTER") || u.includes("BANQUETTE") || u.includes("FHS") || u.includes("OHS") || u.includes("CABINET") || u.includes("JOINERY") || u.includes("COUNTER")) {
        activeLayers.add(l);
      }
    });
    activeLayers.add("ROOM_OVERLAYS");
  } else if (trade === 'av') {
    // Isolate AV presentation screens, TVs, IT racks
    allLayers.forEach(l => {
      const u = l.toUpperCase();
      if (u.includes("AV") || u.includes("TV") || u.includes("DISPLAY") || u.includes("SCREEN") || u.includes("SERVER") || u.includes("IT") || u.includes("MONITOR")) {
        activeLayers.add(l);
      }
    });
    activeLayers.add("ROOM_OVERLAYS");
  }

  updateLayersGridUI();
  render();
}

function setupSearchAndQuickFilters() {
  const searchInput = document.getElementById('spaceSearchInput');
  const btnClear = document.getElementById('btnClearSearch');

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.trim().toLowerCase();
      applySearchFilter();
    });
  }

  if (btnClear) {
    btnClear.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      searchQuery = '';
      applySearchFilter();
    });
  }

  const btnSelectAll = document.getElementById('btnSelectAllLayers');
  const btnDeselectAll = document.getElementById('btnDeselectAllLayers');

  if (btnSelectAll) {
    btnSelectAll.onclick = () => {
      if (!drawingData) return;
      drawingData.layers.forEach(l => activeLayers.add(l));
      activeLayers.add("ROOM_OVERLAYS");
      if (drawingData.fixtures && drawingData.fixtures.length > 0) activeLayers.add("LIGHTING_FIXTURES");
      updateLayersGridUI();
      render();
    };
  }

  if (btnDeselectAll) {
    btnDeselectAll.onclick = () => {
      activeLayers.clear();
      updateLayersGridUI();
      render();
    };
  }
}

function applySearchFilter() {
  render();

  // In room schedule list, filter/highlight cards
  const cards = document.querySelectorAll('.room-card');
  let firstMatch = null;
  cards.forEach(card => {
    const text = card.textContent.toLowerCase();
    if (!searchQuery) {
      card.style.display = 'block';
      card.classList.remove('search-match');
    } else if (text.includes(searchQuery)) {
      card.style.display = 'block';
      card.classList.add('search-match');
      if (!firstMatch) firstMatch = card;
    } else {
      card.style.display = 'none';
      card.classList.remove('search-match');
    }
  });

  if (firstMatch && searchQuery) {
    firstMatch.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}

function setupTabControls() {
  const btnSummary = document.getElementById('tabSummary');
  const btnPricing = document.getElementById('tabPricing');
  const btnRooms = document.getElementById('tabRooms');

  const setTab = (tab) => {
    currentTab = tab;
    if (btnSummary) btnSummary.className = tab === 'summary' ? 'tab-btn active' : 'tab-btn';
    if (btnPricing) btnPricing.className = tab === 'pricing' ? 'tab-btn active' : 'tab-btn';
    if (btnRooms) btnRooms.className = tab === 'rooms' ? 'tab-btn active' : 'tab-btn';
    setupUI();
  };

  if (btnSummary) btnSummary.onclick = () => setTab('summary');
  if (btnPricing) btnPricing.onclick = () => setTab('pricing');
  if (btnRooms) btnRooms.onclick = () => setTab('rooms');
}

function updateLayersGridUI() {
  const grid = document.getElementById('layersGrid');
  const countBadge = document.getElementById('layersCountBadge');
  if (!grid || !drawingData) return;

  grid.innerHTML = '';
  const totalCount = drawingData.layers.length + 1 + (drawingData.fixtures && drawingData.fixtures.length > 0 ? 1 : 0);
  if (countBadge) countBadge.innerText = `${activeLayers.size}/${totalCount} visible`;

  drawingData.layers.forEach(layer => {
    const tag = document.createElement('div');
    const isActive = activeLayers.has(layer);
    tag.className = `layer-tag ${isActive ? 'active' : ''}`;
    const style = getLayerStyle(layer);
    tag.innerHTML = `<div class="layer-dot" style="background: ${style.color}"></div> ${layer}`;
    tag.onclick = () => {
      if (activeLayers.has(layer)) {
        activeLayers.delete(layer);
      } else {
        activeLayers.add(layer);
      }
      updateLayersGridUI();
      render();
    };
    grid.appendChild(tag);
  });

  // Room Overlays Toggle
  const roomTag = document.createElement('div');
  const roomsActive = activeLayers.has("ROOM_OVERLAYS");
  roomTag.className = `layer-tag ${roomsActive ? 'active' : ''}`;
  roomTag.innerHTML = `<div class="layer-dot" style="background: #059669"></div> SPACES (${drawingData.rooms.length})`;
  roomTag.onclick = () => {
    if (activeLayers.has("ROOM_OVERLAYS")) activeLayers.delete("ROOM_OVERLAYS");
    else activeLayers.add("ROOM_OVERLAYS");
    updateLayersGridUI();
    render();
  };
  grid.appendChild(roomTag);

  // Fixtures Layer Toggle
  if (drawingData.fixtures && drawingData.fixtures.length > 0) {
    const fixTag = document.createElement('div');
    const fixActive = activeLayers.has("LIGHTING_FIXTURES");
    fixTag.className = `layer-tag ${fixActive ? 'active' : ''}`;
    fixTag.innerHTML = `<div class="layer-dot" style="background: #d97706"></div> FIXTURES (${drawingData.fixtures.length})`;
    fixTag.onclick = () => {
      if (activeLayers.has("LIGHTING_FIXTURES")) activeLayers.delete("LIGHTING_FIXTURES");
      else activeLayers.add("LIGHTING_FIXTURES");
      updateLayersGridUI();
      render();
    };
    grid.appendChild(fixTag);
  }
}

function updateFinishPills() {
  const container = document.getElementById('finishFilterBar');
  if (!container || !drawingData) return;

  container.innerHTML = '';
  // Gather finishes from rooms
  const finishes = new Map();
  drawingData.rooms.forEach(r => {
    const code = (r.finish_code || "FL-01").trim();
    if (!finishes.has(code)) {
      finishes.set(code, { code, count: 0, totalArea: 0 });
    }
    const item = finishes.get(code);
    item.count += 1;
    item.totalArea += (r.net_area_sqm || 0);
  });

  if (finishes.size > 0) {
    // "All Finishes" pill
    const allPill = document.createElement('div');
    allPill.className = `finish-pill ${activeFinishFilter === null ? 'active' : ''}`;
    allPill.innerText = `All Finishes (${drawingData.rooms.length})`;
    allPill.onclick = () => {
      activeFinishFilter = null;
      updateFinishPills();
      render();
    };
    container.appendChild(allPill);

    finishes.forEach(f => {
      const pill = document.createElement('div');
      pill.className = `finish-pill ${activeFinishFilter === f.code ? 'active' : ''}`;
      const desc = FINISH_PALETTE[f.code] ? FINISH_PALETTE[f.code].name.split('/')[0].trim() : f.code;
      const areaSqft = Math.round(f.totalArea * SQM_TO_SQFT);
      pill.innerText = `${f.code}: ${desc} (${areaSqft.toLocaleString('en-IN')} sqft)`;
      pill.onclick = () => {
        activeFinishFilter = activeFinishFilter === f.code ? null : f.code;
        updateFinishPills();
        render();
      };
      container.appendChild(pill);
    });
  }
}

function updateAIIntelligenceUI() {
  const card = document.getElementById('aiInsightsCard');
  const badge = document.getElementById('aiStatusBadge');
  if (!card) return;

  const ai = drawingData && drawingData.ai_insight;
  if (!ai) {
    card.innerHTML = `<span style="color: var(--txt-muted);">Load a drawing to activate AI space recognition.</span>`;
    if (badge) badge.innerText = "Standby";
    return;
  }

  if (badge) {
    badge.innerText = "Verified";
    badge.className = "badge badge-green";
  }

  const suppressedHtml = (ai.suppressed_trades || []).map(s => `<div style="color: #f87171; margin-bottom: 2px;">• <strong>Suppressed:</strong> ${s}</div>`).join('');
  const reasonsHtml = (ai.reasons || []).slice(0, 3).map(r => `<div>• ${r}</div>`).join('');

  card.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
      <span style="font-weight: 700; color: var(--txt-primary); font-size: 0.78rem;">${ai.title || ai.discipline}</span>
      <span style="color: var(--accent-green); font-weight: 600; font-size: 0.72rem;">${(ai.confidence * 100).toFixed(1)}%</span>
    </div>
    <div style="font-size: 0.7rem; color: var(--txt-muted); margin-bottom: 6px;">
      Scale: <strong style="color: var(--txt-secondary);">1:${ai.scale_ratio || 100}</strong>
      &nbsp;·&nbsp; ${ai.ai_provider_used || 'Local AI'}
    </div>
    ${suppressedHtml ? `<div style="background: rgba(224,82,82,0.08); border-left: 2px solid #E05252; padding: 4px 6px; margin-bottom: 6px; font-size: 0.68rem;">${suppressedHtml}</div>` : ''}
    <div style="font-size: 0.7rem; color: var(--txt-secondary); line-height: 1.4;">
      ${reasonsHtml}
    </div>
  `;
}

function setupUI() {
  const grid = document.getElementById('layersGrid');
  const list = document.getElementById('takeoffList');

  if (!drawingData) {
    if (grid) grid.innerHTML = '<span style="font-size: 0.75rem; color: var(--txt-muted);">No drawing loaded</span>';
    if (list) {
      list.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#E8601C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          </div>
          <h3>Ready for Drawing Upload</h3>
          <p>Upload a PDF or DXF layout to auto-calibrate scale, extract spaces, and generate itemised BOQ quantities.</p>
          <label class="cta-btn" style="cursor:pointer">
            Upload Drawing (PDF / DXF)
            <input type="file" onchange="const f = this.files[0]; if (f) { const dt = new DataTransfer(); dt.items.add(f); document.getElementById('fileInput').files = dt.files; document.getElementById('fileInput').dispatchEvent(new Event('change')); }" accept=".dxf,.pdf" style="display: none;">
          </label>
        </div>
      `;
    }
    updateAIIntelligenceUI();
    return;
  }

  updateLayersGridUI();
  updateFinishPills();
  updateAIIntelligenceUI();

  // Tab Content Rendering
  list.innerHTML = '';
  const totalFloorArea = drawingData.rooms.reduce((sum, r) => sum + (r.net_area_sqm || 0), 0);

  if (currentTab === 'summary') {
    // 1. BOQ Summary View
    const summaryCard = document.createElement('div');
    summaryCard.className = 'boq-summary-card';

    let tableRows = '';
    const totals = drawingData.totals || {};

    if (Object.keys(totals).length > 0) {
      for (const [code, data] of Object.entries(totals)) {
        const rawNet = data.net_quantity ?? data.total_quantity;
        const rawGross = data.gross_quantity ?? rawNet;
        const netObj = formatQuantityAndUnit(rawNet, data.unit);
        const grossObj = formatQuantityAndUnit(rawGross, data.unit);
        const wPct = typeof data.wastage_percent === 'number' ? `${(data.wastage_percent * 100).toFixed(0)}%` : '0%';

        tableRows += `
          <tr>
            <td><strong style="color: var(--brand); font-family: monospace; font-size: 0.75rem;">${code}</strong></td>
            <td style="font-size: 0.76rem; color: var(--t1);">${data.description || code}</td>
            <td style="text-align: right; color: var(--t3); font-weight: 500;">${Number(netObj.qty).toLocaleString('en-IN')}</td>
            <td style="text-align: center; color: var(--brand); font-weight: 600; font-size: 0.74rem;">${wPct}</td>
            <td style="text-align: right; font-weight: 700; color: var(--green);">${Number(grossObj.qty).toLocaleString('en-IN')}</td>
            <td style="text-align: center; color: var(--t3); font-weight: 600; font-size: 0.72rem;">${netObj.unit}</td>
          </tr>
        `;
      }
    } else {
      const netObj = formatQuantityAndUnit(totalFloorArea, 'sqm');
      const grossObj = formatQuantityAndUnit(totalFloorArea * 1.05, 'sqm');
      tableRows += `
        <tr>
          <td><strong style="color: var(--brand); font-family: monospace; font-size: 0.75rem;">FL-RAW</strong></td>
          <td style="font-size: 0.76rem; color: var(--t1);">Measured Floor Area</td>
          <td style="text-align: right; color: var(--t3); font-weight: 500;">${Number(netObj.qty).toLocaleString('en-IN')}</td>
          <td style="text-align: center; color: var(--brand); font-weight: 600;">5%</td>
          <td style="text-align: right; font-weight: 700; color: var(--green);">${Number(grossObj.qty).toLocaleString('en-IN')}</td>
          <td style="text-align: center; color: var(--t3); font-weight: 600; font-size: 0.72rem;">sqft</td>
        </tr>
      `;
    }

    const totalFloorAreaSqft = Math.round(totalFloorArea * SQM_TO_SQFT);
    summaryCard.innerHTML = `
      <div class="boq-metrics">
        <div class="metric-box">
          <div class="metric-val">${totalFloorAreaSqft.toLocaleString('en-IN')} <span style="font-size: 0.8rem; font-weight: 600;">sqft</span></div>
          <div class="metric-lbl">Total Carpet Area</div>
        </div>
        <div class="metric-box">
          <div class="metric-val">${drawingData.rooms.length}</div>
          <div class="metric-lbl">Architectural Spaces</div>
        </div>
      </div>
      <table class="boq-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Trade / Scope</th>
            <th style="text-align: right;" title="Net drawing measurement">Net</th>
            <th style="text-align: center;" title="Standard trade wastage">Waste%</th>
            <th style="text-align: right;" title="Gross procurement order quantity">Gross PO</th>
            <th style="text-align: center;">Unit</th>
          </tr>
        </thead>
        <tbody>
          ${tableRows}
        </tbody>
      </table>
      <div style="margin-top: 12px; font-size: 0.72rem; color: var(--t3); text-align: center; display: flex; justify-content: space-between; border-top: 1px solid var(--border); padding-top: 8px;">
        <span>IS 1200 / POMI Standard</span>
        <span style="color: var(--green); font-weight: 600;">Net vs Gross Procurement Ready</span>
      </div>
    `;
    list.appendChild(summaryCard);

  } else if (currentTab === 'pricing') {
    // 2. Priced BOQ & Budget View
    const pricingCard = document.createElement('div');
    pricingCard.className = 'boq-summary-card';
    const est = drawingData.priced_estimate;

    if (!est || !est.items || est.items.length === 0) {
      pricingCard.innerHTML = `
        <div style="text-align: center; padding: 32px 12px; color: var(--t3);">
          <div style="font-size: 1.8rem; margin-bottom: 8px;">📋</div>
          <p style="font-weight: 700; color: var(--t1); margin-bottom: 4px;">Priced BOQ Generating...</p>
          <p style="font-size: 0.78rem; color: var(--t3);">Upload or recalculate layout to view market-rate estimate.</p>
        </div>
      `;
      list.appendChild(pricingCard);
      return;
    }

    const fmtInr = (num) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(num || 0);

    // Group items by category / trade
    const trades = {};
    est.items.forEach(it => {
      const cat = it.category || 'General Works';
      if (!trades[cat]) trades[cat] = [];
      trades[cat].push(it);
    });

    let tradeSectionsHtml = '';
    for (const [tradeName, items] of Object.entries(trades)) {
      const tradeSubtotal = (est.trade_subtotals_inr && est.trade_subtotals_inr[tradeName]) || items.reduce((s, i) => s + (i.total_amount_inr || 0), 0);
      let rows = '';
      items.forEach(it => {
        const netObj = formatQuantityAndUnit(it.net_quantity, it.unit);
        const grossObj = formatQuantityAndUnit(it.gross_quantity, it.unit);
        let rate = it.unit_rate_inr;
        if (netObj.unit === 'sqft') rate = it.unit_rate_inr / SQM_TO_SQFT;
        else if (netObj.unit === 'Rft') rate = it.unit_rate_inr / M_TO_RFT;

        const itemIdx = est.items.indexOf(it);
        rows += `
          <tr class="priced-item-row" data-item-index="${itemIdx}" data-code="${it.item_code}">
            <td><strong style="color: var(--brand); font-family: monospace; font-size: 0.75rem;">${it.item_code}</strong></td>
            <td style="font-size: 0.76rem; color: var(--t1);" title="${it.description}">${it.description}</td>
            <td style="text-align: right; color: var(--t3); font-size: 0.75rem;">${Number(netObj.qty).toLocaleString('en-IN')}</td>
            <td style="text-align: right; color: var(--green); font-size: 0.75rem; font-weight: 700;">${Number(grossObj.qty).toLocaleString('en-IN')}</td>
            <td style="text-align: center; font-size: 0.72rem; color: var(--t3); font-weight: 600;">${netObj.unit}</td>
            <td style="text-align: right; font-size: 0.75rem; color: var(--t2);">₹${Math.round(rate).toLocaleString('en-IN')}</td>
            <td style="text-align: right; font-weight: 700; color: var(--t1); font-size: 0.78rem;">₹${Math.round(it.total_amount_inr).toLocaleString('en-IN')}</td>
          </tr>
        `;
      });

      tradeSectionsHtml += `
        <tr style="background: var(--surface-2); border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);">
          <td colspan="6" style="font-weight: 700; color: var(--t1); font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.3px; padding: 6px 8px;">${tradeName}</td>
          <td style="text-align: right; font-weight: 700; color: var(--brand); font-size: 0.78rem; padding: 6px 8px;">${fmtInr(tradeSubtotal)}</td>
        </tr>
        ${rows}
      `;
    }

    const benchmarkRate = Math.round(est.cost_per_sqft_inr || (est.cost_per_sqm_inr / SQM_TO_SQFT));
    pricingCard.innerHTML = `
      <div class="priced-budget-header">
        <div style="display: flex; justify-content: space-between; align-items: baseline;">
          <span style="font-size: 0.68rem; font-weight: 700; color: var(--t3); text-transform: uppercase; letter-spacing: 0.5px;">Grand Total Budget (Inc. 18% GST)</span>
          <span style="font-size: 0.68rem; color: var(--brand); font-weight: 700; background: var(--brand-light); border: 1px solid var(--brand-border); padding: 2px 7px; border-radius: var(--r-full); text-transform: uppercase;">Grade: ${est.fitout_grade}</span>
        </div>
        <div style="font-size: 1.65rem; font-weight: 800; color: var(--t1); margin: 6px 0 10px 0; letter-spacing: -0.5px;">
          ${fmtInr(est.grand_total_budget_inr)}
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; font-size: 0.72rem; border-top: 1px solid var(--border); padding-top: 8px;">
          <div><span style="color: var(--t4);">Direct Cost:</span> <strong style="color: var(--t1); display: block;">${fmtInr(est.direct_cost_subtotal_inr)}</strong></div>
          <div><span style="color: var(--t4);">OH & Profit (10%):</span> <strong style="color: var(--t1); display: block;">${fmtInr(est.contractor_overhead_profit_inr)}</strong></div>
          <div><span style="color: var(--t4);">GST (18%):</span> <strong style="color: var(--t1); display: block;">${fmtInr(est.gst_tax_inr)}</strong></div>
        </div>
        <div style="margin-top: 8px; font-size: 0.72rem; color: var(--t3); display: flex; justify-content: space-between; border-top: 1px dashed var(--border); padding-top: 6px;">
          <span>Contingency Buffer (3%): <strong style="color: var(--t2);">${fmtInr(est.contingency_inr)}</strong></span>
          <span>Fitout Rate: <strong style="color: var(--brand);">₹${benchmarkRate.toLocaleString('en-IN')}/sqft</strong></span>
        </div>
      </div>

      <table class="boq-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Description</th>
            <th style="text-align: right;" title="Net drawing quantity">Net</th>
            <th style="text-align: right;" title="Gross procurement order quantity">Gross PO</th>
            <th style="text-align: center;">Unit</th>
            <th style="text-align: right;" title="Combined composite unit rate">Rate</th>
            <th style="text-align: right;" title="Line item total direct cost">Amount</th>
          </tr>
        </thead>
        <tbody>
          ${tradeSectionsHtml}
        </tbody>
      </table>
      <div style="margin-top: 12px; font-size: 0.72rem; color: var(--t3); text-align: center; display: flex; justify-content: space-between; border-top: 1px solid var(--border); padding-top: 8px;">
        <span>IS 1200 / Delhi Schedule of Rates</span>
        <span style="color: var(--green); font-weight: 600;">Click row for Rate Analysis Audit</span>
      </div>
    `;

    list.appendChild(pricingCard);

    // Row click inspection
    pricingCard.querySelectorAll('.priced-item-row').forEach(tr => {
      tr.onclick = () => {
        const idx = parseInt(tr.getAttribute('data-item-index'), 10);
        const code = tr.getAttribute('data-code');
        const item = (!isNaN(idx) && est.items[idx]) ? est.items[idx] : est.items.find(it => it.item_code === code);
        if (item) inspectRateAnalysis(item, est);
      };
    });

  } else {
    // 3. Room Schedule View
    drawingData.rooms.forEach(room => {
      const isSelected = selectedRoom && selectedRoom.id === room.id;
      const isNamed = room.name && !room.name.includes("Unlabeled") && !room.name.startsWith("Room_");
      const cleanName = isNamed ? room.name : `Space ${room.id}`;
      const finish = getRoomFinishStyle(room);
      const areaSqft = Math.round(room.net_area_sqm * SQM_TO_SQFT);
      const perimeterRft = Math.round(room.perimeter_m * M_TO_RFT);

      const card = document.createElement('div');
      card.className = `room-card ${isSelected ? 'selected' : ''}`;
      card.id = `room-card-${room.id}`;
      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <strong style="font-size: 0.86rem; color: ${isSelected ? 'var(--brand)' : 'var(--t1)'};">${cleanName}</strong>
          <span style="font-size: 0.96rem; font-weight: 700; color: var(--green);">${areaSqft.toLocaleString('en-IN')} sqft</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.74rem; color: var(--t3); margin-bottom: 3px;">
          <span>Perimeter: ${perimeterRft.toLocaleString('en-IN')} Rft</span>
          <span style="color: ${finish.stroke}; font-weight: 600;">${room.finish_code || 'FL-01'}: ${finish.name.split('/')[0]}</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.70rem; color: var(--t4);">
          <span>Confidence: ${(room.confidence * 100).toFixed(0)}%</span>
          <span>Status: ${room.status || 'RAW_MEASURED'}</span>
        </div>
      `;
      card.onclick = () => selectRoom(room);
      list.appendChild(card);
    });
  }
}

function inspectRateAnalysis(item, est) {
  const panel = document.getElementById('evidenceContent');
  const evPanel = document.getElementById('evidencePanel');
  if (evPanel) evPanel.open = true;
  if (!panel) return;

  const netObj = formatQuantityAndUnit(item.net_quantity, item.unit);
  const grossObj = formatQuantityAndUnit(item.gross_quantity, item.unit);
  let matRate = item.gross_quantity > 0 ? (item.material_cost_inr / item.gross_quantity) : (item.unit_rate_inr * 0.7);
  let labRate = item.net_quantity > 0 ? (item.labor_cost_inr / item.net_quantity) : (item.unit_rate_inr * 0.3);

  if (netObj.unit === 'sqft') {
    matRate = matRate / SQM_TO_SQFT;
    labRate = labRate / SQM_TO_SQFT;
  } else if (netObj.unit === 'Rft') {
    matRate = matRate / M_TO_RFT;
    labRate = labRate / M_TO_RFT;
  }

  panel.innerHTML = `
    <div style="margin-bottom: 8px;">
      <strong style="color: var(--brand); font-size: 0.92rem; font-family: monospace;">${item.item_code}</strong> — <span style="color: var(--t1); font-weight: 600;">${item.description}</span>
      <div style="font-size: 0.72rem; color: var(--t3); margin-top: 2px;">Trade: ${item.category} | Grade: ${est.fitout_grade.toUpperCase()}</div>
    </div>
    <div style="background: var(--surface-2); border: 1px solid var(--border); border-radius: 6px; padding: 10px; margin-bottom: 8px;">
      <div style="font-size: 0.74rem; font-weight: 700; color: var(--green); margin-bottom: 6px;">IS 1200 / POMI RATE ANALYSIS DUAL-DERIVATION:</div>
      <div style="font-size: 0.74rem; line-height: 1.6; color: var(--t2);">
        <div>• <strong>Material Supply Component (on Gross PO Qty):</strong><br>
          ${Number(grossObj.qty).toLocaleString('en-IN')} ${grossObj.unit} × ₹${Math.round(matRate).toLocaleString('en-IN')}/${grossObj.unit} = <span style="color: var(--brand); font-weight: 700;">₹${item.material_cost_inr.toLocaleString('en-IN', {maximumFractionDigits: 0})}</span>
        </div>
        <div style="margin-top: 6px;">• <strong>Labor & Installation (on Net Installed Drawing Qty):</strong><br>
          ${Number(netObj.qty).toLocaleString('en-IN')} ${netObj.unit} × ₹${Math.round(labRate).toLocaleString('en-IN')}/${netObj.unit} = <span style="color: var(--brand); font-weight: 700;">₹${item.labor_cost_inr.toLocaleString('en-IN', {maximumFractionDigits: 0})}</span>
        </div>
        <div style="margin-top: 8px; border-top: 1px solid var(--border); padding-top: 6px; display: flex; justify-content: space-between;">
          <strong>Total Direct Item Cost:</strong>
          <span style="color: var(--green); font-weight: 800; font-size: 0.88rem;">₹${item.total_amount_inr.toLocaleString('en-IN', {maximumFractionDigits: 0})}</span>
        </div>
      </div>
    </div>
    <div style="font-size: 0.72rem; color: var(--t3);">
      Drawing Net: ${Number(netObj.qty).toLocaleString('en-IN')} ${netObj.unit} | Wastage Factor: ${(item.wastage_percent*100).toFixed(1)}% | Gross PO: ${Number(grossObj.qty).toLocaleString('en-IN')} ${grossObj.unit}
    </div>
  `;
}

function selectRoom(room) {
  selectedRoom = room;
  document.querySelectorAll('.room-card').forEach(c => c.classList.remove('selected'));
  const card = document.getElementById(`room-card-${room ? room.id : ''}`);
  if (card) {
    card.classList.add('selected');
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  const panel = document.getElementById('evidenceContent');
  const evPanel = document.getElementById('evidencePanel');
  if (evPanel && room) evPanel.open = true;
  if (panel && room) {
    const isNamed = room.name && !room.name.includes("Unlabeled") && !room.name.startsWith("Room_");
    const cleanName = isNamed ? room.name : `Space ${room.id}`;
    const finish = getRoomFinishStyle(room);
    const areaSqft = Math.round(room.net_area_sqm * SQM_TO_SQFT);
    const perimeterRft = Math.round(room.perimeter_m * M_TO_RFT);
    const wallAreaSqft = Math.round(room.perimeter_m * 3.0 * SQM_TO_SQFT);

    panel.innerHTML = `
      <div style="margin-bottom: 6px;"><strong style="color: var(--brand); font-size: 0.95rem;">${cleanName}</strong> (${room.id})</div>
      <div><strong>Finish Specification:</strong> <span style="color: ${finish.stroke}; font-weight: 700;">${room.finish_code || 'FL-01'} (${finish.name})</span></div>
      <div><strong>Net Carpet Area:</strong> <span style="color: var(--green); font-weight: 700;">${areaSqft.toLocaleString('en-IN')} sqft</span></div>
      <div><strong>Perimeter:</strong> ${perimeterRft.toLocaleString('en-IN')} Rft | <strong>Ceiling Height:</strong> 10.0 ft</div>
      <div><strong>Wall Surface Gross:</strong> ${wallAreaSqft.toLocaleString('en-IN')} sqft | Status: <em>${room.status}</em></div>
      <div style="margin-top: 6px; font-size: 0.75rem; color: var(--t3);">
        <strong>Audit Boundary Vertices (${room.polygon.length}):</strong><br>
        <code>${room.polygon.slice(0, 4).map(p => `[${p[0].toFixed(0)}, ${p[1].toFixed(0)}]`).join(' → ')}${room.polygon.length > 4 ? ' ...' : ''}</code>
      </div>
    `;
  }
  render();
}

function setupInteractions() {
  canvas.addEventListener('mousedown', (e) => {
    isDragging = true;
    startX = e.clientX - panX;
    startY = e.clientY - panY;
    dragDist = 0;
  });

  window.addEventListener('mousemove', (e) => {
    if (isDragging) {
      const dx = e.clientX - panX - startX;
      const dy = e.clientY - panY - startY;
      dragDist += Math.abs(dx) + Math.abs(dy);
      panX = e.clientX - startX;
      panY = e.clientY - startY;
      render();
    } else if (drawingData && drawingData.rooms && canvas) {
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      const worldPos = screenToWorld(mouseX, mouseY);

      let found = null;
      for (const r of drawingData.rooms) {
        if (pointInPolygon(worldPos, r.polygon)) {
          found = r;
          break;
        }
      }

      if (found !== hoveredRoom) {
        hoveredRoom = found;
        canvas.style.cursor = hoveredRoom ? 'pointer' : (isDragging ? 'grabbing' : 'grab');
        render();
      }
    }
  });

  window.addEventListener('mouseup', (e) => {
    if (isDragging && dragDist < 6 && drawingData && drawingData.rooms) {
      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      const worldPos = screenToWorld(mouseX, mouseY);

      let clickedRoom = null;
      for (const r of drawingData.rooms) {
        if (pointInPolygon(worldPos, r.polygon)) {
          clickedRoom = r;
          break;
        }
      }
      if (clickedRoom) {
        selectRoom(clickedRoom);
      }
    }
    isDragging = false;
  });

  // Cursor-Anchored Mouse Wheel Zoom (CAD Standard)
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    const newScale = Math.max(0.0001, Math.min(scale * zoomFactor, 20.0));

    // Keep world coordinate under mouse pointer invariant
    panX = mouseX - (mouseX - panX) * (newScale / scale);
    panY = mouseY - (mouseY - panY) * (newScale / scale);
    scale = newScale;

    updateZoomDisplay();
    render();
  }, { passive: false });

  document.getElementById('btnZoomIn').onclick = () => {
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const newScale = Math.min(scale * 1.25, 20.0);
    panX = cx - (cx - panX) * (newScale / scale);
    panY = cy - (cy - panY) * (newScale / scale);
    scale = newScale;
    updateZoomDisplay();
    render();
  };

  document.getElementById('btnZoomOut').onclick = () => {
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const newScale = Math.max(scale * 0.8, 0.0001);
    panX = cx - (cx - panX) * (newScale / scale);
    panY = cy - (cy - panY) * (newScale / scale);
    scale = newScale;
    updateZoomDisplay();
    render();
  };

  document.getElementById('btnReset').onclick = () => {
    if (drawingData && drawingData.segments && drawingData.segments.length > 0) {
      autoFitCanvas();
    } else {
      scale = 0.08; panX = 150; panY = 400;
    }
    selectedRoom = null;
    hoveredRoom = null;
    updateZoomDisplay();
    render();
  };

  async function handleUploadedFile(file) {
    if (!file) return;

    const metaBadge = document.getElementById('drawingMeta');
    const statusBadge = document.getElementById('engineStatusBadge');
    const scaleIndicator = document.getElementById('scaleLabelText');

    metaBadge.innerText = `Uploading ${file.name}...`;
    statusBadge.innerText = "Uploading Layout...";
    statusBadge.className = "badge";
    if (scaleIndicator) scaleIndicator.innerText = "Auto-Detecting Scale...";

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("drawing_number", file.name.replace(/\.[^/.]+$/, ""));
      formData.append("revision", "01");

      const uploadRes = await fetch("/v1/drawings/upload", {
        method: "POST",
        body: formData
      });

      if (!uploadRes.ok) throw new Error(`Upload failed: ${uploadRes.statusText}`);

      const uploadData = await uploadRes.json();
      currentDrawingId = uploadData.drawing_id;
      currentFileName = file.name;

      await runTakeoff(currentDrawingId, currentFileName);

    } catch (err) {
      console.error(err);
      statusBadge.innerText = "Upload Failed";
      statusBadge.className = "badge";
      alert(`Failed to upload ${file.name}:\n${err.message}`);
    }
  }

  // Upload handler
  const fileInput = document.getElementById('fileInput');
  if (fileInput) {
    fileInput.addEventListener('change', async (e) => {
      const file = e.target.files[0];
      await handleUploadedFile(file);
    });
  }

  // Drag & Drop onto viewport
  const viewport = document.getElementById('canvasViewport');
  if (viewport) {
    viewport.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.stopPropagation();
      viewport.style.outline = "2px dashed #E8601C";
      viewport.style.outlineOffset = "-4px";
      viewport.style.backgroundColor = "rgba(232, 96, 28, 0.04)";
    });
    viewport.addEventListener('dragleave', (e) => {
      e.preventDefault();
      e.stopPropagation();
      viewport.style.outline = "none";
      viewport.style.backgroundColor = "transparent";
    });
    viewport.addEventListener('drop', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      viewport.style.outline = "none";
      viewport.style.backgroundColor = "transparent";
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        await handleUploadedFile(e.dataTransfer.files[0]);
      }
    });
  }

  // Recalculate Trigger
  const btnRecalc = document.getElementById('btnRunTakeoff');
  if (btnRecalc) {
    btnRecalc.addEventListener('click', () => {
      if (currentDrawingId) {
        runTakeoff(currentDrawingId, currentFileName);
      } else {
        alert("Please upload a drawing first.");
      }
    });
  }

  // Auto-recalculate on Wastage Dropdown Change
  const wastageSelect = document.getElementById('wastageSelect');
  if (wastageSelect) {
    wastageSelect.addEventListener('change', () => {
      if (currentDrawingId) {
        runTakeoff(currentDrawingId, currentFileName);
      }
    });
  }

  // Live Pricing Update on Fitout Grade Dropdown Change
  const gradeSelect = document.getElementById('gradeSelect');
  if (gradeSelect) {
    gradeSelect.addEventListener('change', async () => {
      if (currentDrawingId) {
        await updatePricing(currentDrawingId, gradeSelect.value);
        setupUI();
      }
    });
  }

  setupExportButtons(drawingData ? drawingData.drawing_id : null);
}

async function updatePricing(drawingId, grade) {
  try {
    const res = await fetch(`/v1/drawings/${drawingId}/pricing?fitout_grade=${grade}`);
    if (res.ok) {
      const data = await res.json();
      if (drawingData) {
        drawingData.priced_estimate = data;
      }
    }
  } catch (err) {
    console.error("Failed to fetch live pricing:", err);
  }
}

async function runTakeoff(drawingId, fileName) {
  const metaBadge = document.getElementById('drawingMeta');
  const statusBadge = document.getElementById('engineStatusBadge');
  const btnRecalc = document.getElementById('btnRunTakeoff');
  const scaleIndicator = document.getElementById('scaleLabelText');
  const wastageSelect = document.getElementById('wastageSelect');
  const selectedWastage = wastageSelect ? wastageSelect.value : "standard";
  const gradeSelect = document.getElementById('gradeSelect');
  const selectedGrade = gradeSelect ? gradeSelect.value : "standard";

  metaBadge.innerText = `${fileName}`;
  metaBadge.title = `${fileName} (${drawingId})`;
  statusBadge.innerText = "Quantifying Layout...";
  statusBadge.className = "badge";
  if (scaleIndicator) scaleIndicator.innerText = "Auto-Calibrating Scale...";

  try {
    const processPayload = {
      project_profile: {
        profile_id: "COMMERCIAL_FITOUT",
        units: "mm",
        measurement_profile: "commercial_fitout",
        assumptions_enabled: true,
        ceiling_height_m: 3.0,
        approved_assumptions: ["default_ceiling_height_m", "default_door_width_mm", "default_door_height_mm"],
        default_door_width_mm: 1000,
        default_door_height_mm: 2100,
        wastage_enabled: selectedWastage !== "zero",
        wastage_preset: selectedWastage
      }
    };

    const procRes = await fetch(`/v1/drawings/${drawingId}/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(processPayload)
    });

    if (!procRes.ok) throw new Error(`Calculation failed: ${procRes.statusText}`);

    const takeoffRes = await procRes.json();

    const geom = takeoffRes.geometry || {};
    drawingData = {
      drawing_id: drawingId,
      drawing: {
        filename: fileName,
        drawing_number: takeoffRes.drawing_number,
        revision: takeoffRes.revision
      },
      layers: geom.layers && geom.layers.length > 0 ? geom.layers : ["A-WALL", "A-DOOR", "ROOM_OVERLAYS", "LIGHTING_FIXTURES"],
      segments: geom.segments || [],
      rooms: geom.rooms || [],
      fixtures: geom.fixtures || [],
      takeoff: takeoffRes.items || [],
      totals: takeoffRes.totals || {},
      exceptions: takeoffRes.exceptions || [],
      base_measurements: takeoffRes.base_measurements || {},
      priced_estimate: takeoffRes.priced_estimate || null,
      ai_insight: geom.ai_insight || null
    };

    // Update Auto-Detected Scale Badge
    if (scaleIndicator) {
      const ai = drawingData.ai_insight;
      if (ai && ai.scale_ratio) {
        scaleIndicator.innerText = `Scale: 1:${ai.scale_ratio} (Auto)`;
      } else {
        scaleIndicator.innerText = "Scale: 1:100 (Auto)";
      }
    }

    if (selectedGrade !== "standard") {
      await updatePricing(drawingId, selectedGrade);
    }

    activeLayers.clear();
    drawingData.layers.forEach(l => activeLayers.add(l));
    activeLayers.add("ROOM_OVERLAYS");
    if (drawingData.fixtures && drawingData.fixtures.length > 0) {
      activeLayers.add("LIGHTING_FIXTURES");
    }

    setupUI();
    autoFitCanvas();
    updateZoomDisplay();
    render();

    const totalRooms = drawingData.rooms.length;
    statusBadge.innerText = `Takeoff Ready (${totalRooms} spaces)`;
    statusBadge.className = "badge badge-green";
    if (btnRecalc) btnRecalc.style.display = "inline-flex";

    setupExportButtons(drawingId);

  } catch (err) {
    console.error(err);
    statusBadge.innerText = "Processing Error";
    statusBadge.className = "badge";
    alert(`Failed to calculate quantities for ${fileName}:\n${err.message}`);
  }
}

function setupExportButtons(drawingId) {
  const btnExcel = document.getElementById('btnExportExcel');
  const btnCsv = document.getElementById('btnExportCsv');

  if (btnExcel) {
    btnExcel.onclick = () => {
      const id = drawingId || (drawingData ? drawingData.drawing_id : null);
      if (!id) {
        alert("Upload or select a drawing first to export quantities.");
        return;
      }
      window.open(`/v1/drawings/${id}/export?format=excel`, '_blank');
    };
  }

  if (btnCsv) {
    btnCsv.onclick = () => {
      const id = drawingId || (drawingData ? drawingData.drawing_id : null);
      if (!id) {
        alert("Upload or select a drawing first to export quantities.");
        return;
      }
      window.open(`/v1/drawings/${id}/export?format=csv`, '_blank');
    };
  }
}

function autoFitCanvas() {
  if (!drawingData || !drawingData.segments || drawingData.segments.length === 0) return;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  drawingData.segments.forEach(s => {
    minX = Math.min(minX, s.x1, s.x2);
    maxX = Math.max(maxX, s.x1, s.x2);
    minY = Math.min(minY, s.y1, s.y2);
    maxY = Math.max(maxY, s.y1, s.y2);
  });

  const rangeX = maxX - minX || 1000;
  const rangeY = maxY - minY || 1000;
  const fitScale = Math.min((canvas.width * 0.82) / rangeX, (canvas.height * 0.82) / rangeY);
  scale = Math.max(0.0001, Math.min(fitScale, 10.0));
  panX = canvas.width / 2 - ((minX + maxX) / 2) * scale;
  panY = canvas.height / 2 + ((minY + maxY) / 2) * scale;
}

function worldToScreen(x, y) {
  return {
    x: panX + x * scale,
    y: panY - y * scale
  };
}

function screenToWorld(sx, sy) {
  return {
    x: (sx - panX) / scale,
    y: (panY - sy) / scale
  };
}

function pointInPolygon(pt, vs) {
  const x = pt.x, y = pt.y;
  let inside = false;
  for (let i = 0, j = vs.length - 1; i < vs.length; j = i++) {
    const xi = vs[i][0], yi = vs[i][1];
    const xj = vs[j][0], yj = vs[j][1];
    const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  drawGrid();

  if (!drawingData) {
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    const boxW = Math.min(460, canvas.width - 60);
    const boxH = 210;
    ctx.save();

    // Subtle white background card with soft elevation shadow and clean border
    ctx.fillStyle = "#FFFFFF";
    ctx.shadowColor = "rgba(15, 23, 42, 0.06)";
    ctx.shadowBlur = 20;
    ctx.shadowOffsetY = 4;
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(cx - boxW / 2, cy - boxH / 2, boxW, boxH, 12);
    else ctx.rect(cx - boxW / 2, cy - boxH / 2, boxW, boxH);
    ctx.fill();

    ctx.shadowColor = "transparent";
    ctx.strokeStyle = "#E2E8F0";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([6, 5]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Icon container (soft warm orange tint)
    ctx.fillStyle = "#FFF4EE";
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(cx - 22, cy - boxH/2 + 24, 44, 44, 10);
    else ctx.rect(cx - 22, cy - boxH/2 + 24, 44, 44);
    ctx.fill();

    // COG orange icon
    ctx.fillStyle = "#E8601C";
    ctx.font = "20px sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText("↑", cx, cy - boxH/2 + 46);

    // Headings
    ctx.fillStyle = "#0F172A";
    ctx.font = "600 15px 'Inter', sans-serif";
    ctx.fillText("Upload Architectural Drawing", cx, cy + 6);

    ctx.fillStyle = "#64748B";
    ctx.font = "400 12.5px 'Inter', sans-serif";
    ctx.fillText("Vector PDF or CAD DXF · Automatic scale calibration & BOQ", cx, cy + 28);

    // Pill badge at bottom
    const pillW = 120;
    const pillH = 28;
    const pillY = cy + 48;
    ctx.fillStyle = "#E8601C";
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(cx - pillW / 2, pillY, pillW, pillH, 6);
    else ctx.rect(cx - pillW / 2, pillY, pillW, pillH);
    ctx.fill();

    ctx.fillStyle = "#FFFFFF";
    ctx.font = "600 11.5px 'Inter', sans-serif";
    ctx.fillText("Browse Files", cx, pillY + 14);

    ctx.restore();
    return;
  }

  // 1. Draw CAD Line Segments (Grouped by layer style)
  drawingData.segments.forEach(seg => {
    if (!activeLayers.has(seg.layer)) return;
    const style = getLayerStyle(seg.layer);
    const p1 = worldToScreen(seg.x1, seg.y1);
    const p2 = worldToScreen(seg.x2, seg.y2);

    ctx.save();
    ctx.strokeStyle = style.color;
    ctx.lineWidth = style.width;
    if (style.dash && style.dash.length > 0) ctx.setLineDash(style.dash);

    ctx.beginPath();
    ctx.moveTo(p1.x, p1.y);
    ctx.lineTo(p2.x, p2.y);
    ctx.stroke();
    ctx.restore();
  });

  // 2. Draw Architectural Room Polygons & High-Contrast Finish Overlays
  if (activeLayers.has("ROOM_OVERLAYS")) {
    drawingData.rooms.forEach(room => {
      const isSelected = selectedRoom && selectedRoom.id === room.id;
      const isHovered = hoveredRoom && hoveredRoom.id === room.id;
      const roomFinish = getRoomFinishStyle(room);

      // Check if room matches search query or active finish filter
      const roomNameLower = (room.name || '').toLowerCase();
      const matchesSearch = !searchQuery || roomNameLower.includes(searchQuery) || (room.finish_code || '').toLowerCase().includes(searchQuery);
      const matchesFinish = !activeFinishFilter || room.finish_code === activeFinishFilter;

      const isDimmed = !matchesSearch || !matchesFinish;

      ctx.save();
      ctx.beginPath();
      const scrPts = [];
      room.polygon.forEach((pt, idx) => {
        const scr = worldToScreen(pt[0], pt[1]);
        scrPts.push(scr);
        if (idx === 0) ctx.moveTo(scr.x, scr.y);
        else ctx.lineTo(scr.x, scr.y);
      });
      ctx.closePath();

      if (isSelected) {
        ctx.fillStyle = "rgba(232, 96, 28, 0.16)";
        ctx.strokeStyle = "#E8601C";
        ctx.lineWidth = 2.5;
      } else if (isHovered) {
        ctx.fillStyle = "rgba(232, 96, 28, 0.08)";
        ctx.strokeStyle = "#E8601C";
        ctx.lineWidth = 1.8;
      } else if (isDimmed) {
        ctx.fillStyle = "rgba(241, 245, 249, 0.4)";
        ctx.strokeStyle = "rgba(203, 213, 225, 0.6)";
        ctx.lineWidth = 1;
      } else if (searchQuery && matchesSearch) {
        ctx.fillStyle = "rgba(245, 158, 11, 0.18)";
        ctx.strokeStyle = "#D97706";
        ctx.lineWidth = 2.0;
      } else {
        ctx.fillStyle = roomFinish.fill;
        ctx.strokeStyle = roomFinish.stroke;
        ctx.lineWidth = 1.5;
      }

      ctx.fill();
      ctx.stroke();
      ctx.restore();

      // Smart Room Badges (Only render when room has enough pixel area on screen)
      if (scrPts.length > 0 && !isDimmed) {
        const minX = Math.min(...scrPts.map(p => p.x));
        const maxX = Math.max(...scrPts.map(p => p.x));
        const minY = Math.min(...scrPts.map(p => p.y));
        const maxY = Math.max(...scrPts.map(p => p.y));
        const boxW = maxX - minX;
        const boxH = maxY - minY;

        if (boxW >= 60 && boxH >= 38) {
          const avgX = room.polygon.reduce((sum, p) => sum + p[0], 0) / room.polygon.length;
          const avgY = room.polygon.reduce((sum, p) => sum + p[1], 0) / room.polygon.length;
          const center = worldToScreen(avgX, avgY);

          const isNamed = room.name && !room.name.includes("Unlabeled") && !room.name.startsWith("Room_");
          const titleText = isNamed ? room.name : `Space ${room.id}`;
          const roomAreaSqft = Math.round(room.net_area_sqm * SQM_TO_SQFT);
          const finishText = room.finish_code ? `${room.finish_code} · ${roomAreaSqft.toLocaleString('en-IN')} sqft` : `${roomAreaSqft.toLocaleString('en-IN')} sqft`;

          ctx.font = "bold 11px Inter, sans-serif";
          const textW = Math.max(ctx.measureText(titleText).width, ctx.measureText(finishText).width);
          const pillW = textW + 18;
          const pillH = 34;

          // Glassmorphic pill badge
          ctx.save();
          ctx.fillStyle = isSelected ? "#E8601C" : "rgba(255, 255, 255, 0.96)";
          ctx.shadowColor = "rgba(15, 23, 42, 0.08)";
          ctx.shadowBlur = 8;
          ctx.shadowOffsetY = 2;
          ctx.beginPath();
          if (ctx.roundRect) ctx.roundRect(center.x - pillW / 2, center.y - pillH / 2, pillW, pillH, 6);
          else ctx.rect(center.x - pillW / 2, center.y - pillH / 2, pillW, pillH);
          ctx.fill();

          ctx.shadowColor = "transparent";
          ctx.strokeStyle = isSelected ? "#C2410C" : "#E2E8F0";
          ctx.lineWidth = 1.2;
          ctx.stroke();

          // Title
          ctx.fillStyle = isSelected ? "#FFFFFF" : "#0F172A";
          ctx.textAlign = "center";
          ctx.fillText(titleText, center.x, center.y - 3);

          // Finish / Area Subtext
          ctx.fillStyle = isSelected ? "#FFF4EE" : (roomFinish ? roomFinish.stroke : "#64748B");
          ctx.font = "bold 9.5px Inter, sans-serif";
          ctx.fillText(finishText, center.x, center.y + 11);
          ctx.restore();
        }
      }
    });
  }

  // 3. Draw Physical Lighting & Furniture Fixture Overlays
  if (activeLayers.has("LIGHTING_FIXTURES") && drawingData.fixtures && drawingData.fixtures.length > 0) {
    drawingData.fixtures.forEach(fix => {
      const scr = worldToScreen(fix.x, fix.y);
      if (scr.x < -40 || scr.x > canvas.width + 40 || scr.y < -40 || scr.y > canvas.height + 40) return;

      const isLinear = fix.item_code.startsWith("LT-01") || fix.item_code.startsWith("LT-02") || fix.item_code.startsWith("LT-03") || fix.item_code.startsWith("LT-04");
      const isConcealed = fix.item_code === "LT-05";
      const isHanging = fix.item_code === "LT-06";
      const isDecorative = fix.item_code === "LT-07" || fix.item_code === "LT-08";
      const isWorkstation = fix.item_code === "FN-01";

      ctx.save();
      if (isLinear) {
        // Radiant Amber Linear Light Bar
        ctx.fillStyle = "#D97706";
        ctx.strokeStyle = "#B45309";
        ctx.lineWidth = 1.5;
        const w = Math.max(18, 28 * scale * 0.05);
        const h = Math.max(7, 9 * scale * 0.05);
        ctx.beginPath();
        if (ctx.roundRect) ctx.roundRect(scr.x - w/2, scr.y - h/2, w, h, 3);
        else ctx.rect(scr.x - w/2, scr.y - h/2, w, h);
        ctx.fill();
        ctx.stroke();
      } else if (isConcealed) {
        // Emerald Concealed Downlight Circle
        ctx.fillStyle = "#059669";
        ctx.strokeStyle = "#047857";
        ctx.lineWidth = 1.2;
        const r = Math.max(5, Math.min(10, 8 * scale * 0.05));
        ctx.beginPath();
        ctx.arc(scr.x, scr.y, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      } else if (isHanging) {
        // Architectural Blue Pendant Light Ring
        ctx.fillStyle = "#0284C7";
        ctx.strokeStyle = "#0369A1";
        ctx.lineWidth = 1.2;
        const r = Math.max(5, Math.min(10, 8 * scale * 0.05));
        ctx.beginPath();
        ctx.arc(scr.x, scr.y, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      } else if (isDecorative) {
        // Rosette
        ctx.fillStyle = "#DB2777";
        ctx.strokeStyle = "#BE185D";
        ctx.lineWidth = 2;
        const r = Math.max(7, Math.min(14, 12 * scale * 0.05));
        ctx.beginPath();
        ctx.arc(scr.x, scr.y, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      } else if (isWorkstation) {
        // Subtle Workstation Point
        ctx.fillStyle = "#475569";
        ctx.beginPath();
        ctx.arc(scr.x, scr.y, Math.max(3, 4 * scale * 0.05), 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    });
  }
}

function drawGrid() {
  const step = 40;
  ctx.fillStyle = "rgba(15, 23, 42, 0.07)";
  for (let x = 0; x < canvas.width; x += step) {
    for (let y = 0; y < canvas.height; y += step) {
      ctx.beginPath();
      ctx.arc(x, y, 0.9, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}
