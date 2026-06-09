"""Module IA — génération de trajectoire de soudage.

Transforme la géométrie d'une pièce (`piece.json`) en une liste de points
de soudage au format du contrat commun de l'équipe SmartFactory :

    [{"pos": [x, y, z], "vitesse": v}, ...]

Types de joints supportés :
    - "ligne" : segment droit (debut, fin)
    - "arc"   : arc de cercle court (debut, fin, centre)

Si `piece["ferme"] == True`, la trajectoire est traitée comme un contour
fermé (l'analyse d'angles tourne en circulaire, et le doublon final est
retiré si présent).

Auteure : Saint-Vil Angie-Reyna Leddycia — Groupe 1 SmartFactory.

Lancement direct (depuis la racine du dépôt) :
    python src/ia_trajectoire.py [chemin/vers/piece.json]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

_EPS = 1e-9


def charger_piece(chemin):
    """Charge un fichier piece.json et renvoie son contenu."""
    with open(chemin, "r", encoding="utf-8") as f:
        return json.load(f)


def generer_trajectoire(piece_data):
    """Génère la trajectoire de soudage à partir des données géométriques.

    Args:
        piece_data: dict décrivant la pièce (clés "joints", "parametres",
            et optionnellement "ferme": bool).

    Returns:
        list[dict] au format [{"pos": [x, y, z], "vitesse": v}, ...].
    """
    params = piece_data.get("parametres", {})
    pas = params.get("pas_mm", 10) / 1000.0
    v_nom = params.get("vitesse_nominale", 0.05)
    v_angle = params.get("vitesse_angle", 0.02)
    seuil_rad = math.radians(params.get("seuil_angle_deg", 30))
    ferme = bool(piece_data.get("ferme", False))

    trajectoire = []
    for joint in piece_data.get("joints", []):
        pts = _echantillonner_joint(joint, pas)
        if pts is None:
            continue
        if trajectoire and _distance(trajectoire[-1]["pos"], pts[0]) < 1e-6:
            pts = pts[1:]
        trajectoire.extend({"pos": p, "vitesse": v_nom} for p in pts)

    if ferme and len(trajectoire) >= 2 and _distance(trajectoire[-1]["pos"], trajectoire[0]["pos"]) < 1e-6:
        trajectoire.pop()

    _ralentir_dans_les_angles(trajectoire, v_angle, seuil_rad, ferme=ferme)
    return trajectoire


def _echantillonner_joint(joint, pas):
    """Échantillonne un joint selon son type. None si type non supporté."""
    t = joint["type"]
    if t == "ligne":
        return _echantillonner_ligne(joint["debut"], joint["fin"], pas)
    if t == "arc":
        return _echantillonner_arc(joint["debut"], joint["fin"], joint["centre"], pas)
    return None


def _distance(a, b):
    return math.sqrt(sum((bi - ai) ** 2 for ai, bi in zip(a, b)))


def _echantillonner_ligne(debut, fin, pas):
    longueur = _distance(debut, fin)
    if longueur < 1e-6:
        return [list(debut)]
    n = max(int(round(longueur / pas)), 1)
    return [
        [debut[k] + (fin[k] - debut[k]) * i / n for k in range(3)]
        for i in range(n + 1)
    ]


def _echantillonner_arc(debut, fin, centre, pas):
    """Échantillonne le plus court arc allant de `debut` à `fin` autour de `centre`.

    Lève ValueError si l'arc est dégénéré (rayons différents, debut/fin
    confondus, ou debut/fin diamétralement opposés — le plan est ambigu).
    """
    vd = [debut[k] - centre[k] for k in range(3)]
    vf = [fin[k] - centre[k] for k in range(3)]
    r_d = math.sqrt(sum(x * x for x in vd))
    r_f = math.sqrt(sum(x * x for x in vf))
    if r_d < _EPS or abs(r_d - r_f) > 1e-4:
        raise ValueError(
            f"Arc invalide : distances debut/centre ({r_d:.4f}) et fin/centre "
            f"({r_f:.4f}) différentes — le point n'est pas sur le même cercle."
        )

    r = r_d
    vd_n = [x / r for x in vd]
    vf_n = [x / r for x in vf]

    cos_a = max(-1.0, min(1.0, sum(vd_n[k] * vf_n[k] for k in range(3))))
    if cos_a > 1 - _EPS:
        raise ValueError("Arc dégénéré : debut et fin confondus.")
    if cos_a < -1 + _EPS:
        raise ValueError(
            "Arc à 180° : debut et fin diamétralement opposés — le plan de l'arc "
            "est ambigu. Découpez en deux arcs ou utilisez deux segments."
        )

    angle = math.acos(cos_a)
    proj = cos_a
    tangent = [vf_n[k] - proj * vd_n[k] for k in range(3)]
    n_tan = math.sqrt(sum(x * x for x in tangent))
    tangent = [x / n_tan for x in tangent]

    longueur = r * angle
    n = max(int(round(longueur / pas)), 1)
    points = []
    for i in range(n + 1):
        t = (i / n) * angle
        pos = [
            centre[k] + r * (math.cos(t) * vd_n[k] + math.sin(t) * tangent[k])
            for k in range(3)
        ]
        points.append(pos)
    return points


def _ralentir_dans_les_angles(trajectoire, v_angle, seuil_rad, ferme=False):
    """Réduit la vitesse autour des points où le cap change brutalement.

    Si `ferme=True`, la trajectoire est traitée comme circulaire (le dernier
    point est voisin du premier).
    """
    n = len(trajectoire)
    if n < 3:
        return
    indices = range(n) if ferme else range(1, n - 1)
    for i in indices:
        a = trajectoire[(i - 1) % n]["pos"]
        b = trajectoire[i]["pos"]
        c = trajectoire[(i + 1) % n]["pos"]
        ab = [b[k] - a[k] for k in range(3)]
        bc = [c[k] - b[k] for k in range(3)]
        nab = math.sqrt(sum(x * x for x in ab))
        nbc = math.sqrt(sum(x * x for x in bc))
        if nab < _EPS or nbc < _EPS:
            continue
        cos_t = sum(ab[k] * bc[k] for k in range(3)) / (nab * nbc)
        cos_t = max(-1.0, min(1.0, cos_t))
        if math.acos(cos_t) > seuil_rad:
            for j in (i - 1, i, i + 1):
                idx = j % n if ferme else j
                if 0 <= idx < n:
                    trajectoire[idx]["vitesse"] = v_angle


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    racine = Path(__file__).resolve().parents[1]
    chemin = Path(sys.argv[1]) if len(sys.argv) > 1 else racine / "data" / "piece.json"
    if not chemin.is_absolute():
        chemin = racine / chemin

    piece = charger_piece(chemin)
    traj = generer_trajectoire(piece)

    print(f"Pièce       : {piece.get('id', '?')}")
    print(f"Description : {piece.get('description', '')}")
    print(f"Fermée      : {bool(piece.get('ferme', False))}")
    print(f"Points générés : {len(traj)}\n")
    v_nom = piece.get("parametres", {}).get("vitesse_nominale", 0.05)
    for i, p in enumerate(traj):
        marqueur = "  <-- angle" if p["vitesse"] < v_nom else ""
        print(f"  [{i:3d}] pos=[{p['pos'][0]:.3f}, {p['pos'][1]:.3f}, {p['pos'][2]:.3f}]  v={p['vitesse']:.4f}{marqueur}")
