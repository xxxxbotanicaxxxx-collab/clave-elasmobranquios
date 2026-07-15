# 🦈 Clave de Identificación de Elasmobranquios de Colombia

Clave taxonómica **interactiva y offline** para que pescadores, técnicos y
naturalistas identifiquen en campo **tiburones, rayas y quimeras** de aguas
colombianas mediante preguntas sobre rasgos morfológicos visibles.

Cubre **114 especies** (51 tiburones, 60 rayas y 3 quimeras) documentadas en la
*Guía para la identificación de especies de tiburones, rayas y quimeras de
Colombia* (SQUALUS, 2011).

---

## ✨ Características

- **Funciona sin internet** (offline, instalable como app en el móvil).
- **Clave dicotómica** por rasgos morfológicos: forma del cuerpo, aletas,
  branquias, disco, cola, espinas, etc.
- **Ficha de especie** con: estado de conservación (IUCN / CITES / Libro Rojo),
  alertas de especies protegidas, reproducción y tallas de madurez,
  descripción morfológica y coloración.
- **Botón de retroceso** para corregir respuestas en cualquier momento.
- Diseño **mobile-first**, con botones grandes aptos para uso en lancha.

---

## 📱 Cómo usarla

### Opción A — En el móvil (instalable, offline)
1. Suba la carpeta `clave-app/` a cualquier hosting estático (GitHub Pages,
   Netlify, o un servidor local en su red).
2. Ábrala en el navegador del móvil (Chrome / Edge / Safari).
3. Use el menú del navegador → **"Agregar a pantalla de inicio"**.
4. A partir de ahí funciona como una app, **sin conexión a internet**.

### Opción B — En el computador (servidor local)
La app necesita servirse por HTTP (no se abre con doble-clic sobre el HTML,
porque el navegador bloquea la carga de datos locales). Desde la carpeta
`clave-app/`:

```bash
# Python (ya instalado en este equipo)
python -m http.server 8765
```

Luego abrir en el navegador: **http://localhost:8765**

> En el navegador **Firefox** sí suele funcionar abrir `index.html` directamente
> con doble-clic; Chrome y Edge requieren el servidor local.

---

## 🔬 Cómo funciona la identificación

La clave recorre un **árbol dicotómico de 44 nodos**. Cada paso formula una
pregunta sobre un rasgo visible (número de dorsales, forma del hocico, tipo de
cola, etc.) y el usuario elige la opción que observa. Tras 2 a 9 pasos se llega
al resultado.

**Estructura de las ramas superiores** (rasgos diagnósticos grandes):

```
Forma del cuerpo
├── Tiburón  →  nº de branquias  →  aleta anal  →  nictitante/barbillones  →  familias
├── Raya     →  hocico en sierra / órgano eléctrico / forma del disco / tipo de cola  →  familias
└── Quimera  →  forma del hocico  →  Chimaeridae / Rhinochimaeridae
```

Cuando varias especies de una misma familia comparten todos los rasgos
visibles y no pueden separarse con fiabilidad por morfología de campo, la clave
termina en un **grupo candidato** que muestra las especies posibles para
compararlas por talla, distribución y rasgos finos.

---

## 📁 Estructura de archivos

```
clave-app/
├── index.html          · página única
├── styles.css          · estilos mobile-first
├── app.js              · motor de la clave (recorrido, fichas, grupos)
├── sw.js               · service worker (caché offline)
├── manifest.json       · manifiesto PWA (instalable)
├── data/
│   ├── species.json    · 114 especies normalizadas + rasgos
│   └── tree.json       · árbol dicotómico (44 nodos)
└── build/
    ├── extract_pdf.py      · Fase 1: extracción de la guía PDF
    ├── normalize.py        · Fase 2: normalización + codificación de rasgos
    ├── build_tree.py       · Fase 3: generación del árbol
    └── pdf_descriptions.json
```

Los scripts de `build/` permiten regenerar los datos desde cero (fuente JSON
original + guía PDF).

---

## 🛡️ Aviso importante sobre especies protegidas

La clave marca con una **alerta naranja** las especies cuya captura o comercio
están restringidos o prohibidos (CITES Apéndice I, Libro Rojo CR/EN, y todos los
peces sierra — *Pristidae*). Si se capturan de forma incidental, **deben
devolverse al mar vivos**.

---

## 📚 Fuente de los datos

- **Guía para la identificación de especies de tiburones, rayas y quimeras de
  Colombia** (SQUALUS, 2011). Las descripciones morfológicas, coloración y
  aspectos reproductivos se extrajeron por parsing del PDF original.
- Dataset JSON de partida del usuario (44 archivos con taxonomía, distribución,
  conservación y pesquería).
- Los rasgos diagnósticos a nivel de orden/familia se basan en la taxonomía
  clásica de elasmobranquios (estables y verificables).

Cada rasgo en `species.json` lleva marca de **fuente** (`taxonomia`, `json` o
`pdf`) para mantener la trazabilidad.

---

## 🔄 Regenerar los datos

Si se modifican los JSON originales o la guía, regenere con (desde `build/`):

```bash
python extract_pdf.py     # Fase 1 -> pdf_descriptions.json
python normalize.py       # Fase 2 -> data/species.json
python build_tree.py      # Fase 3 -> data/tree.json
```

Requiere Python 3.10+ con `PyMuPDF` (`pip install pymupdf`).

---

## 📝 Limitaciones conocidas

- **Sin imágenes** por ahora (solo texto). La estructura está lista para añadir
  ilustraciones o fotos por especie en el futuro.
- Algunas especies de familias con datos morfológicos homogéneos (rayas látigo,
  rajidos de profundidad) terminan en grupo candidato, ya que la separación
  especie-a-especie requiere examen detallado de laboratorio.
- Los rasgos finos (cresta interdorsal, espiráculos) están disponibles solo
  donde la guía los menciona explícitamente.
