/* ===== Clave de Elasmobranquios - motor de la app ===== */
'use strict';

let TREE = null;      // {root, nodes: {id: node}}
let SPECIES = null;   // {especie_id: rec}
let history = [];     // [{nodeId, opcionIdx}] pila para "atrás"
let currentNodeId = null;

const main = document.getElementById('main');
const btnBack = document.getElementById('btn-back');
const btnRestart = document.getElementById('btn-restart');
const titleEl = document.getElementById('title');
const progressEl = document.getElementById('progress');
const statusEl = document.getElementById('status');

// ---------------------------------------------------------------------------
// Carga de datos
// ---------------------------------------------------------------------------
async function load() {
  try {
    const [t, s] = await Promise.all([
      fetch('data/tree.json').then(r => r.json()),
      fetch('data/species.json').then(r => r.json()),
    ]);
    // indexar nodos por id
    const nodes = {};
    t.nodes.forEach(n => nodes[n.id] = n);
    TREE = { root: t.root, nodes };
    SPECIES = s;
    statusEl.textContent = `${Object.keys(s).length} especies cargadas`;
    renderStart();
  } catch (e) {
    main.innerHTML = `<div class="seccion"><h3>Error</h3><div class="contenido">
      No se pudieron cargar los datos. Si abrió el archivo directamente con
      file://, algunos navegadores bloquean fetch. Use un servidor local
      (ver README) o pruebe con Firefox.<br><br><code>${e.message}</code></div></div>`;
    statusEl.textContent = 'Error de carga';
  }
}

// ---------------------------------------------------------------------------
// Render: pantalla de inicio
// ---------------------------------------------------------------------------
function renderStart() {
  titleEl.textContent = '🦈 Clave de Elasmobranquios';
  btnBack.classList.add('hidden');
  btnRestart.classList.add('hidden');
  progressEl.classList.add('hidden');
  history = [];
  const n = Object.keys(SPECIES).length;
  main.innerHTML = `
    <div class="start-screen">
      <div class="emoji">🦈</div>
      <h2>Clave de Identificación</h2>
      <p>Tiburones, rayas y quimeras de Colombia<br>
         ${n} especies — identificación por rasgos en campo</p>
      <button class="btn-primary" id="btn-start">Comenzar identificación</button>
    </div>`;
  document.getElementById('btn-start').addEventListener('click', () => {
    goTo(TREE.root);
  });
}

// ---------------------------------------------------------------------------
// Render: pregunta
// ---------------------------------------------------------------------------
function renderQuestion(node) {
  const stepNum = history.length + 1;
  titleEl.textContent = `Paso ${stepNum}`;
  btnBack.classList.toggle('hidden', history.length === 0);
  btnRestart.classList.remove('hidden');
  // barra de progreso (estimada: hasta ~9 pasos)
  const pct = Math.min(100, Math.round((history.length / 9) * 100));
  progressEl.classList.remove('hidden');
  progressEl.querySelector('.progress-fill').style.width = pct + '%';
  progressEl.querySelector('.progress-text').textContent = `Paso ${stepNum}`;

  let ayudaHtml = '';
  if (node.ayuda) {
    ayudaHtml = `<div class="q-ayuda">${escapeHtml(node.ayuda)}</div>`;
  }
  let opcionesHtml = node.opciones.map((op, i) =>
    `<button class="opcion" data-idx="${i}">${escapeHtml(op.texto)}</button>`
  ).join('');

  main.innerHTML = `
    <div class="question-screen">
      <span class="q-step">Pregunta ${stepNum}</span>
      <div class="q-pregunta">${escapeHtml(node.pregunta)}</div>
      ${ayudaHtml}
      <div class="opciones">${opcionesHtml}</div>
    </div>`;

  main.querySelectorAll('.opcion').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.idx, 10);
      handleAnswer(node, idx);
    });
  });
}

// ---------------------------------------------------------------------------
// Manejar respuesta
// ---------------------------------------------------------------------------
function handleAnswer(node, idx) {
  const op = node.opciones[idx];
  history.push({ nodeId: node.id, opcionIdx: idx });
  const sig = op.siguiente;
  if (typeof sig === 'object') {
    // hoja
    if (sig.tipo === 'especie') {
      renderSpecies(sig.especie_id);
    } else if (sig.tipo === 'grupo') {
      renderGroup(sig);
    }
  } else {
    goTo(sig);
  }
}

function goTo(nodeId) {
  currentNodeId = nodeId;
  const node = TREE.nodes[nodeId];
  if (!node) {
    console.error('Nodo no encontrado:', nodeId);
    return;
  }
  renderQuestion(node);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ---------------------------------------------------------------------------
// Atrás / Reiniciar
// ---------------------------------------------------------------------------
btnBack.addEventListener('click', () => {
  if (history.length === 0) return;
  history.pop();
  if (history.length === 0) {
    renderStart();
  } else {
    // volver al nodo padre del último paso
    const last = history[history.length - 1];
    const parentNode = TREE.nodes[last.nodeId];
    const parentOp = parentNode.opciones[last.opcionIdx];
    // el nodo donde estábamos era hijo de parentNode
    // para revivir: ir al nodo anterior en el historial
    history.pop(); // quitar el último que acabamos de mirar
    if (history.length === 0) {
      renderStart();
    } else {
      const prev = history[history.length - 1];
      const pn = TREE.nodes[prev.nodeId];
      const pop = pn.opciones[prev.opcionIdx];
      if (typeof pop.siguiente === 'string') {
        goTo(pop.siguiente);
      } else {
        renderStart();
      }
    }
  }
});

btnRestart.addEventListener('click', renderStart);

// ---------------------------------------------------------------------------
// Render: ficha de especie
// ---------------------------------------------------------------------------
function renderSpecies(eid) {
  const sp = SPECIES[eid];
  if (!sp) { main.innerHTML = '<p>Especie no encontrada.</p>'; return; }
  titleEl.textContent = 'Resultado';
  btnBack.classList.remove('hidden');
  btnRestart.classList.remove('hidden');
  progressEl.classList.add('hidden');

  const cons = sp.conservacion || {};
  const morf = sp.morfometria || {};
  const dist = sp.distribucion || {};
  const rep = sp.reproduccion || {};

  // badges de conservación
  const badges = [];
  if (cons.IUCN) badges.push(iucnBadge(cons.IUCN));
  if (cons.CITES && String(cons.CITES).toLowerCase() !== 'no listada'
      && cons.CITES !== null) {
    badges.push(`<span class="badge CITES">CITES ${escapeHtml(cons.CITES)}</span>`);
  }
  if (cons.libro_rojo && String(cons.libro_rojo).toLowerCase() !== 'no incluida'
      && cons.libro_rojo !== null) {
    badges.push(`<span class="badge LR">Libro Rojo ${escapeHtml(cons.libro_rojo)}</span>`);
  }
  const badgesHtml = badges.length
    ? `<div class="badges">${badges.join('')}</div>` : '';

  // alerta protegida
  let alertaHtml = '';
  if (cons.protegida) {
    alertaHtml = `<div class="alerta-protegida">
      <span class="icon">⚠️</span>
      <div><strong>Especie protegida.</strong> Su captura y comercio están
      restringidos o prohibidos. Si la captura de forma incidental,
      devuélvala al mar viva en lo posible.</div>
    </div>`;
  }

  // distribución legible
  let distParts = [];
  if (dist.caribe) distParts.push('Caribe');
  if (dist.pacifico) distParts.push('Pacífico');
  if (dist.aguas_continentales) distParts.push('agua dulce');
  const distText = distParts.length ? distParts.join(', ') : 'No disponible';

  // talla legible
  let tallaText = 'No disponible';
  if (morf.talla_max_cm) {
    tallaText = morf.talla_max_cm >= 100
      ? (morf.talla_max_cm / 100).toFixed(morf.talla_max_cm % 100 === 0 ? 0 : 1) + ' m'
      : Math.round(morf.talla_max_cm) + ' cm';
  }
  // profundidad
  let profText = 'No disponible';
  if (morf.profundidad_min_m != null && morf.profundidad_max_m != null) {
    profText = `${morf.profundidad_min_m}–${morf.profundidad_max_m} m`;
  }

  // tipo reproducción legible
  let repTipo = rep.tipo || '';
  const repMap = {
    'VIA': 'Vivípara aplacentaria',
    'VIP': 'Vivípara placentaria',
    'OVI': 'Ovípara (pone huevos en cápsulas)',
  };
  if (repMap[repTipo]) repTipo = repMap[repTipo];

  main.innerHTML = `
    <div class="ficha">
      <div class="ficha-header">
        <div class="nombre-cientifico">${escapeHtml(sp.nombre_cientifico || '')}</div>
        <div class="nombre-comun">${escapeHtml(sp.nombre_comun_es || '')}</div>
        ${sp.nombre_comun_en ? `<div class="nombre-comun-en">${escapeHtml(sp.nombre_comun_en)}</div>` : ''}
        <div class="familia-tag">${escapeHtml(sp.familia || '')} · ${escapeHtml(sp.orden || '')}</div>
      </div>

      ${alertaHtml}

      <div class="seccion">
        <h3>🛡️ Estado de conservación</h3>
        <div class="contenido">${badgesHtml || '<p>Sin datos de conservación.</p>'}</div>
      </div>

      <div class="seccion">
        <h3>📏 Morfometría y hábitat</h3>
        <div class="contenido">
          <p><span class="key">Talla máxima:</span> ${tallaText}</p>
          <p><span class="key">Profundidad:</span> ${profText}</p>
          <p><span class="key">Distribución:</span> ${distText}</p>
        </div>
      </div>

      ${sp.caracteristica ? `<div class="seccion">
        <h3>🔍 Rasgos distintivos</h3>
        <div class="contenido">${escapeHtml(sp.caracteristica)}</div>
      </div>` : ''}

      ${sp.descripcion ? `<div class="seccion">
        <h3>📝 Descripción morfológica</h3>
        <div class="contenido">${escapeHtml(sp.descripcion)}</div>
      </div>` : ''}

      ${sp.coloracion ? `<div class="seccion">
        <h3>🎨 Coloración</h3>
        <div class="contenido">${escapeHtml(sp.coloracion)}</div>
      </div>` : ''}

      <div class="seccion">
        <h3>🐣 Reproducción</h3>
        <div class="contenido">
          ${repTipo ? `<p><span class="key">Tipo:</span> ${escapeHtml(repTipo)}</p>` : '<p>No disponible.</p>'}
          ${rep.texto ? `<p>${escapeHtml(rep.texto)}</p>` : ''}
        </div>
      </div>

      <button class="btn-secondary" id="btn-repeat">🔄 Identificar otro ejemplar</button>
    </div>`;

  document.getElementById('btn-repeat').addEventListener('click', renderStart);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function iucnBadge(cat) {
  const c = String(cat).toUpperCase();
  const labels = {
    CR: 'CR · En Peligro Crítico', EN: 'EN · En Peligro',
    VU: 'VU · Vulnerable', NT: 'NT · Casi Amenazada',
    LC: 'LC · Preocupación Menor', DD: 'DD · Datos Insuficientes',
  };
  const cls = ['CR','EN','VU','NT','LC','DD'].includes(c) ? `IUCN-${c}` : 'neutral';
  return `<span class="badge ${cls}">IUCN ${labels[c] || cat}</span>`;
}

// ---------------------------------------------------------------------------
// Render: grupo candidato
// ---------------------------------------------------------------------------
function renderGroup(leaf) {
  titleEl.textContent = 'Compare las especies';
  btnBack.classList.remove('hidden');
  btnRestart.classList.remove('hidden');
  progressEl.classList.add('hidden');

  const items = leaf.especie_ids.map(eid => {
    const sp = SPECIES[eid];
    if (!sp) return null;
    const morf = sp.morfometria || {};
    let talla = '?';
    if (morf.talla_max_cm) {
      talla = morf.talla_max_cm >= 100
        ? (morf.talla_max_cm / 100).toFixed(1) + ' m'
        : Math.round(morf.talla_max_cm) + ' cm';
    }
    const dparts = [];
    if (sp.distribucion && sp.distribucion.caribe) dparts.push('Caribe');
    if (sp.distribucion && sp.distribucion.pacifico) dparts.push('Pacífico');
    return `<div class="grupo-item" data-eid="${eid}">
      <div class="gn">${escapeHtml(sp.nombre_cientifico)}</div>
      <div class="gc">${escapeHtml(sp.nombre_comun_es || '')}</div>
      <div class="meta">📏 ${talla} · 📍 ${dparts.join('/') || '?'}
        ${sp.caracteristica ? ' · ' + escapeHtml(sp.caracteristica.slice(0, 50)) : ''}</div>
    </div>`;
  }).filter(Boolean).join('');

  main.innerHTML = `
    <div class="grupo">
      <h2>${escapeHtml(leaf.titulo || 'Especies candidatas')}</h2>
      <p class="intro">Varias especies comparten estos rasgos. Toque una para
      ver su ficha completa y comparar los detalles.</p>
      <div class="grupo-lista">${items}</div>
      <button class="btn-secondary" id="btn-repeat">🔄 Empezar de nuevo</button>
    </div>`;

  main.querySelectorAll('.grupo-item').forEach(el => {
    el.addEventListener('click', () => renderSpecies(el.dataset.eid));
  });
  document.getElementById('btn-repeat').addEventListener('click', renderStart);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------
function escapeHtml(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ---------------------------------------------------------------------------
// Service worker (offline)
// ---------------------------------------------------------------------------
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('sw.js').catch(() => {});
  });
}

// ---------------------------------------------------------------------------
// Arranque
// ---------------------------------------------------------------------------
load();
