# -*- coding: utf-8 -*-
"""
Fase 1 — Extraccion de descripciones del PDF de la guia SQUALUS 2011.

Patron verificado (CONSISTENTE en todo el documento):
  - Pagina PAR  = DATOS de la especie N  (primera linea = nombre cientifico,
                  contiene "Familia").
  - Pagina IMPAR siguiente = DESCRIPCION de la especie N (empieza con
                  "Descripcion").

Estructura del texto de la pagina de descripcion:
    Descripcion
    <texto descripcion>
    Coloracion: <texto coloracion>   (encabezado inline con dos puntos)
    <texto reproductivo>             (sin encabezado previo)
    Aspectos reproductivos           (encabezado que aparece DESPUES del texto)
    CITES / IUCN / LIBRO ROJO + valores
    Distribucion + n pagina

Salida: build/pdf_descriptions.json
"""
import json
import os
import re
import glob
import unicodedata

import fitz  # PyMuPDF

BASE = r"C:\Users\panma\Desktop\Elasms"
PDF = r"C:\Users\panma\Downloads\02_Hidrologia_y_Medio_Ambiente\guia_tiburones_rayas_quimeras.pdf"
JSON_DIR = BASE
OUT = os.path.join(BASE, "clave-app", "build", "pdf_descriptions.json")


def _norm(s):
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"\s*\(.*?\)", "", s)           # quitar autor entre parentesis
    s = re.sub(r"\s*-\s*.*$", "", s)           # quitar " - nombre comun"
    s = re.sub(r"/.*$", "", s)                 # "Pristis perotteti / zephyreus"
    s = "".join(c for c in unicodedata.normalize("NFD", s)
                if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z ]", "", s)
    # Tolerancia a variantes ortograficas frecuentes en la literatura:
    #   i <-> y   (hipostoma/hypostoma), dobles consonantes (harriota/harriotta),
    #   c <-> s,  c <-> k.
    s = (s.replace("y", "i")
           .replace("ph", "f")
           .replace("rr", "r").replace("ll", "l").replace("nn", "n")
           .replace("tt", "t").replace("ss", "s").replace("pp", "p"))
    s = re.sub(r"\s+", " ", s).strip()
    # primeras dos palabras (genero + especie) para tolerar variantes
    parts = s.split()
    return " ".join(parts[:2]) if len(parts) >= 2 else s


def load_targets():
    targets = {}
    files = sorted(glob.glob(os.path.join(JSON_DIR, "*.json")))

    def add(nom, eid, fam):
        if not nom:
            return
        key = _norm(nom)
        if key and key not in targets:
            targets[key] = {"especie_id": eid, "nombre": nom, "familia": fam}

    for f in files:
        if "clave-app" in f:
            continue
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if "taxonomia" in d and "nombre_cientifico" in d.get("taxonomia", {}):
            t = d["taxonomia"]
            fam = t.get("familia") or d.get("metadata", {}).get("familia")
            eid = d.get("especie_id") or d.get("metadata", {}).get("especie_id")
            add(t["nombre_cientifico"], eid, fam)
        for key in ("resumen_especies", "especies"):
            if isinstance(d.get(key), list):
                for sp in d[key]:
                    add(sp.get("nombre_cientifico"), sp.get("especie_id"),
                        (d.get("metadata_familia", {}) or {}).get("familia"))
        for k, v in d.items():
            if isinstance(v, dict) and isinstance(v.get("especies"), list):
                for sp in v["especies"]:
                    add(sp.get("nombre_cientifico"), sp.get("especie_id"),
                        v.get("familia") or k)
    return targets


def parse_desc_page(text):
    """Parsea una pagina de descripcion en sus tres bloques."""
    t = text.replace("\r\n", "\n").replace("\r", "\n")

    # --- Limpiar marca de final: seccion de conservacion + distribucion + npag ---
    # Cortar en "Aspectos reproductivos" (encabezado que cierra el bloque reprod)
    m_ar = re.search(r"(?m)^\s*Aspectos\s+reproductivos\s*$", t)
    ar_pos = m_ar.start() if m_ar else None

    # Bloque de conservacion al final: CITES/IUCN/LIBRO ROJO + Distribucion
    m_cons = re.search(r"(?m)^\s*CITES\s*$", t)
    cons_pos = m_cons.start() if m_cons else None

    # ---- Descripcion ----
    # El encabezado "Descripcion" suele iniciar la pagina, pero en algunas
    # fichas (p.ej. Pristis pectinata) aparece al FINAL. Para detectar el
    # caso valido, exigimos que "Descripcion" este antes de "Coloracion:".
    m_col_label = re.search(r"(?im)\bColoraci[oó]n\s*:", t)
    col_label_pos = m_col_label.start() if m_col_label else None
    m_desc = re.search(r"(?m)^\s*Descripci[oó]n\s*:?\s*$", t)
    if m_desc and (col_label_pos is None or m_desc.start() < col_label_pos):
        desc_start = m_desc.end()
    else:
        # El encabezado "Descripcion" falta o va al final: toda la pagina
        # (hasta Coloracion/CITES) es la descripcion.
        desc_start = 0
    # limite superior de la descripcion: Coloracion o CITES
    desc_end_candidates = []
    if col_label_pos is not None:
        desc_end_candidates.append(col_label_pos)
    if cons_pos:
        desc_end_candidates.append(cons_pos)
    if ar_pos:
        desc_end_candidates.append(ar_pos)
    desc_end = min(desc_end_candidates) if desc_end_candidates else len(t)
    descripcion = t[desc_start:desc_end].strip()

    # ---- Coloracion ----
    coloracion = ""
    col_start = m_col_label.end() if m_col_label else None
    # El texto reproductivo suele empezar con "Especie vivipara/ovipara".
    # Lo buscamos en toda la pagina (no solo despues de Coloracion), porque a
    # veces la descripcion de coloracion va ANTES del encabezado "Coloracion:".
    m_rep_start = re.search(r"(?im)\bEspecie\s+(viv[íi]para|ov[íi]para)", t)
    rep_text_start = m_rep_start.start() if m_rep_start else None

    if col_start is not None and rep_text_start is not None and rep_text_start > col_start:
        # coloracion entre "Coloracion:" y el texto reproductivo
        coloracion = t[col_start:rep_text_start].strip()
        if not coloracion:
            # el texto descriptivo iba antes del encabezado; tomar la ultima
            # linea de la descripcion como coloracion
            tail = descripcion.split("\n")
            if tail:
                coloracion = tail[-1].strip()
                descripcion = "\n".join(tail[:-1]).strip()
        rep_start = rep_text_start
    elif rep_text_start is not None:
        # no hay encabezado Coloracion: la coloracion va antes de "Especie..."
        # tomar la ultima linea descriptiva
        rep_start = rep_text_start
        before = t[desc_start:rep_text_start].strip()
        tail = before.split("\n")
        if len(tail) > 1:
            coloracion = tail[-1].strip()
            descripcion = "\n".join(tail[:-1]).strip()
    else:
        # sin texto reproductivo identificable
        coloracion = ""
        rep_start = desc_end

    # ---- Reproductivos: desde rep_start hasta el encabezado
    #       "Aspectos reproductivos" (o CITES si falta) ----
    if ar_pos and ar_pos > rep_start:
        rep_end = ar_pos
    elif cons_pos and cons_pos > rep_start:
        rep_end = cons_pos
    else:
        rep_end = len(t)
    reproductivos = t[rep_start:rep_end].strip()

    # Limpiar numeros de pagina sueltos y "Distribucion" final
    reproductivos = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", reproductivos).strip()
    reproductivos = re.sub(r"(?m)^\s*Distribuci[oó]n\s*$.*", "", reproductivos,
                           flags=re.DOTALL).strip()
    coloracion = re.sub(r"(?m)^\s*Distribuci[oó]n\s*$.*", "", coloracion,
                        flags=re.DOTALL).strip()

    return {
        "descripcion": descripcion,
        "coloracion": coloracion,
        "reproductivos": reproductivos,
    }


def extract(targets):
    doc = fitz.open(PDF)
    npages = doc.page_count
    print(f"PDF: {npages} paginas | especies objetivo: {len(targets)}")

    results = {}        # especie_id -> rec
    by_name = {}        # nombre_norm -> rec (sin id)
    matched = set()

    skip_labels = {"familia", "orden", "descripción", "coloración",
                   "descriptor", "descriptor de la especie",
                   "hábitat", "hábitos", "dieta", "comercialización",
                   "talla máxima", "profundidad", "consumo", "pesquería"}
    for pno in range(0, npages):
        text = doc[pno].get_text("text")
        if not text or "Familia" not in text:
            continue
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        # Probar TODAS las lineas candidatas como posible nombre cientifico.
        # El layout varia: a veces el nombre va al inicio, a veces despues del
        # bloque de iconos de habitat/habitos/dieta.
        key = None
        nom_pdf = None
        for ln in lines:
            low = ln.lower().strip()
            if low in skip_labels or "familia" in low or "orden" in low:
                continue
            if re.fullmatch(r"\d{1,3}", ln):
                continue
            k = _norm(ln)
            if k in targets:
                key = k
                nom_pdf = ln
                break
            # tolerar "Genero especie - nombre comun"
            k2 = _norm(ln.split(" - ")[0])
            if k2 in targets:
                key = k2
                nom_pdf = ln.split(" - ")[0]
                break
        if key is None:
            continue
        # pagina de descripcion = pno + 1
        desc_pno = pno + 1
        if desc_pno >= npages:
            continue
        desc_text = doc[desc_pno].get_text("text")
        blocks = parse_desc_page(desc_text)
        if not blocks:
            continue
        tgt = targets[key]
        rec = {
            "especie_id": tgt["especie_id"],
            "nombre_cientifico": tgt["nombre"],
            "nombre_cientifico_pdf": nom_pdf,
            "familia": tgt["familia"],
            "pagina_pdf_datos": pno + 1,
            "pagina_pdf_desc": desc_pno + 1,
            **blocks,
        }
        if tgt["especie_id"] is not None:
            results[tgt["especie_id"]] = rec
        else:
            by_name[key] = rec
        matched.add(key)

    doc.close()
    return results, by_name, matched, targets


def main():
    targets = load_targets()
    print(f"Especies objetivo cargadas: {len(targets)}")
    results, by_name, matched, targets = extract(targets)

    print("\n" + "=" * 60)
    print(f"Fichas con especie_id: {len(results)}")
    print(f"Fichas sin id (por nombre): {len(by_name)}")
    print(f"Total matcheadas: {len(matched)} / {len(targets)}")

    missing = [v["nombre"] for k, v in targets.items() if k not in matched]
    if missing:
        print(f"\nNO encontradas ({len(missing)}):")
        for m in sorted(missing):
            print(f"   - {m}")

    # guardar
    out = {}
    next_id = -1
    for eid, rec in sorted(results.items(), key=lambda x: str(x[0])):
        out[str(eid)] = rec
    for key, rec in by_name.items():
        out[f"name__{key}"] = rec

    json.dump(out, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\nGuardado: {OUT}")

    # muestras: una limpia y una problematica
    print("\n--- MUESTRA Carcharhinus acronotus ---")
    r = results.get(40)
    if r:
        print("DESC:", r["descripcion"][:250])
        print("COL :", r["coloracion"][:150])
        print("REP :", r["reproductivos"][:200])

    print("\n--- MUESTRA Prionace glauca ---")
    r = results.get(53)
    if r:
        print("DESC:", r["descripcion"][:250])
        print("COL :", r["coloracion"][:150])
        print("REP :", r["reproductivos"][:200])


if __name__ == "__main__":
    main()
