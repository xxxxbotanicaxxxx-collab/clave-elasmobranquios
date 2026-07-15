# -*- coding: utf-8 -*-
"""
Fase 3 — Construccion del arbol dicotomico (data/tree.json).

El arbol se define como una lista de nodos. Cada nodo:
  {
    "id": "nXX",
    "pregunta": "texto de la pregunta",
    "ayuda": "texto explicativo opcional del rasgo a mirar",
    "opciones": [
       {"texto": "SI / alternativa A", "siguiente": "nYY" o "result_id"},
       ...
    ]
  }
Las hojas (resultados) son especies individuales {tipo:"especie", especie_id:"NN"}
o grupos candidatos {tipo:"grupo", titulo:"...", especie_ids:[...], eje:"..."}.

Estrategia:
  - Ramas superiores: diseno manual basado en taxonomia (rasgos 100%
    discriminantes).
  - Ramas intra-familia: generadas con reglas desde species.json, usando los
    rasgos disponibles (cresta interdorsal, branquiales, talla, distribucion,
    caracteristica textual). Donde no se puede separar, grupo candidato.
"""
import json
import os

BASE = r"C:\Users\panma\Desktop\Elasms\clave-app"
SPEC = os.path.join(BASE, "data", "species.json")
OUT = os.path.join(BASE, "data", "tree.json")

species = json.load(open(SPEC, encoding="utf-8"))
by_id = species  # {especie_id: rec}

# Agrupar por familia
from collections import defaultdict
by_fam = defaultdict(list)
for v in species.values():
    by_fam[v["familia"]].append(v)

nodes = []
_counter = [0]
def new_id():
    _counter[0] += 1
    return f"n{_counter[0]:03d}"

def add_node(pregunta, opciones, ayuda=""):
    nid = new_id()
    nodes.append({"id": nid, "pregunta": pregunta, "ayuda": ayuda,
                  "opciones": opciones})
    return nid

def leaf_especie(eid):
    sp = by_id[str(eid)]
    return {"tipo": "especie", "especie_id": str(eid),
            "titulo": sp["nombre_cientifico"]}

def leaf_grupo(eids, titulo, eje=""):
    return {"tipo": "grupo", "titulo": titulo,
            "especie_ids": [str(e) for e in eids],
            "eje": eje}


# ===========================================================================
# NIVEL 1: forma del cuerpo (tiburon / raya / quimera)
# ===========================================================================
# Pre-asignar ids de las 3 grandes ramas para enlazar.
id_tiburon = "tiburon"
id_raya = "raya"
id_quimera = "quimera"

# ===========================================================================
# RAMA QUIMERAS (3 spp, 2 familias) — sencilla, manual
# ===========================================================================
def build_quimera():
    # Rhinochimaeridae: hocico largo (1 sp: Neoharriotta carri)
    # Chimaeridae: hocico corto (2 spp: Chimaera cubana, Hydrolagus alberti)
    rhi = by_fam["Rhinochimaeridae"]
    chi = by_fam["Chimaeridae"]
    # separar chimaeridae por profundidad (cubana <900m vs alberti >900m)
    n_hocico = add_node(
        "¿El hocico es LARGO y puntiagudo, proyectado hacia adelante como una aguja fina?",
        ayuda="Las quimeras tienen opérculo cubriendo las branquias y una espina "
              "venenosa en la primera aleta dorsal.",
        opciones=[
            {"texto": "Sí, hocico largo y fino", "siguiente": leaf_especie(rhi[0]["especie_id"])},
            {"texto": "No, hocico corto y redondeado", "siguiente": "QUI_CIMA"},
        ])
    # Chimaeridae: separar por tamaño/profundidad
    cubana = [s for s in chi if "cubana" in s["nombre_cientifico"].lower()][0]
    alberti = [s for s in chi if "alberti" in s["nombre_cientifico"].lower()][0]
    n_cima = add_node(
        "¿El animal es grande (hasta 1 m) y proviene de aguas MUY profundas "
        "(más de 900 m)?",
        ayuda=f"Chimaera cubana: hasta 80 cm, 180-900 m de profundidad.\n"
              f"Hydrolagus alberti: hasta 1 m, 348-1470 m (la más profunda).",
        opciones=[
            {"texto": "Sí, grande y muy profundo", "siguiente": leaf_especie(alberti["especie_id"])},
            {"texto": "No, menor y menos profundo", "siguiente": leaf_especie(cubana["especie_id"])},
        ])
    return n_hocico, {"QUI_CIMA": n_cima}

# ===========================================================================
# RAMA TIBURONES — niveles superiores por rasgos taxonomicos
# ===========================================================================
def build_tiburon():
    """Construye la rama tiburones. Devuelve (id_nodo_entrada, saltos)."""
    saltos = {}

    # --- N branquiales: Hexanchiformes tiene 6-7; el resto 5 ---
    hexan = by_fam["Hexanchidae"]
    n_branq = add_node(
        "¿Cuántas hendiduras branquiales (aberturas de agallas) tiene a cada "
        "lado de la cabeza?",
        ayuda="Cuente las aberturas detrás de la cabeza. La mayoría de "
              "tiburones tiene 5. Los Hexanchiformes tienen 6 o 7, muy visibles.",
        opciones=[
            {"texto": "6 o 7 hendiduras", "siguiente": "TIB_HEXAN"},
            {"texto": "5 hendiduras", "siguiente": "TIB_5BRANQ"},
        ])

    # --- Hexanchidae: 6 (Hexanchus) vs 7 (Heptranchias, Notorynchus) ---
    h6 = [s for s in hexan if s["rasgos"].get("branquiales") == 6]
    h7 = [s for s in hexan if "Siete" in (s["caracteristica"] or "")
          or "siete" in (s["caracteristica"] or "").lower()
          or "sept" in (s["caracteristica"] or "").lower()]
    # En realidad por descripcion: Heptranchias=7, Notorynchus=7, Hexanchus=6
    h7_ids = {s["especie_id"] for s in hexan
              if s["nombre_cientifico"].split()[0] in ("Heptranchias", "Notorynchus")}
    n_hexan = add_node(
        "¿Tiene SEIS o SIETE hendiduras branquiales?",
        ayuda="Hexanchus: 6 hendiduras. Heptranchias y Notorynchus: 7 hendiduras.",
        opciones=[
            {"texto": "Seis hendiduras", "siguiente": "HEX_6"},
            {"texto": "Siete hendiduras", "siguiente": "HEX_7"},
        ])
    saltos["TIB_HEXAN"] = n_hexan

    # Hexanchus (6): 2 spp -> por talla (griseus 6m vs nakamurai 1.8m)
    hex6 = [s for s in hexan if s["especie_id"] not in h7_ids]
    n_hex6 = add_node(
        "¿Es un tiburón MUY grande (hasta 6 m)?",
        ayuda=f"Hexanchus griseus: hasta 6 m, la cañabota gigante.\n"
              f"Hexanchus nakamurai: hasta 1.8 m, cañabota ojigrande.",
        opciones=[
            {"texto": "Sí, muy grande (~6 m)", "siguiente": leaf_especie(
                [s for s in hex6 if "griseus" in s["nombre_cientifico"].lower()][0]["especie_id"])},
            {"texto": "No, menor (~1.8 m)", "siguiente": leaf_especie(
                [s for s in hex6 if "nakamurai" in s["nombre_cientifico"].lower()][0]["especie_id"])},
        ])
    saltos["HEX_6"] = n_hex6

    # 7 hendiduras: Heptranchias (1.4m) vs Notorynchus (3m)
    hex7 = [s for s in hexan if s["especie_id"] in h7_ids]
    n_hex7 = add_node(
        "¿Es un tiburón grande (alrededor de 3 m) con cabeza ancha?",
        ayuda=f"Heptranchias perlo: ~1.4 m, hocico puntiagudo.\n"
              f"Notorynchus cepedianus: ~3 m, cabeza ancha.",
        opciones=[
            {"texto": "Sí, ~3 m y cabeza ancha", "siguiente": leaf_especie(
                [s for s in hex7 if "Notorynchus" in s["nombre_cientifico"]][0]["especie_id"])},
            {"texto": "No, ~1.4 m y puntiagudo", "siguiente": leaf_especie(
                [s for s in hex7 if "Heptranchias" in s["nombre_cientifico"]][0]["especie_id"])},
        ])
    saltos["HEX_7"] = n_hex7

    # --- 5 branquias: separar por aleta anal y espinas dorsales ---
    n_5br = add_node(
        "¿Tiene aleta anal (aleta pequeña en el vientre, entre las aletas "
        "pélvicas y la cola)?",
        ayuda="Mire la parte inferior, entre las pélvicas y la cola. Algunos "
              "tiburones carecen de aleta anal.",
        opciones=[
            {"texto": "Sí, tiene aleta anal", "siguiente": "TIB_CON_ANAL"},
            {"texto": "No, sin aleta anal", "siguiente": "TIB_SIN_ANAL"},
        ])
    saltos["TIB_5BRANQ"] = n_5br

    # --- SIN anal: Squaliformes (Centrophorus, Etmopterus, Squalus, Centroscyllium)
    #     y Squatinidae (angel) ---
    sin_anal_fams = ["Centrophoridae", "Etmopteridae", "Squalidae",
                     "Centroscylliidae", "Squatinidae"]
    sin_anal = [s for f in sin_anal_fams for s in by_fam.get(f, [])]
    n_sinal = add_node(
        "¿El cuerpo es MUY APLANADO (como una raya) con aletas pectorales "
        "muy grandes y separadas de la cabeza?",
        ayuda="Los tiburones ángel (Squatinidae) tienen el cuerpo aplanado y "
              "parecen rayas, pero son tiburones. Los Squaliformes tienen "
              "cuerpo típico de tiburón.",
        opciones=[
            {"texto": "Sí, cuerpo aplanado tipo raya", "siguiente": "SQUAT"},
            {"texto": "No, cuerpo de tiburón normal", "siguiente": "SQUAL"},
        ])
    saltos["TIB_SIN_ANAL"] = n_sinal

    # Squatinidae: 2 spp por talla (californica 150 vs dumeril)
    squat = by_fam["Squatinidae"]
    n_squat = add_node(
        "¿Qué especie de tiburón ángel es? (Compare por región y detalles)",
        ayuda="Ambas son tiburones ángel (cuerpo aplanado).",
        opciones=[{"texto": f"{s['nombre_cientifico']}",
                   "siguiente": leaf_especie(s["especie_id"])} for s in squat])
    saltos["SQUAT"] = n_squat

    # Squaliformes: separar Etmopteridae (enanos) del resto por talla
    squalish = [s for f in ["Centrophoridae", "Etmopteridae", "Squalidae",
                            "Centroscylliidae"] for s in by_fam.get(f, [])]
    etmo = by_fam["Etmopteridae"]
    grandes = [s for s in squalish if s["especie_id"] not in {e["especie_id"] for e in etmo}]
    n_squal = add_node(
        "¿Es un tiburón ENANO (menos de 50 cm) con ambas dorsales provistas "
        "de espina?",
        ayuda="Los Etmopteridae (tiburones linterna) son enanos (<50 cm), "
              "oscuros, a veces bioluminiscentes. El resto (Centrophorus, "
              "Squalus, Centroscyllium) son más grandes.",
        opciones=[
            {"texto": "Sí, enano con espinas dorsales", "siguiente": "ETMOP"},
            {"texto": "No, más grande o sin esa combinación", "siguiente": "SQUAL_GR"},
        ])
    saltos["SQUAL"] = n_squal

    # Etmopteridae: grupo candidato (7 spp, se separan por coloración/talla/dist)
    n_etmop = add_node(
        "¿Qué tiburón linterna (Etmopteridae) es? Compare por coloración y talla.",
        ayuda="Tiburones enanos oscuros del Caribe/Pacífico profundo. Use la "
              "ficha comparativa.",
        opciones=[{"texto": f"{s['nombre_cientifico']} ({s['morfometria']['talla_max_cm'] or '?'} cm)",
                   "siguiente": leaf_especie(s["especie_id"])} for s in etmo])
    saltos["ETMOP"] = n_etmop

    # Squaliformes grandes: Centrophorus(1), Squalus(1), Centroscyllium(1) -> grupo
    n_squalgr = add_node(
        "¿Cuál de estos tiburones esqualiformes es? (3 especies)",
        ayuda="Centrophorus granulosus (160 cm), Squalus cubensis (110 cm), "
              "Centroscyllium nigrum (50 cm, Pacífico).",
        opciones=[{"texto": f"{s['nombre_cientifico']}",
                   "siguiente": leaf_especie(s["especie_id"])} for s in grandes])
    saltos["SQUAL_GR"] = n_squalgr

    # --- CON anal: separar por nictitante, barbillones, hocico, tamanos ---
    con_anal_fams = ["Carcharhinidae", "Scyliorhinidae", "Triakidae",
                     "Alopiidae", "Lamnidae", "Mitsukurinidae", "Odontaspididae",
                     "Heterodontidae", "Ginglymostomatidae", "Rhincodontidae"]
    n_conanal = add_node(
        "¿Tiene una membrana nictitante (un párpado interno) en el ojo, o "
        "barbillones (carnosidades) colgando junto a la boca?",
        ayuda="La membrana nictitante es un párpado vertical en la esquina del "
              "ojo. Los barbillones son filamentos carnosos cerca de las "
              "fosas nasales.",
        opciones=[
            {"texto": "Sí, tiene membrana nictitante", "siguiente": "CARC_SCYL"},
            {"texto": "Tiene barbillones (sin nictitante)", "siguiente": "ORECT"},
            {"texto": "No, ni nictitante ni barbillones", "siguiente": "LAMN_HET"},
        ])
    saltos["TIB_CON_ANAL"] = n_conanal

    # Nictitante: Carcharhinidae + Scyliorhinidae
    carc = by_fam["Carcharhinidae"]
    scyl = by_fam["Scyliorhinidae"]
    n_cs = add_node(
        "¿Es un tiburón pequeño (menos de 60 cm), delgado, a menudo con "
        "patrón de manchas?",
        ayuda="Los Scyliorhinidae (tiburones gato) son pequeños (<60 cm) y "
              "delgados. Los Carcharhinidae (réquiem) son típicamente más "
              "grandes y robustos.",
        opciones=[
            {"texto": "Sí, pequeño y manchado", "siguiente": "SCYL"},
            {"texto": "No, tiburón mediano o grande", "siguiente": "CARC"},
        ])
    saltos["CARC_SCYL"] = n_cs

    # Scyliorhinidae: grupo candidato (8 spp)
    n_scyl = add_node(
        "¿Qué tiburón gato (Scyliorhinidae) es? Compare por patrón, hocico y talla.",
        ayuda="Tiburones pequeños del Caribe/Pacífico. Ficha comparativa.",
        opciones=[{"texto": f"{s['nombre_cientifico']} ({s['morfometria']['talla_max_cm'] or '?'} cm)",
                   "siguiente": leaf_especie(s["especie_id"])} for s in scyl])
    saltos["SCYL"] = n_scyl

    # Carcharhinidae: separar por cresta interdorsal + color de puntas
    n_carc, carc_salt = build_carcharhinidae(carc)
    saltos["CARC"] = n_carc
    saltos.update(carc_salt)

    # Orectolobiformes (barbillones): Ginglymostoma + Rhincodon
    orecc = by_fam["Ginglymostomatidae"] + by_fam["Rhincodontidae"]
    n_orect = add_node(
        "¿Es el tiburón ballena (enorme, hasta 15 m, con puntos blancos)?",
        ayuda=f"Rhincodon typus: el pez más grande del mundo, hasta 15 m, con "
              f"patrón de puntos. Ginglymostoma cirratum: tiburón nodriza, "
              f"hasta 4.3 m.",
        opciones=[
            {"texto": "Sí, tiburón ballena gigante", "siguiente": leaf_especie(
                [s for s in orecc if "Rhincodon" in s["nombre_cientifico"]][0]["especie_id"])},
            {"texto": "No, tiburón nodriza (~4 m)", "siguiente": leaf_especie(
                [s for s in orecc if "Ginglymostoma" in s["nombre_cientifico"]][0]["especie_id"])},
        ])
    saltos["ORECT"] = n_orect

    # Sin nictitante ni barbillones: Lamnidae, Mitsukurinidae, Odontaspididae,
    # Alopiidae (cola larga), Heterodontidae (cuernos)
    lamn = by_fam["Lamnidae"] + by_fam["Mitsukurinidae"] + by_fam["Odontaspididae"] + by_fam["Alopiidae"]
    het = by_fam["Heterodontidae"]
    n_lamn_het = add_node(
        "¿Tiene la cola (lóbulo superior de la aleta caudal) EXTREMADAMENTE "
        "larga, casi tan larga como el cuerpo?",
        ayuda="Los Alopiidae (tiburones zorro) tienen una cola desproporcionada. "
              "Los Heterodontidae (tiburones toro/bullhead) tienen crestas "
              "óseas sobre los ojos y espinas dorsales.",
        opciones=[
            {"texto": "Sí, cola extremadamente larga", "siguiente": "ALOP"},
            {"texto": "Tiene crestas óseas sobre los ojos y espinas dorsales",
             "siguiente": "HETERO"},
            {"texto": "No, cola y cabeza normales", "siguiente": "LAMN"},
        ])
    saltos["LAMN_HET"] = n_lamn_het

    # Alopiidae: 2 spp por color/talla
    alop = by_fam["Alopiidae"]
    n_alop = add_node(
        "¿Qué tiburón zorro (Alopiidae) es?",
        ayuda="Cola extremadamente larga. Compare talla y color.",
        opciones=[{"texto": f"{s['nombre_cientifico']} ({s['morfometria']['talla_max_cm'] or '?'} cm)",
                   "siguiente": leaf_especie(s["especie_id"])} for s in alop])
    saltos["ALOP"] = n_alop

    # Heterodontidae: 3 spp
    n_hetero = add_node(
        "¿Qué tiburón toro (Heterodontidae) es? Compare por región.",
        ayuda="Crestas sobre los ojos, espinas dorsales.",
        opciones=[{"texto": f"{s['nombre_cientifico']}",
                   "siguiente": leaf_especie(s["especie_id"])} for s in het])
    saltos["HETERO"] = n_hetero

    # Lamniformes restantes: Isurus (lamnidae), Mitsukurina (duende),
    # Odontaspis -> grupo
    n_lamn = add_node(
        "¿Cuál de estos tiburones lamniformes es? (3 especies)",
        ayuda="Isurus oxyrinchus (marrajo, 4 m, cuerpo torpedos), "
              "Mitsukurina owstoni (duende, hocico larguísimo), "
              "Odontaspis ferox (4.1 m, dientes sobresalientes).",
        opciones=[{"texto": f"{s['nombre_cientifico']}",
                   "siguiente": leaf_especie(s["especie_id"])} for s in lamn])
    saltos["LAMN"] = n_lamn

    return n_branq, saltos


def build_carcharhinidae(carc):
    """Carcharhinidae (18 spp): separar por cresta interdorsal y rasgos visibles."""
    saltos = {}
    # Primero: Galeocerdo (tigre, único género claramente distinto, 7.5m) y
    # Prionace (azul, color único)
    # Mejor enfoque: preguntas por rasgos visibles en campo.
    n = add_node(
        "¿El tiburón tiene BANDAS VERTICALES oscuras en el cuerpo (especialmente "
        "visible en juveniles)?",
        ayuda="Galeocerdo cuvier (tiburón tigre): bandas verticales, hasta 7.5 m.",
        opciones=[
            {"texto": "Sí, bandas verticales", "siguiente": leaf_especie(
                [s for s in carc if "Galeocerdo" in s["nombre_cientifico"]][0]["especie_id"])},
            {"texto": "No, sin bandas verticales", "siguiente": "CARC_COL"},
        ])
    saltos["CARC"] = n
    # Color del cuerpo / puntas de aletas
    rest = [s for s in carc if "Galeocerdo" not in s["nombre_cientifico"]]
    azul = [s for s in rest if "Prionace" in s["nombre_cientifico"]]
    n2 = add_node(
        "¿El cuerpo es de color AZUL OSCURO intenso, esbelto, con aletas "
        "pectorales muy largas?",
        ayuda="Prionace glauca (tiburón azul): azul intenso inconfundible, "
              "hasta 4.8 m.",
        opciones=[
            {"texto": "Sí, azul oscuro intenso", "siguiente": leaf_especie(azul[0]["especie_id"])},
            {"texto": "No, gris/marrón típico", "siguiente": "CARC_PUNTAS"},
        ])
    saltos["CARC_COL"] = n2
    # Puntas de aletas
    rest2 = [s for s in rest if "Prionace" not in s["nombre_cientifico"]]
    n3 = add_node(
        "¿Las puntas de las aletas (dorsal, pectorales) tienen un color "
        "claramente distinto al cuerpo?",
        ayuda="Mire los extremos de la primera dorsal y las pectorales.",
        opciones=[
            {"texto": "Puntas BLANCAS marcadas", "siguiente": "CARC_BLANCO"},
            {"texto": "Puntas NEGRAS marcadas", "siguiente": "CARC_NEGRO"},
            {"texto": "Puntas del mismo color", "siguiente": "CARC_GRIS"},
        ])
    saltos["CARC_PUNTAS"] = n3
    # Puntas blancas: albimarginatus (Pac) vs longimanus (ambos)
    pb = [s for s in rest2 if "albimarginatus" in s["nombre_cientifico"].lower()
          or "longimanus" in s["nombre_cientifico"].lower()]
    n4 = add_node(
        "¿Las pectorales son MUY largas (más largas que la cabeza) con forma "
        "de pala y puntas blancas redondeadas?",
        ayuda="Carcharhinus longimanus (oceánico): pectorales en pala, "
              "peligroso en alta mar. C. albimarginatus: puntas blancas "
              "pero pectorales normales, solo Pacífico.",
        opciones=[
            {"texto": "Sí, pectorales en pala, muy largas", "siguiente": leaf_especie(
                [s for s in pb if "longimanus" in s["nombre_cientifico"].lower()][0]["especie_id"])},
            {"texto": "No, pectorales normales", "siguiente": leaf_especie(
                [s for s in pb if "albimarginatus" in s["nombre_cientifico"].lower()][0]["especie_id"])},
        ])
    saltos["CARC_BLANCO"] = n4
    # Puntas negras: limbatus vs acronotus (mancha hocico)
    pn = [s for s in rest2 if "limbatus" in s["nombre_cientifico"].lower()
          or "acronotus" in s["nombre_cientifico"].lower()]
    n5 = add_node(
        "¿Tiene una mancha negra en la PUNTA DEL HOCICO?",
        ayuda="C. acronotus: mancha negra en el hocico (blacknose), ~2.2 m. "
              "C. limbatus: puntas negras en varias aletas pero hocico limpio.",
        opciones=[
            {"texto": "Sí, mancha negra en el hocico", "siguiente": leaf_especie(
                [s for s in pn if "acronotus" in s["nombre_cientifico"].lower()][0]["especie_id"])},
            {"texto": "No, hocico sin mancha", "siguiente": leaf_especie(
                [s for s in pn if "limbatus" in s["nombre_cientifico"].lower()][0]["especie_id"])},
        ])
    saltos["CARC_NEGRO"] = n5
    # Resto gris (sin puntas marcadas): grupo candidato
    gris = [s for s in rest2 if "albimarginatus" not in s["nombre_cientifico"].lower()
            and "longimanus" not in s["nombre_cientifico"].lower()
            and "limbatus" not in s["nombre_cientifico"].lower()
            and "acronotus" not in s["nombre_cientifico"].lower()]
    n6 = add_node(
        "¿Cuál de estos carcharhínidos es? Compare por hocico, talla y región.",
        ayuda="Carcharhínidos sin puntas de aleta marcadas: use la ficha "
              "comparativa (hocico, talla, distribución).",
        opciones=[{"texto": f"{s['nombre_cientifico']} ({s['morfometria']['talla_max_cm'] or '?'} cm)",
                   "siguiente": leaf_especie(s["especie_id"])} for s in gris])
    saltos["CARC_GRIS"] = n6
    return n, saltos


# ===========================================================================
# RAMA RAYAS — niveles superiores
# ===========================================================================
def build_raya():
    saltos = {}
    # Sierra (Pristidae) vs el resto
    n = add_node(
        "¿El hocico es una SIERRA larga y aplanada con dientes a los lados?",
        ayuda="Los peces sierra (Pristidae) tienen un hocico en sierra "
              "inconfundible. ¡Ambas especies están EN PELIGRO CRÍTICO y "
              "están PROTEGIDAS!",
        opciones=[
            {"texto": "Sí, hocico en sierra", "siguiente": "RAYA_SIERRA"},
            {"texto": "No, hocico normal", "siguiente": "RAYA_NOSIERRA"},
        ])
    saltos["RAYA"] = n

    # Pristidae: 2 spp por nº dientes de la sierra
    prist = by_fam["Pristidae"]
    pect = [s for s in prist if "pectinata" in s["nombre_cientifico"].lower()][0]
    perot = [s for s in prist if "perotteti" in s["nombre_cientifico"].lower()
             or "zephyreus" in s["nombre_cientifico"].lower()][0]
    n2 = add_node(
        "¿Los dientes de la sierra son PEQUEÑOS y MUY JUNTOS (23-34 por lado)?",
        ayuda=f"Pristis pectinata: 23-34 dientes pequeños y cercanos.\n"
              f"Pristis perotteti/zephyreus: 17-22 dientes más grandes y "
              f"separados. ¡PROTEGIDAS - liberar si captura!",
        opciones=[
            {"texto": "Sí, dientes pequeños y juntos", "siguiente": leaf_especie(pect["especie_id"])},
            {"texto": "No, dientes grandes y separados", "siguiente": leaf_especie(perot["especie_id"])},
        ])
    saltos["RAYA_SIERRA"] = n2

    # Sin sierra: órgano eléctrico?
    n3 = add_node(
        "¿Es una raya REDONDA y robusta capaz de dar DESCARGAS ELÉCTRICAS "
        "(temblor al tocarla)?",
        ayuda="Las rayas eléctricas (Narcinidae, Torpedinidae) tienen disco "
              "circular y órganos eléctricos. ¡Cuidado, pueden dar calambres!",
        opciones=[
            {"texto": "Sí, raya eléctrica", "siguiente": "RAYA_ELEC"},
            {"texto": "No, no eléctrica", "siguiente": "RAYA_NOELEC"},
        ])
    saltos["RAYA_NOSIERRA"] = n3

    # Eléctricas: Narcinidae (pequeñas) vs Torpedinidae (más grandes)
    narc = by_fam["Narcinidae"]
    torp = by_fam["Torpedinidae"]
    n4 = add_node(
        "¿Es una raya eléctrica GRANDE (más de 50 cm, disco casi circular "
        "y grueso)?",
        ayuda="Torpedinidae (torpedos): grandes, disco grueso circular, hasta "
              "1.8 m. Narcinidae: pequeñas, <77 cm.",
        opciones=[
            {"texto": "Sí, grande y gruesa", "siguiente": "TORPEDO"},
            {"texto": "No, pequeña (<77 cm)", "siguiente": "NARCINE"},
        ])
    saltos["RAYA_ELEC"] = n4
    n_torp = add_node(
        "¿Qué torpedo (Torpedinidae) es? Compare por región.",
        ayuda="Rayas eléctricas grandes.",
        opciones=[{"texto": f"{s['nombre_cientifico']}",
                   "siguiente": leaf_especie(s["especie_id"])} for s in torp])
    saltos["TORPEDO"] = n_torp
    n_narc = add_node(
        "¿Qué raya eléctrica pequeña (Narcinidae) es? Compare por talla y patrón.",
        ayuda="Pequeñas rayas eléctricas. Diplobatis <25 cm, Narcine >27 cm.",
        opciones=[{"texto": f"{s['nombre_cientifico']} ({s['morfometria']['talla_max_cm'] or '?'} cm)",
                   "siguiente": leaf_especie(s["especie_id"])} for s in narc])
    saltos["NARCINE"] = n_narc

    # No eléctricas, sin sierra: separar por forma del disco / cola
    n5 = add_node(
        "¿El cuerpo tiene forma de ALAS puntiagudas tipo águila o manta "
        "(disco muy ancho, aletas pectorales como alas)?",
        ayuda="Myliobatidae (águilas marinas, mantas, mobulas): alas "
              "puntiagudas. Gymnuridae (mariposa): disco más ancho que largo "
              "pero cola cortísima.",
        opciones=[
            {"texto": "Sí, alas tipo águila/manta", "siguiente": "MYLIO"},
            {"texto": "Disco MUY ancho (mariposa) con cola cortísima", "siguiente": leaf_especie(
                by_fam["Gymnuridae"][0]["especie_id"])},
            {"texto": "Disco redondo o romboidal normal", "siguiente": "RAYA_DISCO"},
        ])
    saltos["RAYA_NOELEC"] = n5

    # Myliobatidae: 8 spp, grupo por género
    myl = by_fam["Myliobatidae"]
    n6 = add_node(
        "¿Es una MANTA GIGANTE (más de 5 m de envergadura)?",
        ayuda="Manta birostris: hasta 7 m, la raya más grande del mundo. "
              "Mobula spp: mantas diablo más pequeñas (1-2 m). Aetobatus: "
              "chucho pintado con puntos blancos. Rhinoptera: gavilán con "
              "hocico hendido.",
        opciones=[
            {"texto": "Sí, manta gigante (>5 m)", "siguiente": leaf_especie(
                [s for s in myl if "Manta" in s["nombre_cientifico"]][0]["especie_id"])},
            {"texto": "Con PUNTOS BLANCOS sobre fondo oscuro", "siguiente": leaf_especie(
                [s for s in myl if "Aetobatus" in s["nombre_cientifico"]][0]["especie_id"])},
            {"texto": "Manta mediana lisa o gavilán (hocico hendido)", "siguiente": "MYLIO_REST"},
        ])
    saltos["MYLIO"] = n6
    myl_rest = [s for s in myl if "Manta" not in s["nombre_cientifico"]
                and "Aetobatus" not in s["nombre_cientifico"]]
    n7 = add_node(
        "¿Cuál de estas rayas (Mobula/Rhinoptera) es? Compare por región y hocico.",
        ayuda="Mobula: mantas diablo. Rhinoptera: gavilanes con hocico "
              "cuadrado/hendido. Use la ficha comparativa.",
        opciones=[{"texto": f"{s['nombre_cientifico']}",
                   "siguiente": leaf_especie(s["especie_id"])} for s in myl_rest])
    saltos["MYLIO_REST"] = n7

    # Disco redondo/romboidal: separar por cola (látigo vs delgada con dorsales)
    n8 = add_node(
        "¿La cola es delgada y LARGA tipo LÁTIGO, SIN aletas dorsales, a "
        "menudo con una espina venenosa?",
        ayuda="Rayas látigo (Dasyatidae, Urotrygonidae, Potamotrygonidae): "
              "cola látigo con espina. Rajidae: cola delgada CON dos dorsales "
              "y SIN espina venenosa.",
        opciones=[
            {"texto": "Sí, cola látigo con espina", "siguiente": "RAYA_LATIGO"},
            {"texto": "Cola delgada con dos dorsales y sin espina venenosa",
             "siguiente": "RAJIDAE"},
            {"texto": "Cuerpo de guitarra (hocico largo, cola robusta con dorsales)",
             "siguiente": "RHINOBAT"},
        ])
    saltos["RAYA_DISCO"] = n8

    # Rajidae: 10 spp, grupo candidato
    raj = by_fam["Rajidae"] + by_fam["Anacanthobatidae"]
    n_raj = add_node(
        "¿Qué raya (Rajidae) es? Compare por talla y región.",
        ayuda="Rayas de aguas profundas, disco romboidal, cola delgada sin "
              "espina venenosa. ¡Ovíparas (ponen huevos)!",
        opciones=[{"texto": f"{s['nombre_cientifico']} ({s['morfometria']['talla_max_cm'] or '?'} cm)",
                   "siguiente": leaf_especie(s["especie_id"])} for s in raj])
    saltos["RAJIDAE"] = n_raj

    # Rhinobatidae: 5 spp, grupo
    rhinob = by_fam["Rhinobatidae"]
    n_rhinob = add_node(
        "¿Qué raya guitarra (Rhinobatidae) es? Compare por región.",
        ayuda="Cuerpo de guitarra: hocico largo, cola robusta con dos dorsales.",
        opciones=[{"texto": f"{s['nombre_cientifico']}",
                   "siguiente": leaf_especie(s["especie_id"])} for s in rhinob])
    saltos["RHINOBAT"] = n_rhinob

    # Látigo: agua dulce (Potamotrygonidae) vs marina (Dasyatidae, Urotrygonidae)
    pot = by_fam["Potamotrygonidae"]
    dasy = by_fam["Dasyatidae"]
    urot = by_fam["Urotrygonidae"]
    n9 = add_node(
        "¿La capturó en AGUA DULCE (río, quebrada, estero)?",
        ayuda="Potamotrygonidae: rayas exclusivas de agua dulce (Amazonas, "
              "Orinoco, Magdalena). ¡Espina muy venenosa! Las demás son marinas.",
        opciones=[
            {"texto": "Sí, agua dulce", "siguiente": "POTAMO"},
            {"texto": "No, agua salada (mar)", "siguiente": "LATIGO_MAR"},
        ])
    saltos["RAYA_LATIGO"] = n9
    # Potamotrygonidae: grupo
    n_pot = add_node(
        "¿Qué raya de agua dulce (Potamotrygonidae) es? Compare por patrón y talla.",
        ayuda="Rayas de río con patrones llamativos (ocelos, rosetas, manchas).",
        opciones=[{"texto": f"{s['nombre_cientifico']} ({s['morfometria']['talla_max_cm'] or '?'} cm)",
                   "siguiente": leaf_especie(s["especie_id"])} for s in pot])
    saltos["POTAMO"] = n_pot
    # Dasyatidae + Urotrygonidae: separar por talla (Urotrygon pequeno)
    n10 = add_node(
        "¿Es una raya PEQUEÑA (menos de 50 cm de ancho) con disco casi "
        "circular?",
        ayuda="Urotrygonidae: pequeñas (<76 cm), disco redondo, Pacífico "
              "principalmente. Dasyatidae: más grandes, disco romboidal.",
        opciones=[
            {"texto": "Sí, pequeña y circular", "siguiente": "UROTRYGON"},
            {"texto": "No, más grande y romboidal", "siguiente": "DASYATIS"},
        ])
    saltos["LATIGO_MAR"] = n10
    n_uro = add_node(
        "¿Qué raya redonda (Urotrygonidae) es? Compare por región y talla.",
        ayuda="Rayas látigo pequeñas del Pacífico/Caribe.",
        opciones=[{"texto": f"{s['nombre_cientifico']} ({s['morfometria']['talla_max_cm'] or '?'} cm)",
                   "siguiente": leaf_especie(s["especie_id"])} for s in urot])
    saltos["UROTRYGON"] = n_uro
    n_das = add_node(
        "¿Qué raya látigo (Dasyatidae) es? Compare por región.",
        ayuda="Rayas látigo marinas, cola muy larga con espina venenosa.",
        opciones=[{"texto": f"{s['nombre_cientifico']}",
                   "siguiente": leaf_especie(s["especie_id"])} for s in dasy])
    saltos["DASYATIS"] = n_das

    return n, saltos


# ===========================================================================
# Resolver todos los saltos y ensamblar
# ===========================================================================
def build_all():
    # crear los 3 nodos de entrada (referenciados antes de definirse)
    global nodes
    nodes = []

    # Construir cada rama (devuelve id de entrada + saltos a resolver)
    tib_entry, tib_salt = build_tiburon()
    raya_entry, raya_salt = build_raya()
    qui_entry, qui_salt = build_quimera()

    all_salt = {}
    all_salt.update(tib_salt)
    all_salt.update(raya_salt)
    all_salt.update(qui_salt)

    # Nodo raiz
    root = add_node(
        "¿Qué tipo de animal es?",
        ayuda="Observe la forma general del cuerpo.",
        opciones=[
            {"texto": "TIBURÓN: cuerpo alargado con aletas pectorales separadas de la cabeza",
             "siguiente": tib_entry},
            {"texto": "RAYA: cuerpo aplanado en disco, aletas pectorales unidas a la cabeza",
             "siguiente": raya_entry},
            {"texto": "QUIMERA: cabeza grande, ojos grandes, opérculo cubriendo las branquias",
             "siguiente": qui_entry},
        ])

    # Resolver saltos: cada "siguiente" que es un string clave debe apuntar al
    # id del nodo correspondiente.
    salt_targets = {f"TIB_{k}": v for k, v in tib_salt.items()}
    salt_targets.update(raya_salt)
    salt_targets.update(qui_salt)
    # Los nodos de entrada de rama ya son ids reales. Los saltos internos
    # mapean etiqueta -> id real. Sustituir en todas las opciones.
    for node in nodes:
        for op in node["opciones"]:
            sig = op["siguiente"]
            if isinstance(sig, str) and sig in all_salt:
                op["siguiente"] = all_salt[sig]

    # Marcar raiz
    tree = {"root": root, "nodes": nodes}
    return tree


if __name__ == "__main__":
    tree = build_all()
    # Validacion: todos los 'siguiente' apuntan a un id existente o a una hoja dict
    node_ids = {n["id"] for n in tree["nodes"]}
    errores = []
    especies_alcanzables = set()
    for n in tree["nodes"]:
        for op in n["opciones"]:
            sig = op["siguiente"]
            if isinstance(sig, dict):
                if sig["tipo"] == "especie":
                    especies_alcanzables.add(sig["especie_id"])
            elif isinstance(sig, str):
                if sig not in node_ids:
                    errores.append(f"{n['id']} -> '{sig}' no existe")
            else:
                errores.append(f"{n['id']} -> tipo raro {type(sig)}")
    print(f"Nodos: {len(tree['nodes'])}")
    print(f"Errores de enlace: {len(errores)}")
    for e in errores[:20]:
        print("   ", e)
    # cobertura de especies
    todas = set(species.keys())
    no_alcanzables = todas - especies_alcanzables
    print(f"\nEspecies alcanzables por el arbol: {len(especies_alcanzables)}/{len(todas)}")
    if no_alcanzables:
        print("NO alcanzables:")
        for eid in sorted(no_alcanzables, key=int):
            print(f"   {eid} {species[eid]['nombre_cientifico']} ({species[eid]['familia']})")

    json.dump(tree, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nGuardado: {OUT}")
