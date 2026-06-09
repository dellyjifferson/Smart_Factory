"""Entraînement du modèle ML qui prédit la vitesse de soudage.

Pipeline :
    1. Génère un dataset synthétique en parcourant des pièces variées
       (lignes droites, L à angles divers, arcs de rayons divers, contours).
    2. Pour chaque point intérieur : extrait les features géométriques
       et calcule la vitesse « experte » (cible) via `vitesse_experte`.
    3. Split train/test, entraîne un RandomForestRegressor.
    4. Affiche R², MAE, et l'importance des features.
    5. Sauvegarde le modèle dans data/modele_vitesse.joblib.

Lancement (depuis la racine du dépôt) :
    python src/entrainement_modele.py

Auteure : Saint-Vil Angie-Reyna Leddycia — Groupe 1 SmartFactory.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from ia_trajectoire import generer_trajectoire
from ia_trajectoire_ml import (
    CHEMIN_MODELE_DEFAUT,
    extraire_features_trajectoire,
    vitesse_experte,
)

FEATURES_NOMS = ["angle_local", "courbure_locale", "angle_max_fenetre"]

PARAMS_BASE = {
    "pas_mm": 10,
    "vitesse_nominale": 0.05,
    "vitesse_angle": 0.02,
    "seuil_angle_deg": 30,
}


def _piece_L(angle_deg, longueur=0.2, z=0.8):
    """Cordon en L formant l'angle interne `angle_deg` (180° = droit, 0° = retour)."""
    rad = math.radians(angle_deg)
    debut = [0.5, 0.2, z]
    coude = [0.5, 0.2 + longueur, z]
    fin = [0.5 + longueur * math.sin(rad), 0.2 + longueur + longueur * math.cos(rad), z]
    return {
        "id": f"synth_L_{angle_deg}",
        "joints": [
            {"type": "ligne", "debut": debut, "fin": coude},
            {"type": "ligne", "debut": coude, "fin": fin},
        ],
        "parametres": PARAMS_BASE,
    }


def _piece_arc(rayon, angle_balayé_deg, z=0.8):
    """Arc de rayon donné couvrant `angle_balayé_deg` degrés."""
    rad = math.radians(angle_balayé_deg)
    centre = [0.6, 0.4, z]
    debut = [centre[0], centre[1] - rayon, z]
    fin = [centre[0] + rayon * math.sin(rad), centre[1] - rayon * math.cos(rad), z]
    return {
        "id": f"synth_arc_r{rayon}_a{angle_balayé_deg}",
        "joints": [{"type": "arc", "debut": debut, "fin": fin, "centre": centre}],
        "parametres": PARAMS_BASE,
    }


def _piece_rectangle(largeur, hauteur, z=0.8):
    """Contour rectangulaire fermé."""
    x0, y0 = 0.5, 0.2
    p1 = [x0, y0, z]
    p2 = [x0 + largeur, y0, z]
    p3 = [x0 + largeur, y0 + hauteur, z]
    p4 = [x0, y0 + hauteur, z]
    return {
        "id": f"synth_rect_{largeur}x{hauteur}",
        "joints": [
            {"type": "ligne", "debut": p1, "fin": p2},
            {"type": "ligne", "debut": p2, "fin": p3},
            {"type": "ligne", "debut": p3, "fin": p4},
            {"type": "ligne", "debut": p4, "fin": p1},
        ],
        "parametres": PARAMS_BASE,
        "ferme": True,
    }


def _piece_ligne(longueur, z=0.8):
    return {
        "id": f"synth_ligne_{longueur}",
        "joints": [
            {"type": "ligne", "debut": [0.5, 0.2, z], "fin": [0.5, 0.2 + longueur, z]}
        ],
        "parametres": PARAMS_BASE,
    }


def generer_pieces_synthetiques():
    """Renvoie une liste variée de pièces pour l'entraînement."""
    pieces = []
    pieces.extend(_piece_ligne(L) for L in [0.1, 0.2, 0.3, 0.5])
    pieces.extend(_piece_L(a) for a in [30, 45, 60, 75, 90, 105, 120, 135, 150])
    pieces.extend(
        _piece_arc(r, a)
        for r in [0.05, 0.1, 0.15, 0.2, 0.3, 0.5]
        for a in [30, 60, 90, 120, 150]
    )
    pieces.extend(
        _piece_rectangle(w, h)
        for w in [0.1, 0.2, 0.3]
        for h in [0.1, 0.2, 0.3]
    )
    return pieces


def construire_dataset():
    """Construit (X, y) à partir des pièces synthétiques."""
    X, y = [], []
    pieces = generer_pieces_synthetiques()
    print(f"Pièces générées : {len(pieces)}")

    for piece in pieces:
        traj = generer_trajectoire(piece)
        ferme = bool(piece.get("ferme", False))
        features = extraire_features_trajectoire(traj, ferme=ferme)
        for f in features:
            X.append(f)
            y.append(vitesse_experte(*f))

    return X, y


def entrainer(X_train, y_train):
    """Entraîne et renvoie le modèle."""
    modele = RandomForestRegressor(
        n_estimators=80,
        max_depth=10,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    modele.fit(X_train, y_train)
    return modele


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=== Entraînement du modèle de vitesse (v2 sklearn) ===\n")
    X, y = construire_dataset()
    print(f"Échantillons collectés : {len(X)}")
    print(f"Plage des vitesses cibles : [{min(y):.4f}, {max(y):.4f}] m/s\n")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    modele = entrainer(X_train, y_train)

    y_pred = modele.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    print(f"R²  (test) : {r2:.4f}")
    print(f"MAE (test) : {mae:.5f} m/s\n")

    print("Importance des features :")
    for nom, imp in zip(FEATURES_NOMS, modele.feature_importances_):
        print(f"  {nom:<20s} {imp:.3f}")
    print()

    CHEMIN_MODELE_DEFAUT.parent.mkdir(exist_ok=True)
    joblib.dump(modele, CHEMIN_MODELE_DEFAUT)
    taille_ko = CHEMIN_MODELE_DEFAUT.stat().st_size / 1024
    print(f"Modèle sauvegardé : {CHEMIN_MODELE_DEFAUT}  ({taille_ko:.1f} Ko)")


if __name__ == "__main__":
    main()
