"""
SmartFactory — Module 4 : Qualité & Visualisation
==================================================
Groupe 1 ARCMIND ROBOTICS
Rôle     : Détection d'anomalies, overlay statut, rapport qualité de fin de cycle
Projet   : Cellule robotisée de soudage intelligente — CoppeliaSim / Python ZMQ

Usage standalone (depuis la racine du dépôt) :
    python src/detection_anomalies.py

Intégration dans main.py (appel depuis Louis) :
    from detection_anomalies import verifier, analyser_cycle, afficher_statut_coppeliasim
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path


# ══════════════════════════════════════════════════════
#  1. FONCTION PRINCIPALE — CONTRAT D'ÉQUIPE
# ══════════════════════════════════════════════════════

def verifier(pos_reelle: list, pos_theorique: list, seuil: float) -> str:
    """
    Compare la position réelle du robot à la position théorique.

    Paramètres
    ----------
    pos_reelle    : [x, y, z] — position mesurée (fournie par Louis / ZMQ)
    pos_theorique : [x, y, z] — position attendue (issue de la trajectoire d'Angie)
    seuil         : float     — écart max toléré en mètres (ex : 0.010 = 10 mm)

    Retourne
    --------
    "OK"       — position conforme
    "ANOMALIE" — déviation supérieure au seuil
    """
    ecart = _distance_euclidienne(pos_reelle, pos_theorique)
    return "OK" if ecart <= seuil else "ANOMALIE"


# ══════════════════════════════════════════════════════
#  2. VÉRIFICATION ENRICHIE (usage interne + rapport)
# ══════════════════════════════════════════════════════

def verifier_detail(pos_reelle: list, pos_theorique: list, seuil: float) -> dict:
    """
    Variante de verifier() renvoyant un dict complet pour le rapport.

    Retourne
    --------
    dict :
        statut        "OK" | "ANOMALIE"
        ecart         distance euclidienne en mètres
        pos_reelle    [x, y, z]
        pos_theorique [x, y, z]
        seuil         valeur utilisée
        detail        message lisible
    """
    ecart = _distance_euclidienne(pos_reelle, pos_theorique)
    statut = "OK" if ecart <= seuil else "ANOMALIE"
    detail = (
        f"Conforme — écart {ecart:.4f} m"
        if statut == "OK"
        else f"Déviation {ecart:.4f} m > seuil {seuil:.4f} m"
    )
    return {
        "statut": statut,
        "ecart": round(ecart, 6),
        "pos_reelle": pos_reelle,
        "pos_theorique": pos_theorique,
        "seuil": seuil,
        "detail": detail,
    }


# ══════════════════════════════════════════════════════
#  3. ANALYSE D'UN CYCLE COMPLET
# ══════════════════════════════════════════════════════

def analyser_cycle(
    positions_reelles: list,
    trajectoire_theorique: list,
    seuil: float,
) -> dict:
    """
    Analyse point par point un cycle de soudage complet.

    Paramètres
    ----------
    positions_reelles     : liste de [x, y, z] mesurés en temps réel
    trajectoire_theorique : liste de dicts {"pos": [x,y,z], "vitesse": float}
                            — format contrat commun (Angie / ia_trajectoire.py)
    seuil                 : écart max toléré en mètres

    Retourne
    --------
    dict rapport qualité complet (voir exporter_rapport pour le détail)
    """
    resultats = []
    anomalies = 0
    ecart_max = 0.0

    for i, (pos_r, point_t) in enumerate(zip(positions_reelles, trajectoire_theorique)):
        res = verifier_detail(pos_r, point_t["pos"], seuil)
        res["index"] = i
        resultats.append(res)

        if res["statut"] == "ANOMALIE":
            anomalies += 1
        if res["ecart"] > ecart_max:
            ecart_max = res["ecart"]

    total = len(resultats)
    taux = round(((total - anomalies) / total) * 100, 2) if total > 0 else 0.0

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_points": total,
        "points_ok": total - anomalies,
        "anomalies": anomalies,
        "taux_qualite_pct": taux,
        "ecart_max_m": round(ecart_max, 6),
        "seuil_m": seuil,
        "verdict": "CYCLE OK" if anomalies == 0 else f"CYCLE DÉFAILLANT ({anomalies} anomalie(s))",
        "details": resultats,
    }


# ══════════════════════════════════════════════════════
#  4. OVERLAY STATUT — CONSOLE / COPPELIASIM
# ══════════════════════════════════════════════════════

# Codes ANSI pour la console
_VERT   = "\033[92m"
_JAUNE  = "\033[93m"
_ROUGE  = "\033[91m"
_RESET  = "\033[0m"

# Textes overlay (repris dans CoppeliaSim si sim disponible)
STATUTS = {
    "OK":       "NORMAL",
    "ANOMALIE": "ANOMALIE",
    "ARRET":    "ARRÊT",
}


def afficher_statut_console(statut: str, ecart: float = None):
    """
    Affiche le statut en console avec couleur.
    statut : "OK" | "ANOMALIE" | "ARRET"
    """
    label = STATUTS.get(statut, statut)
    if statut == "OK":
        ligne = f"{_VERT}  ✅  [{label}]{_RESET}"
    elif statut == "ANOMALIE":
        ligne = f"{_JAUNE}  ⚠️   [{label}]{_RESET}"
    else:
        ligne = f"{_ROUGE}  🛑  [{label}] — ARRÊT D'URGENCE{_RESET}"

    print("─" * 44)
    print(ligne)
    if ecart is not None:
        print(f"      Écart mesuré : {ecart:.4f} m")
    print("─" * 44)


def afficher_statut_coppeliasim(sim, statut: str):
    """
    Overlay dans CoppeliaSim via addLog.
    Appelée depuis main.py quand la simulation tourne.

    Paramètres
    ----------
    sim    : objet ZMQ RemoteAPI (passé par Louis)
    statut : "OK" | "ANOMALIE" | "ARRET"
    """
    label = STATUTS.get(statut, statut)
    # verbosité : 2=INFO, 4=WARNING, 8=ERROR
    verbosity = {
        "OK":       2,
        "ANOMALIE": 4,
        "ARRET":    8,
    }.get(statut, 2)
    try:
        sim.addLog(verbosity, f"[QUALITE] {label}")
    except Exception:
        # CoppeliaSim non connecté — fallback console
        afficher_statut_console(statut)


# ══════════════════════════════════════════════════════
#  5. TRACÉ DU CORDON (Drawing Object — fourni par Delly)
# ══════════════════════════════════════════════════════

def tracer_point_cordon(sim, drawing_handle: int, pos: list):
    """
    Ajoute un point au tracé du cordon dans CoppeliaSim.

    Paramètres
    ----------
    sim            : objet ZMQ RemoteAPI
    drawing_handle : handle du Drawing Object créé par Delly
    pos            : [x, y, z] — position réelle du robot à ce pas
    """
    try:
        sim.addDrawingObjectItem(drawing_handle, pos)
    except Exception as e:
        print(f"  [cordon] Erreur tracé : {e}")


# ══════════════════════════════════════════════════════
#  6. RAPPORT QUALITÉ — AFFICHAGE + EXPORT JSON
# ══════════════════════════════════════════════════════

def afficher_rapport(rapport: dict):
    """Affiche le rapport qualité final en console."""
    sep = "═" * 50
    print(f"\n{sep}")
    print("  📋  RAPPORT QUALITÉ — SmartFactory")
    print(sep)
    print(f"  Date/heure      : {rapport['timestamp']}")
    print(f"  Points analysés : {rapport['total_points']}")
    print(f"  Points OK       : {rapport['points_ok']}")
    print(f"  Anomalies       : {rapport['anomalies']}")
    print(f"  Taux qualité    : {rapport['taux_qualite_pct']} %")
    print(f"  Écart maximum   : {rapport['ecart_max_m']} m")
    print(f"  Seuil utilisé   : {rapport['seuil_m']} m")
    print(f"\n  ▶  VERDICT : {rapport['verdict']}")
    print(f"{sep}\n")


def exporter_rapport(rapport: dict, fichier: str = "rapport_qualite.json"):
    """Sauvegarde le rapport qualité dans un fichier JSON."""
    chemin = Path(fichier)
    with open(chemin, "w", encoding="utf-8") as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)
    print(f"  💾 Rapport exporté → {chemin.resolve()}")


# ══════════════════════════════════════════════════════
#  7. UTILITAIRE INTERNE
# ══════════════════════════════════════════════════════

def _distance_euclidienne(p1: list, p2: list) -> float:
    """Distance euclidienne entre deux points 3D."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))


# ══════════════════════════════════════════════════════
#  8. DONNÉES FACTICES & DÉMONSTRATION STANDALONE
# ══════════════════════════════════════════════════════

# Trajectoire théorique — format contrat commun (compatible ia_trajectoire.py)
_TRAJECTOIRE_DEMO = [
    {"pos": [0.500, 0.200, 0.800], "vitesse": 0.05},
    {"pos": [0.500, 0.210, 0.800], "vitesse": 0.05},
    {"pos": [0.500, 0.220, 0.800], "vitesse": 0.05},
    {"pos": [0.500, 0.230, 0.800], "vitesse": 0.05},
    {"pos": [0.500, 0.240, 0.800], "vitesse": 0.05},
    {"pos": [0.550, 0.240, 0.800], "vitesse": 0.02},  # angle — vitesse réduite
    {"pos": [0.600, 0.240, 0.800], "vitesse": 0.05},
    {"pos": [0.610, 0.240, 0.800], "vitesse": 0.05},
]

# Positions réelles « bonnes » (légères vibrations normales)
_POS_BONNES = [
    [0.500, 0.200, 0.800],
    [0.500, 0.210, 0.800],
    [0.501, 0.220, 0.800],
    [0.500, 0.230, 0.801],
    [0.500, 0.240, 0.800],
    [0.550, 0.240, 0.800],
    [0.600, 0.240, 0.800],
    [0.610, 0.241, 0.800],
]

# Positions réelles « déviées » (anomalies introduites)
_POS_DEVIEES = [
    [0.500, 0.200, 0.800],
    [0.500, 0.210, 0.800],
    [0.522, 0.220, 0.800],   # ← déviation X (+22 mm)
    [0.500, 0.230, 0.818],   # ← déviation Z (+18 mm)
    [0.500, 0.240, 0.800],
    [0.550, 0.240, 0.800],
    [0.600, 0.240, 0.800],
    [0.610, 0.241, 0.800],
]

SEUIL_DEMO = 0.010  # 10 mm


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("\n" + "─" * 50)
    print("  SmartFactory — Module 4 : Qualité & Visualisation")
    print("  Auteure : Mibell Raphaëlla")
    print("─" * 50)

    # ── Test verifier() simple ──────────────────────────
    print("\n[ Test verifier() — point unique ]")
    r1 = verifier([0.500, 0.200, 0.800], [0.500, 0.200, 0.800], SEUIL_DEMO)
    r2 = verifier([0.522, 0.200, 0.800], [0.500, 0.200, 0.800], SEUIL_DEMO)
    print(f"  Point conforme  → {r1}")   # OK
    print(f"  Point dévié     → {r2}")   # ANOMALIE

    # ── Test overlay console ────────────────────────────
    print("\n[ Overlay statut console ]")
    afficher_statut_console("OK",       ecart=0.003)
    afficher_statut_console("ANOMALIE", ecart=0.022)
    afficher_statut_console("ARRET")

    # ── Test cycle BON ──────────────────────────────────
    print("\n[ TEST 1 — Trajectoire BONNE ]")
    rapport_bon = analyser_cycle(_POS_BONNES, _TRAJECTOIRE_DEMO, SEUIL_DEMO)
    afficher_rapport(rapport_bon)
    exporter_rapport(rapport_bon, "rapport_cycle_bon.json")

    # ── Test cycle DÉVIÉ ────────────────────────────────
    print("[ TEST 2 — Trajectoire DÉVIÉE ]")
    rapport_devie = analyser_cycle(_POS_DEVIEES, _TRAJECTOIRE_DEMO, SEUIL_DEMO)
    afficher_rapport(rapport_devie)
    exporter_rapport(rapport_devie, "rapport_cycle_devie.json")

    print("  ✅  Démonstration terminée.\n")