# -*- coding: utf-8 -*-
"""
Fase 2 — Normalizacion a esquema unico + codificacion de rasgos de clave.

Fusiona:
  - Los 44 JSON del usuario (3 esquemas distintos).
  - Las descripciones extraidas del PDF (build/pdf_descriptions.json).

Produce data/species.json con un esquema uniforme por especie, incluyendo
un bloque "rasgos" estructurado que alimenta el arbol dicotomico.

Los rasgos grandes (cuerpo_forma, num_dorsales, branquiales, aleta_anal,
etc.) se infieren del orden/familia mediante una tabla taxonomica estable.
Los rasgos especificos (cresta interdorsal, espiraculos, forma del disco,
coloracion) se extraen del JSON/PDF cuando existen, con marca de fuente.
"""
import json
import os
import re
import glob
import unicodedata

BASE = r"C:\Users\panma\Desktop\Elasms"
APP = os.path.join(BASE, "clave-app")
PDF_DESC = os.path.join(APP, "build", "pdf_descriptions.json")
OUT = os.path.join(APP, "data", "species.json")

# ---------------------------------------------------------------------------
# Tabla taxonomica: rasgos diagnosticos estables por orden/familia.
# Fuente: taxonomia clasica de elasmobranquios (Compagno; guia SQUALUS 2011).
# cuerpo_forma: "tiburon" | "raya" | "quimera"
# ---------------------------------------------------------------------------
# Cada entrada: (orden, familia) -> rasgos por defecto
TAXON = {
    # ---------------- TIBURONES ----------------
    # Hexanchiformes: 1 dorsal, 6-7 branquias, sin anal
    "Hexanchidae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                        num_dorsales=1, branquiales=6, aleta_anal=True,
                        orden="Hexanchiformes"),
    # Squaliformes: 2 dorsales con espina, sin anal
    "Centrophoridae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                           num_dorsales=2, espinas_dorsales=True,
                           aleta_anal=False, orden="Squaliformes"),
    "Etmopteridae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                         num_dorsales=2, espinas_dorsales=True,
                         aleta_anal=False, orden="Squaliformes"),
    "Squalidae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                      num_dorsales=2, espinas_dorsales=True,
                      aleta_anal=False, orden="Squaliformes"),
    "Centroscylliidae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                             num_dorsales=2, espinas_dorsales=True,
                             aleta_anal=False, orden="Squaliformes"),
    # Squatiniformes: cuerpo aplanado tipo raya PERO es tiburon; sin anal
    "Squatinidae": dict(grupo="tiburon", cuerpo_forma="tiburon_angel",
                        num_dorsales=2, aleta_anal=False,
                        orden="Squatiniformes"),
    # Pristiophoriformes: hocico sierra (no en dataset)
    # Heterodontiformes: 2 dorsales con espina, anal presente
    "Heterodontidae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                           num_dorsales=2, espinas_dorsales=True,
                           aleta_anal=True, orden="Heterodontiformes"),
    # Orectolobiformes: 2 dorsales, anal presente, sin nictitante, barbillones
    "Ginglymostomatidae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                               num_dorsales=2, aleta_anal=True,
                               membrana_nictitante=False, barbillones=True,
                               orden="Orectolobiformes"),
    "Rhincodontidae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                           num_dorsales=2, aleta_anal=True,
                           membrana_nictitante=False, barbellones=True,
                           orden="Orectolobiformes"),
    # Lamniformes: 2 dorsales, anal, sin nictitante
    "Alopiidae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                      num_dorsales=2, aleta_anal=True,
                      membrana_nictitante=False, orden="Lamniformes"),
    "Lamnidae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                     num_dorsales=2, aleta_anal=True,
                     membrana_nictitante=False, orden="Lamniformes"),
    "Mitsukurinidae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                           num_dorsales=2, aleta_anal=True,
                           membrana_nictitante=False, orden="Lamniformes"),
    "Odontaspididae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                           num_dorsales=2, aleta_anal=True,
                           membrana_nictitante=False, orden="Lamniformes"),
    # Carcharhiniformes: 2 dorsales, anal, CON nictitante
    "Carcharhinidae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                           num_dorsales=2, aleta_anal=True,
                           membrana_nictitante=True, orden="Carcharhiniformes"),
    "Sphyrnidae": dict(grupo="tiburon", cuerpo_forma="tiburon_martillo",
                       num_dorsales=2, aleta_anal=True,
                       membrana_nictitante=True, orden="Carcharhiniformes"),
    "Scyliorhinidae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                           num_dorsales=2, aleta_anal=True,
                           membrana_nictitante=True, orden="Carcharhiniformes"),
    "Triakidae": dict(grupo="tiburon", cuerpo_forma="tiburon",
                      num_dorsales=2, aleta_anal=True,
                      membrana_nictitante=True, orden="Carcharhiniformes"),
    # ---------------- RAYAS ----------------
    # Pristidae: hocico en sierra, cuerpo tipo tiburon, 2 dorsales, agua dulce
    "Pristidae": dict(grupo="raya", cuerpo_forma="tiburon_sierra",
                      num_dorsales=2, aleta_anal=False, sierra=True,
                      cola_tipo="robusta", orden="Pristiformes"),
    # Torpediniformes: organo electrico, disco circular, 2 dorsales
    "Narcinidae": dict(grupo="raya", cuerpo_forma="raya",
                       num_dorsales=2, organo_electrico=True,
                       cola_tipo="robusta", orden="Torpediniformes"),
    "Torpedinidae": dict(grupo="raya", cuerpo_forma="raya",
                         num_dorsales=2, organo_electrico=True,
                         cola_tipo="robusta", orden="Torpediniformes"),
    # Rajiformes (Rajidae): disco romboidal, cola delgada SIN espina venenosa
    "Rajidae": dict(grupo="raya", cuerpo_forma="raya",
                    num_dorsales=2, cola_tipo="delgada",
                    espina_caudal_venenosa=False,
                    disco_forma="romboidal", orden="Rajiformes"),
    "Anacanthobatidae": dict(grupo="raya", cuerpo_forma="raya",
                             num_dorsales=0, cola_tipo="delgada",
                             espina_caudal_venenosa=False,
                             disco_forma="romboidal", orden="Rajiformes"),
    # Rhinobatidae: cuerpo guitarra, 2 dorsales
    "Rhinobatidae": dict(grupo="raya", cuerpo_forma="raya_guitarra",
                         num_dorsales=2, aleta_anal=False,
                         cola_tipo="robusta", orden="Rajiformes"),
    # Myliobatiformes: cola látigo con espina venenosa
    "Dasyatidae": dict(grupo="raya", cuerpo_forma="raya",
                       num_dorsales=0, cola_tipo="latigo",
                       espina_caudal_venenosa=True,
                       disco_forma="romboidal", orden="Myliobatiformes"),
    "Potamotrygonidae": dict(grupo="raya", cuerpo_forma="raya",
                             num_dorsales=0, cola_tipo="latigo",
                             espina_caudal_venenosa=True,
                             disco_forma="redondeado", agua_dulce=True,
                             orden="Myliobatiformes"),
    "Urotrygonidae": dict(grupo="raya", cuerpo_forma="raya",
                          num_dorsales=0, cola_tipo="latigo",
                          espina_caudal_venenosa=True,
                          disco_forma="redondeado", orden="Myliobatiformes"),
    "Gymnuridae": dict(grupo="raya", cuerpo_forma="raya",
                       num_dorsales=0, cola_tipo="corta",
                       espina_caudal_venenosa=True,
                       disco_forma="mariposa", orden="Myliobatiformes"),
    "Myliobatidae": dict(grupo="raya", cuerpo_forma="raya_manta",
                         num_dorsales=0, cola_tipo="latigo",
                         espina_caudal_venenosa=False,
                         disco_forma="ala", orden="Myliobatiformes"),
    # ---------------- QUIMERAS ----------------
    "Rhinochimaeridae": dict(grupo="quimera", cuerpo_forma="quimera",
                             num_dorsales=2, espinas_dorsales=True,
                             branquiales="operculo", hocico_forma="largo",
                             orden="Chimaeriformes"),
    "Chimaeridae": dict(grupo="quimera", cuerpo_forma="quimera",
                        num_dorsales=2, espinas_dorsales=True,
                        branquiales="operculo", hocico_forma="corto",
                        orden="Chimaeriformes"),
}

# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _cap_familia(fam):
    """Normaliza 'rhinochimaeridae' -> 'Rhinochimaeridae'."""
    if not fam:
        return fam
    f = str(fam).strip()
    # quitar prefijos comunes
    f = re.sub(r"^familia[\s_]+", "", f, flags=re.I)
    return f[:1].upper() + f[1:]

def _strip(s):
    if s is None:
        return ""
    return str(s).strip()

def to_float(v):
    """Extrae un numero (posiblemente de una cadena tipo '2.2 m')."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"(\d+(?:[.,]\d+)?)", str(v))
    return float(m.group(1).replace(",", ".")) if m else None

def parse_talla_cm(raw, unidad=None):
    """Devuelve talla en cm a partir de valor + unidad."""
    val = to_float(raw)
    if val is None:
        return None
    u = (unidad or "").lower()
    if u.startswith("m") and not u.startswith("mm") and val < 100:
        # metros -> cm (si val<100, evita confundir 120 cm etiquetado 'm')
        return val * 100
    return val

def parse_profundidad(raw):
    """Devuelve (min_m, max_m) desde '0 - 75 m' o dict."""
    if isinstance(raw, dict):
        return (to_float(raw.get("minima")),
                to_float(raw.get("maxima")))
    if raw is None:
        return (None, None)
    s = str(raw)
    nums = re.findall(r"\d+", s)
    if len(nums) >= 2:
        return (float(nums[0]), float(nums[1]))
    if len(nums) == 1:
        return (0.0, float(nums[0]))
    return (None, None)

def parse_distribucion(raw):
    """Devuelve dict {caribe, pacifico, aguas_continentales}."""
    out = {"caribe": False, "pacifico": False,
           "aguas_continentales": False}
    if raw is None:
        return out
    if isinstance(raw, dict):
        # esquema A detallado
        am = raw.get("aguas_marinas", {})
        if isinstance(am, dict):
            mc = am.get("mar_caribe", {})
            op = am.get("oceano_pacifico", {})
            if isinstance(mc, dict) and mc.get("zonas_confirmadas"):
                out["caribe"] = True
            if isinstance(op, dict) and op.get("zonas_confirmadas"):
                out["pacifico"] = True
        ac = raw.get("aguas_continentales", {})
        if isinstance(ac, dict) and ac.get("cuencas_confirmadas"):
            out["aguas_continentales"] = True
        desc = _strip(raw.get("descripcion")).lower()
        if "dulce" in desc or "rioc" in desc or "cuencas" in desc:
            out["aguas_continentales"] = True
        return out
    # cadena
    s = _strip(raw).lower()
    if "caribe" in s:
        out["caribe"] = True
    if "pacífico" in s or "pacifico" in s:
        out["pacifico"] = True
    if "dulce" in s or "rioc" in s or "estuario" in s:
        out["aguas_continentales"] = True
    return out


# ---------------------------------------------------------------------------
# Recolectar todas las especies de los 3 esquemas JSON
# ---------------------------------------------------------------------------
def harvest_json_species():
    """Devuelve {especie_id: {campos crudos}} unificando los 44 JSON."""
    species = {}
    files = sorted(glob.glob(os.path.join(BASE, "*.json")))

    def norm_id(eid):
        return str(eid) if eid is not None else None

    for f in files:
        if "clave-app" in f:
            continue
        d = json.load(open(f, encoding="utf-8"))

        # Esquema A/B: especie detallada
        if "taxonomia" in d and "nombre_cientifico" in d.get("taxonomia", {}):
            t = d["taxonomia"]
            eid = norm_id(d.get("especie_id") or d.get("metadata", {}).get("especie_id"))
            if not eid:
                continue
            sp = species.setdefault(eid, {"especie_id": eid})
            sp["nombre_cientifico"] = t.get("nombre_cientifico")
            sp["nombre_comun_es"] = t.get("nombre_cientifico") and None
            sp["nombre_comun_es"] = t.get("nombre_comun_espanol") or t.get("nombre_comun")
            sp["nombre_comun_en"] = t.get("nombre_comun_ingles") or t.get("nombre_comun_en")
            sp["familia"] = t.get("familia") or d.get("metadata", {}).get("familia")
            sp["orden"] = t.get("orden") or d.get("metadata", {}).get("orden")
            sp["_fuente_json"] = os.path.basename(f)
            # morfometria
            morf = d.get("morfometria") or d.get("morfologia", {})
            if isinstance(morf, dict):
                if "talla_maxima" in morf:
                    tm = morf["talla_maxima"]
                    sp["talla_max_cm"] = parse_talla_cm(
                        tm.get("valor") if isinstance(tm, dict) else tm,
                        tm.get("unidad") if isinstance(tm, dict) else None)
                elif "talla_maxima_cm" in morf:
                    sp["talla_max_cm"] = to_float(morf["talla_maxima_cm"])
                if "profundidad" in morf:
                    sp["prof_min_m"], sp["prof_max_m"] = parse_profundidad(
                        morf["profundidad"])
                elif "profundidad_min_m" in morf:
                    sp["prof_min_m"] = to_float(morf.get("profundidad_min_m"))
                    sp["prof_max_m"] = to_float(morf.get("profundidad_max_m"))
            # distribucion
            sp["distribucion_raw"] = d.get("distribucion")
            # conservacion
            cons = d.get("estado_conservacion") or d.get("conservacion") or {}
            if isinstance(cons, dict):
                iucn = cons.get("IUCN")
                if isinstance(iucn, dict):
                    sp["IUCN"] = iucn.get("categoria")
                else:
                    sp["IUCN"] = iucn
                sp["libro_rojo"] = cons.get("libro_rojo", {}).get("categoria") \
                    if isinstance(cons.get("libro_rojo"), dict) else cons.get("libro_rojo")
                cites = cons.get("CITES", {})
                sp["CITES"] = cites.get("apendice") or cites.get("categoria") \
                    if isinstance(cites, dict) else cites
            # reproduccion
            rep = d.get("reproduccion") or {}
            if isinstance(rep, dict):
                sp["rep_tipo"] = rep.get("tipo") or rep.get("tipo_descripcion")
            # descripcion textual (esquema A)
            dm = d.get("descripcion_morfologica", {})
            if isinstance(dm, dict):
                sp["json_descripcion"] = dm.get("descripcion_general")
                sp["json_coloracion"] = dm.get("coloracion")
                sp["json_distintivas"] = dm.get("caracteristicas_distintivas")
            # esquema B estructurado
            db = d.get("descripcion", {})
            if isinstance(db, dict):
                sp.setdefault("json_desc_estruct", {}).update(db)
            col = d.get("coloracion", {})
            if isinstance(col, dict) and "patron" in col:
                sp["json_coloracion"] = sp.get("json_coloracion") or col.get("patron")
            continue

        # Esquema C: archivos familiares / grupos
        md = d.get("metadata_familia") or d.get("metadata_seccion", {})
        fam_nombre = md.get("familia")
        orden = md.get("orden")
        for key in ("resumen_especies", "especies"):
            if isinstance(d.get(key), list):
                for s in d[key]:
                    eid = norm_id(s.get("especie_id"))
                    if not eid:
                        continue
                    sp = species.setdefault(eid, {"especie_id": eid})
                    sp["nombre_cientifico"] = s.get("nombre_cientifico")
                    nc = s.get("nombre_comun") or s.get("nombre_comun_espanol")
                    sp["nombre_comun_es"] = nc
                    sp["familia"] = s.get("familia") or fam_nombre
                    sp["orden"] = s.get("orden") or orden
                    # talla
                    if "talla_max_cm" in s:
                        sp["talla_max_cm"] = to_float(s["talla_max_cm"])
                    elif "talla_max_m" in s:
                        sp["talla_max_cm"] = to_float(s["talla_max_m"]) * 100 \
                            if s.get("talla_max_m") else None
                    elif "talla_max" in s:
                        sp["talla_max_cm"] = parse_talla_cm(s["talla_max"])
                    # profundidad
                    if "profundidad" in s:
                        sp["prof_min_m"], sp["prof_max_m"] = parse_profundidad(
                            s["profundidad"])
                    sp["distribucion_raw"] = s.get("distribucion")
                    sp["IUCN"] = s.get("IUCN")
                    sp["json_caracteristica"] = s.get("caracteristica")
                    # pristidae: bloque sierra
                    if isinstance(s.get("sierra"), dict):
                        sp["sierra_dientes"] = s["sierra"].get("dientes_por_lado")
                    # pristidae: conservacion
                    cons = s.get("conservacion")
                    if isinstance(cons, dict):
                        sp["IUCN"] = sp.get("IUCN") or cons.get("IUCN")
                        sp["CITES"] = cons.get("CITES")
                        sp["libro_rojo"] = cons.get("libro_rojo")
                    sp["_fuente_json"] = os.path.basename(f)
        # familias anidadas (quimeras, rayas restantes)
        for k, v in d.items():
            if isinstance(v, dict) and isinstance(v.get("especies"), list):
                sub_fam = v.get("familia") or k.replace("familia_", "")
                sub_orden = v.get("orden")
                for s in v["especies"]:
                    eid = norm_id(s.get("especie_id"))
                    if not eid:
                        continue
                    sp = species.setdefault(eid, {"especie_id": eid})
                    sp["nombre_cientifico"] = s.get("nombre_cientifico")
                    sp["nombre_comun_es"] = s.get("nombre_comun_espanol") \
                        or s.get("nombre_comun")
                    sp["nombre_comun_en"] = s.get("nombre_comun_ingles") \
                        or s.get("nombre_comun_en")
                    sp["familia"] = s.get("familia") or sub_fam
                    sp["orden"] = s.get("orden") or sub_orden
                    if "talla_maxima_cm" in s:
                        sp["talla_max_cm"] = to_float(s["talla_maxima_cm"])
                    elif "talla_maxima_m" in s:
                        sp["talla_max_cm"] = to_float(s["talla_maxima_m"]) * 100
                    morf = s.get("morfometria", {})
                    if isinstance(morf, dict):
                        if "profundidad_min_m" in morf:
                            sp["prof_min_m"] = to_float(morf["profundidad_min_m"])
                            sp["prof_max_m"] = to_float(morf["profundidad_max_m"])
                    sp["distribucion_raw"] = s.get("distribucion")
                    cons = s.get("conservacion", {})
                    if isinstance(cons, dict):
                        sp["IUCN"] = cons.get("IUCN")
                        sp["CITES"] = cons.get("CITES")
                        sp["libro_rojo"] = cons.get("libro_rojo")
                    rep = s.get("reproduccion", {})
                    if isinstance(rep, dict):
                        sp["rep_tipo"] = rep.get("tipo_descripcion") or rep.get("tipo")
                    # descripcion estructurada (quimeras)
                    db = s.get("descripcion", {})
                    if isinstance(db, dict):
                        sp["json_desc_estruct"] = db
                    sp["json_caracteristica"] = s.get("caracteristica") \
                        or v.get("caracteristica_distintiva")
                    sp["_fuente_json"] = os.path.basename(f)
    return species


# ---------------------------------------------------------------------------
# Rasgos desde texto (heuristica) para enriquecer rasgos especificos
# ---------------------------------------------------------------------------
def detectar_rasgos_texto(texto):
    """Detecta rasgos morfologicos en texto libre (descripcion del PDF/JSON)."""
    rasgos = {}
    if not texto:
        return rasgos
    # normalizar saltos de linea y espacios multiples para que las frases
    # partidas por \n en el PDF se reconstruyan
    t = re.sub(r"\s+", " ", texto).lower()
    # --- Cresta interdorsal ---
    if "cresta interdorsal" in t:
        # contexto alrededor de la mencion (±80 chars)
        idx = t.find("cresta interdorsal")
        ctx = t[max(0, idx-80):idx+30]
        if "no presenta cresta" in ctx or "sin cresta interdorsal" in ctx \
                or "carece de cresta" in ctx or "ausencia de cresta" in ctx:
            rasgos["cresta_interdorsal"] = False
        elif "presenta cresta" in ctx or "con cresta interdorsal" in ctx \
                or "posee cresta" in ctx or "tiene cresta" in ctx:
            rasgos["cresta_interdorsal"] = True
        else:
            # mencion sin negacion -> asume presente
            if not re.search(r"\b(no|sin|carece|ausen)\w*\s+(de\s+)?cresta",
                             ctx):
                rasgos["cresta_interdorsal"] = True
    # --- Espiraculos ---
    if "espirác" in t or "espirac" in t:
        idx = min(t.find("espirác"), t.find("espirac"))
        ctx = t[max(0, idx-60):idx+60]
        if re.search(r"\b(sin|no presenta|ausente|carece)\w*.*espir", ctx) \
                or "espiráculos ausentes" in t:
            rasgos["espiraculos"] = False
        elif re.search(r"\b(con|presenta|posee|pequeña|pequeño|diminut)\w*.*espir",
                       ctx) or "espiráculos en hendidura" in t:
            rasgos["espiraculos"] = True
    # --- Hocico forma (rayas y tiburones sierra) ---
    if "hocico en forma de sierra" in t or "hocico alargado y aplanado, en forma" in t:
        rasgos["hocico_sierra"] = True
    # --- Membrana nictitante (refuerzo) ---
    if "membranas nictitantes" in t or "membrana nictitante" in t \
            or "párpados nictitantes" in t or "parpados nictitantes" in t:
        if "sin" in t[:t.find("nictitante")] and re.search(
                r"sin\s+(membranas?|parpados|párpados)\s+nictit", t):
            rasgos["membrana_nictitante"] = False
        else:
            rasgos["membrana_nictitante"] = True
    return rasgos


# ---------------------------------------------------------------------------
# Construir species.json
# ---------------------------------------------------------------------------
def build():
    species = harvest_json_species()
    pdf_desc = json.load(open(PDF_DESC, encoding="utf-8"))
    print(f"JSON: {len(species)} especies | PDF: {len(pdf_desc)} descripciones")

    out = {}
    sin_familia = []
    for eid, sp in species.items():
        familia = sp.get("familia")
        orden = sp.get("orden")
        # normalizar capitalizacion de familia para matching consistente
        familia = _cap_familia(familia)
        # matching case-insensitive de familia
        taxon = TAXON.get(familia)
        if not taxon:
            sin_familia.append((eid, sp.get("nombre_cientifico"), familia))
            continue

        # rasgos base desde taxonomia
        rasgos = {k: v for k, v in taxon.items()
                  if k not in ("grupo",)}
        fuente_rasgos = {k: "taxonomia" for k in rasgos}

        # morfometria
        talla_cm = sp.get("talla_max_cm")
        prof_min = sp.get("prof_min_m")
        prof_max = sp.get("prof_max_m")

        # distribucion
        dist = parse_distribucion(sp.get("distribucion_raw"))

        # conservacion
        iucn = sp.get("IUCN")
        cites = sp.get("CITES")
        libro_rojo = sp.get("libro_rojo")
        protegida = (str(cites) in ("Apéndice I", "Apendice I", "1")
                     or str(libro_rojo) in ("CR", "EN"))
        # los pristidos siempre protegidos
        if familia == "Pristidae":
            protegida = True

        # texto descripcion: PDF si existe, si no JSON
        pdf = pdf_desc.get(eid)
        desc_texto = ""
        col_texto = ""
        rep_texto = ""
        if pdf:
            desc_texto = pdf.get("descripcion", "")
            col_texto = pdf.get("coloracion", "")
            rep_texto = pdf.get("reproductivos", "")
        if not desc_texto:
            desc_texto = sp.get("json_descripcion", "") or ""
        if not col_texto:
            col_texto = sp.get("json_coloracion", "") or ""
        # rasgos desde texto
        rt = detectar_rasgos_texto(desc_texto + " " + col_texto)
        for k, v in rt.items():
            if v is not None:
                rasgos[k] = v
                fuente_rasgos[k] = "pdf"

        # caracteristica distintiva del JSON (frase corta)
        caract = sp.get("json_caracteristica") or ""
        distintivas = sp.get("json_distintivas")
        if distintivas and isinstance(distintivas, list):
            caract = caract or "; ".join(distintivas)

        # pristidae: dientes de sierra
        if familia == "Pristidae" and sp.get("sierra_dientes"):
            rasgos["sierra_dientes"] = sp["sierra_dientes"]
            fuente_rasgos["sierra_dientes"] = "json"

        rec = {
            "especie_id": eid,
            "nombre_cientifico": sp.get("nombre_cientifico"),
            "nombre_comun_es": sp.get("nombre_comun_es"),
            "nombre_comun_en": sp.get("nombre_comun_en"),
            "orden": orden or taxon.get("orden"),
            "familia": familia,
            "grupo": taxon.get("grupo"),
            "rasgos": rasgos,
            "fuente_rasgos": fuente_rasgos,
            "morfometria": {
                "talla_max_cm": talla_cm,
                "profundidad_min_m": prof_min,
                "profundidad_max_m": prof_max,
            },
            "distribucion": dist,
            "conservacion": {
                "IUCN": iucn,
                "libro_rojo": libro_rojo,
                "CITES": cites,
                "protegida": protegida,
            },
            "reproduccion": {
                "tipo": sp.get("rep_tipo"),
                "texto": rep_texto,
            },
            "descripcion": desc_texto,
            "coloracion": col_texto,
            "caracteristica": caract,
        }
        out[eid] = rec

    # reporte
    print(f"\nEspecies normalizadas: {len(out)}")
    if sin_familia:
        print(f"\nSIN familia conocida (descartadas): {len(sin_familia)}")
        for e, n, f in sin_familia:
            print(f"   id={e} {n} familia={f!r}")

    # cobertura de rasgos
    print("\nCobertura de rasgos clave:")
    for r in ["cuerpo_forma", "num_dorsales", "aleta_anal",
              "cresta_interdorsal", "espiraculos", "disco_forma",
              "cola_tipo", "espina_caudal_venenosa", "organo_electrico",
              "sierra"]:
        n = sum(1 for v in out.values() if r in v["rasgos"]
                and v["rasgos"][r] is not None)
        print(f"   {r:28s} {n}/{len(out)}")

    json.dump(out, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\nGuardado: {OUT}")

    # muestra
    print("\n--- MUESTRA: Carcharhinus falciformis ---")
    if "43" in out:
        s = out["43"]
        print("rasgos:", json.dumps(s["rasgos"], ensure_ascii=False))
        print("IUCN:", s["conservacion"]["IUCN"], "| CITES:", s["conservacion"]["CITES"])
        print("desc:", s["descripcion"][:150])

if __name__ == "__main__":
    build()
