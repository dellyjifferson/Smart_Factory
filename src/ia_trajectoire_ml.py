"""Module IA v2 — ajustement de la vitesse de soudage par scikit-learn.

Étend la v1 (règles binaires) avec un modèle de régression qui prédit la
vitesse à partir de **features géométriques locales** :

    - angle_local        : angle (rad) entre (i-1, i, i+1) ; 0 = ligne droite
    - courbure_locale    : 1 / rayon du cercle circonscrit aux 3 points ;
                           ≈ 0 sur une ligne droite, élevé sur un arc serré
    - angle_max_fenetre  : angle max observé sur la fenêtre ±2 points autour
                           de i — permet d'**anticiper** un coin proche

Le modèle est entraîné une fois (`entrainement_modele.py`) sur un dataset
synthétique généré par une fonction « expert » (`vitesse_experte`), puis
chargé depuis `data/modele_vitesse.joblib`.

Le format de sortie est **identique** au contrat commun de la v1 :
    [{"pos": [x, y, z], "vitesse": v}, ...]

Auteure : Saint-Vil Angie-Reyna Leddycia — Groupe 1 SmartFactory.
"""
from __future__ import annotations

import math
from pathlib import Path

from ia_trajectoire import charger_piece, generer_trajectoire

V_NOMINALE = 0.05
V_MIN = 0.015
SEUIL_ANGLE_RAD = math.radians(20)
SEUIL_COURBURE = 5.0  # 1/m — au-delà = arc serré (r < 20 cm)

CHEMIN_MODELE_DEFAUT = Path(__file__).resolve().parents[1] / "data" / "modele_vitesse.joblib"


def vitesse_experte(angle_local, courbure_locale, angle_max_fenetre):
    """Fonction « expert » qui sert de cible synthétique pour l'entraînement.

    Module la vitesse selon trois critères, de façon **progressive**
    (contrairement à la v1 qui est binaire). C'est cette fonction non
    linéaire que le modèle apprend.
    """
    v = V_NOMINALE

    if angle_max_fenetre > SEUIL_ANGLE_RAD:
        excess = (angle_max_fenetre - SEUIL_ANGLE_RAD) / (math.pi - SEUIL_ANGLE_RAD)
        v *= max(0.3, 1.0 - 0.7 * excess)

    if courbure_locale > SEUIL_COURBURE:
        excess = (courbure_locale - SEUIL_COURBURE) / 30.0
        v *= max(0.5, 1.0 - 0.5 * excess)

    return max(V_MIN, v)


def extraire_features_point(trajectoire, i, ferme=False):
    """Calcule le vecteur de features pour le point d'index `i`.

    Retourne `[angle_local, courbure_locale, angle_max_fenetre]`.
    Aux bords (i=0 ou i=n-1 en mode non-fermé), `angle_local` vaut 0
    (pas d'angle défini sans deux voisins).
    """
    angle_local = _angle_3pts(trajectoire, i, ferme)
    if angle_local is None:
        angle_local = 0.0
    courbure = _courbure_3pts(trajectoire, i, ferme)

    angles = []
    for j in range(i - 2, i + 3):
        a = _angle_3pts(trajectoire, j, ferme)
        if a is not None:
            angles.append(a)
    angle_max_fenetre = max(angles) if angles else 0.0

    return [angle_local, courbure, angle_max_fenetre]


def extraire_features_trajectoire(trajectoire, ferme=False):
    """Renvoie la matrice de features (n_points × n_features)."""
    return [extraire_features_point(trajectoire, i, ferme=ferme) for i in range(len(trajectoire))]


def generer_trajectoire_ml(piece_data, modele):
    """Génère la trajectoire et **remplace** les vitesses par les prédictions du modèle.

    Args:
        piece_data: dict (même format que `generer_trajectoire`).
        modele: objet sklearn (RandomForestRegressor ou similaire) ayant `predict`.

    Returns:
        Trajectoire au format contrat commun, vitesses ML.
    """
    traj = generer_trajectoire(piece_data)
    ferme = bool(piece_data.get("ferme", False))
    X = extraire_features_trajectoire(traj, ferme=ferme)
    vitesses = modele.predict(X)
    for i, v in enumerate(vitesses):
        traj[i]["vitesse"] = max(V_MIN, float(v))
    return traj


def charger_modele(chemin=None):
    """Charge un modèle entraîné via joblib.

    Force `n_jobs=1` pour garantir des prédictions strictement déterministes
    (sklearn peut produire des écarts < 1e-15 entre appels avec n_jobs > 1
    à cause de l'ordre d'accumulation parallèle).
    """
    import joblib
    chemin = Path(chemin) if chemin else CHEMIN_MODELE_DEFAUT
    modele = joblib.load(chemin)
    if hasattr(modele, "n_jobs"):
        modele.n_jobs = 1
    return modele


def _angle_3pts(trajectoire, i, ferme=False):
    """Angle interne en `i` (rad). 0 = droite, π = demi-tour. None si i en bord."""
    n = len(trajectoire)
    if n < 3:
        return None
    if ferme:
        a = trajectoire[(i - 1) % n]["pos"]
        b = trajectoire[i % n]["pos"]
        c = trajectoire[(i + 1) % n]["pos"]
    else:
        if i <= 0 or i >= n - 1:
            return None
        a = trajectoire[i - 1]["pos"]
        b = trajectoire[i]["pos"]
        c = trajectoire[i + 1]["pos"]
    ab = [b[k] - a[k] for k in range(3)]
    bc = [c[k] - b[k] for k in range(3)]
    nab = math.sqrt(sum(x * x for x in ab))
    nbc = math.sqrt(sum(x * x for x in bc))
    if nab < 1e-9 or nbc < 1e-9:
        return 0.0
    cos_t = sum(ab[k] * bc[k] for k in range(3)) / (nab * nbc)
    cos_t = max(-1.0, min(1.0, cos_t))
    return math.acos(cos_t)


def _courbure_3pts(trajectoire, i, ferme=False):
    """Courbure (1/m) du cercle circonscrit aux 3 points autour de i. 0 si colinéaires."""
    n = len(trajectoire)
    if n < 3:
        return 0.0
    if ferme:
        a = trajectoire[(i - 1) % n]["pos"]
        b = trajectoire[i % n]["pos"]
        c = trajectoire[(i + 1) % n]["pos"]
    else:
        if i <= 0 or i >= n - 1:
            return 0.0
        a = trajectoire[i - 1]["pos"]
        b = trajectoire[i]["pos"]
        c = trajectoire[i + 1]["pos"]
    ab = [b[k] - a[k] for k in range(3)]
    ac = [c[k] - a[k] for k in range(3)]
    bc = [c[k] - b[k] for k in range(3)]
    nab = math.sqrt(sum(x * x for x in ab))
    nbc = math.sqrt(sum(x * x for x in bc))
    nac = math.sqrt(sum(x * x for x in ac))
    cross = [
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    ]
    deux_aire = math.sqrt(sum(x * x for x in cross))
    if deux_aire < 1e-9 or nab * nbc * nac < 1e-12:
        return 0.0
    return 2.0 * deux_aire / (nab * nbc * nac)


if __name__ == "__main__":
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    racine = Path(__file__).resolve().parents[1]
    chemin = Path(sys.argv[1]) if len(sys.argv) > 1 else racine / "data" / "piece.json"
    if not chemin.is_absolute():
        chemin = racine / chemin

    piece = charger_piece(chemin)
    modele = charger_modele()
    traj = generer_trajectoire_ml(piece, modele)

    print(f"Pièce       : {piece.get('id', '?')}")
    print(f"Modèle      : RandomForestRegressor (v2 sklearn)")
    print(f"Points générés : {len(traj)}\n")
    for i, p in enumerate(traj):
        print(f"  [{i:3d}] pos=[{p['pos'][0]:.3f}, {p['pos'][1]:.3f}, {p['pos'][2]:.3f}]  v={p['vitesse']:.4f}")
