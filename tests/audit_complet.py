"""Audit complet du module IA / trajectoire.

Vérifie systématiquement :
  - les 6 garanties annoncées dans docs/contrat_trajectoire.md
  - les edge cases du module v1 et v2
  - la cohérence v1 ↔ v2 (mêmes positions, vitesses différentes)
  - la reproductibilité du pipeline ML
  - l'API publique et le doc-code alignment

Lancement (depuis la racine du dépôt) :
    python tests/audit_complet.py

Exit code 0 si tout passe, 1 sinon.
"""
from __future__ import annotations

import math
import sys
import traceback
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
SRC = RACINE / "src"
sys.path.insert(0, str(SRC))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from ia_trajectoire import (  # noqa: E402
    _echantillonner_arc,
    _echantillonner_ligne,
    charger_piece,
    generer_trajectoire,
)
from ia_trajectoire_ml import (  # noqa: E402
    V_MIN,
    V_NOMINALE,
    charger_modele,
    extraire_features_trajectoire,
    generer_trajectoire_ml,
    vitesse_experte,
)

PASSED = []
FAILED = []


def _run(nom, fn):
    try:
        fn()
        PASSED.append(nom)
        print(f"  OK   {nom}")
    except AssertionError as e:
        FAILED.append((nom, f"ASSERTION: {e}"))
        print(f"  FAIL {nom}: {e}")
    except Exception as e:
        FAILED.append((nom, f"{type(e).__name__}: {e}"))
        print(f"  FAIL {nom}: {type(e).__name__}: {e}")


def _distance(a, b):
    return math.sqrt(sum((bi - ai) ** 2 for ai, bi in zip(a, b)))


PIECES_REELLES = [
    "data/piece.json",
    "data/piece_arc.json",
    "data/piece_contour.json",
]

# ============================================================
print("=== Section 1 : Garanties du contrat (sur 3 pièces réelles) ===")
# ============================================================

for chemin_str in PIECES_REELLES:
    chemin = RACINE / chemin_str
    nom_piece = chemin.stem
    piece = charger_piece(chemin)
    traj = generer_trajectoire(piece)
    pas_m = piece["parametres"]["pas_mm"] / 1000.0
    v_nom = piece["parametres"]["vitesse_nominale"]

    _run(f"[{nom_piece}] G1 len(traj) >= 2",
         lambda t=traj: (_ for _ in ()).throw(AssertionError(f"len={len(t)}")) if len(t) < 2 else None)

    def _check_dedup(t=traj):
        for i in range(1, len(t)):
            d = _distance(t[i - 1]["pos"], t[i]["pos"])
            assert d > 1e-6, f"doublon au point {i}: d={d:.2e}"
    _run(f"[{nom_piece}] G2 pas de doublons consécutifs", _check_dedup)

    def _check_espace(t=traj, p=pas_m):
        for i in range(1, len(t)):
            d = _distance(t[i - 1]["pos"], t[i]["pos"])
            assert 0.5 * p <= d <= 1.5 * p, f"espacement {d:.4f}m hors [0.5*pas, 1.5*pas] au point {i}"
    _run(f"[{nom_piece}] G3 espacement ≈ pas_mm (±50%)", _check_espace)

    def _check_v_pos(t=traj):
        for i, p in enumerate(t):
            assert p["vitesse"] > 0, f"vitesse <= 0 au point {i}: v={p['vitesse']}"
    _run(f"[{nom_piece}] G4 vitesse > 0 partout", _check_v_pos)

    def _check_format(t=traj):
        for i, p in enumerate(t):
            assert isinstance(p["pos"], list), f"pos pas list au point {i}"
            assert len(p["pos"]) == 3, f"pos longueur != 3 au point {i}"
            for c in p["pos"]:
                assert isinstance(c, (int, float)), f"coord pas numérique au point {i}"
            assert isinstance(p["vitesse"], (int, float)), f"vitesse pas numérique au point {i}"
    _run(f"[{nom_piece}] format — pos list[float,3], vitesse float", _check_format)


# Garantie 5 et 6 — testées en sémantique sur les pièces réelles
def _g5_L():
    piece = charger_piece(RACINE / "data" / "piece.json")
    traj = generer_trajectoire(piece)
    v_nom = piece["parametres"]["vitesse_nominale"]
    ralentis = [i for i, p in enumerate(traj) if p["vitesse"] < v_nom]
    assert len(ralentis) == 3, f"L: attendu 3 points ralentis, vu {len(ralentis)}: {ralentis}"
    assert ralentis == [19, 20, 21], f"L: indices attendus [19,20,21], vu {ralentis}"
_run("G5 L à 90° — 3 points consécutifs ralentis au coude", _g5_L)


def _g6_contour():
    piece = charger_piece(RACINE / "data" / "piece_contour.json")
    traj = generer_trajectoire(piece)
    v_nom = piece["parametres"]["vitesse_nominale"]
    ralentis = sorted(i for i, p in enumerate(traj) if p["vitesse"] < v_nom)
    assert len(ralentis) == 12, f"contour: attendu 12 points ralentis (4 coins × 3), vu {len(ralentis)}: {ralentis}"
    # Doit inclure le wrap-around : indices 79 et 0 et 1
    assert 0 in ralentis and 1 in ralentis and 79 in ralentis, \
        f"contour fermé: wrap-around manquant, ralentis={ralentis}"
_run("G6 Contour fermé — 4 coins × 3 pts ralentis (avec wrap-around)", _g6_contour)


def _arc_no_slow():
    piece = charger_piece(RACINE / "data" / "piece_arc.json")
    traj = generer_trajectoire(piece)
    v_nom = piece["parametres"]["vitesse_nominale"]
    ralentis = [i for i, p in enumerate(traj) if p["vitesse"] < v_nom]
    assert len(ralentis) == 0, f"arc lisse: aucun ralentissement attendu, vu {len(ralentis)}: {ralentis}"
_run("Arc lisse — aucun point ralenti", _arc_no_slow)


# ============================================================
print("\n=== Section 2 : Edge cases v1 ===")
# ============================================================

def _no_params():
    piece = {"id": "test", "joints": [
        {"type": "ligne", "debut": [0, 0, 0], "fin": [0.05, 0, 0]}
    ]}
    traj = generer_trajectoire(piece)
    assert len(traj) >= 2
_run("Piece sans 'parametres' → defaults utilisés", _no_params)

def _no_joints():
    piece = {"id": "test", "parametres": {"pas_mm": 10}}
    traj = generer_trajectoire(piece)
    assert traj == [], f"attendu [], vu {traj}"
_run("Piece sans 'joints' → trajectoire vide", _no_joints)

def _unknown_type():
    piece = {"id": "test", "joints": [
        {"type": "spirale", "debut": [0, 0, 0], "fin": [0.1, 0, 0]}
    ], "parametres": {}}
    traj = generer_trajectoire(piece)
    assert traj == [], f"attendu skip silencieux → [], vu {traj}"
_run("Type de joint inconnu → skip silencieux", _unknown_type)

def _short_line():
    piece = {"id": "test", "joints": [
        {"type": "ligne", "debut": [0, 0, 0], "fin": [0.003, 0, 0]}
    ], "parametres": {"pas_mm": 10}}
    traj = generer_trajectoire(piece)
    assert len(traj) >= 2, f"ligne courte: au moins 2 points attendus, vu {len(traj)}"
    # Et pas de doublons
    d = _distance(traj[0]["pos"], traj[1]["pos"])
    assert d > 1e-6, f"ligne courte: doublon au point 1: d={d:.2e}"
_run("Ligne courte (< pas) → 2 points distincts", _short_line)

def _degenerate_line():
    piece = {"id": "test", "joints": [
        {"type": "ligne", "debut": [0.5, 0.2, 0.8], "fin": [0.5, 0.2, 0.8]}
    ], "parametres": {"pas_mm": 10}}
    traj = generer_trajectoire(piece)
    # Doit soit retourner [] / [un seul point], soit lever — pas 2 doublons
    if len(traj) >= 2:
        for i in range(1, len(traj)):
            d = _distance(traj[i - 1]["pos"], traj[i]["pos"])
            assert d > 1e-6, f"BUG: ligne dégénérée (debut==fin) crée doublons consécutifs, viole G2 — traj={traj}"
_run("Ligne dégénérée (debut==fin) → pas de doublons (G2)", _degenerate_line)

def _arc_eq():
    try:
        _echantillonner_arc([0, 0, 0], [0, 0, 0], [0.5, 0, 0], 0.01)
        raise AssertionError("ValueError attendue (debut==fin)")
    except ValueError:
        pass
_run("Arc debut==fin → ValueError", _arc_eq)

def _arc_diff_r():
    try:
        _echantillonner_arc([0.5, 0, 0], [0, 0.3, 0], [0, 0, 0], 0.01)
        raise AssertionError("ValueError attendue (rayons différents)")
    except ValueError:
        pass
_run("Arc rayons différents → ValueError", _arc_diff_r)

def _arc_180():
    try:
        _echantillonner_arc([0.5, 0, 0], [-0.5, 0, 0], [0, 0, 0], 0.01)
        raise AssertionError("ValueError attendue (180°)")
    except ValueError:
        pass
_run("Arc 180° → ValueError", _arc_180)


# ============================================================
print("\n=== Section 3 : Module ML ===")
# ============================================================

modele = None
try:
    modele = charger_modele()
    print(f"  modèle : {type(modele).__name__} chargé")
except Exception as e:
    print(f"  modèle indisponible : {e}")

if modele is not None:
    for chemin_str in PIECES_REELLES:
        chemin = RACINE / chemin_str
        nom_piece = chemin.stem
        piece = charger_piece(chemin)
        traj_v1 = generer_trajectoire(piece)
        traj_v2 = generer_trajectoire_ml(piece, modele)

        def _same_len(t1=traj_v1, t2=traj_v2):
            assert len(t1) == len(t2), f"v1={len(t1)} vs v2={len(t2)}"
        _run(f"[{nom_piece}] v2 même longueur que v1", _same_len)

        def _same_pos(t1=traj_v1, t2=traj_v2):
            for i, (p1, p2) in enumerate(zip(t1, t2)):
                assert p1["pos"] == p2["pos"], f"position diff au point {i}: {p1['pos']} vs {p2['pos']}"
        _run(f"[{nom_piece}] v2 mêmes positions que v1", _same_pos)

        def _v_in_range(t=traj_v2):
            for i, p in enumerate(t):
                v = p["vitesse"]
                assert V_MIN <= v <= V_NOMINALE * 1.01, f"vitesse hors plage au point {i}: v={v} (V_MIN={V_MIN}, V_NOMINALE={V_NOMINALE})"
        _run(f"[{nom_piece}] v2 vitesses ∈ [V_MIN, V_NOMINALE]", _v_in_range)

        def _v_pos_v2(t=traj_v2):
            for i, p in enumerate(t):
                assert p["vitesse"] > 0
        _run(f"[{nom_piece}] v2 vitesse > 0 partout (G4)", _v_pos_v2)


    def _no_none_features():
        piece = charger_piece(RACINE / "data" / "piece.json")
        traj = generer_trajectoire(piece)
        features = extraire_features_trajectoire(traj, ferme=False)
        for i, feat in enumerate(features):
            for j, f in enumerate(feat):
                assert f is not None, f"BUG: feature[{i}][{j}] est None — invalide pour sklearn"
                assert isinstance(f, (int, float)), f"feature[{i}][{j}] pas numérique: {type(f).__name__}"
    _run("features (non-fermé) — aucune valeur None passée au modèle", _no_none_features)


    def _no_none_features_ferme():
        piece = charger_piece(RACINE / "data" / "piece_contour.json")
        traj = generer_trajectoire(piece)
        features = extraire_features_trajectoire(traj, ferme=True)
        for i, feat in enumerate(features):
            for j, f in enumerate(feat):
                assert f is not None, f"BUG: feature[{i}][{j}] est None (mode fermé)"
                assert isinstance(f, (int, float))
    _run("features (fermé) — aucune valeur None passée au modèle", _no_none_features_ferme)


    def _reproductible():
        piece = charger_piece(RACINE / "data" / "piece.json")
        t1 = generer_trajectoire_ml(piece, modele)
        t2 = generer_trajectoire_ml(piece, modele)
        for i, (a, b) in enumerate(zip(t1, t2)):
            assert a["vitesse"] == b["vitesse"], f"non-déterministe au point {i}"
    _run("Reproductibilité — deux predict consécutifs identiques", _reproductible)


    def _vitesse_experte_range():
        for angle in [0.0, 0.1, 0.5, 1.0, 1.5, math.pi]:
            for courbure in [0.0, 1.0, 5.0, 10.0, 50.0, 100.0]:
                for amax in [0.0, 0.5, 1.0, 1.5, math.pi]:
                    v = vitesse_experte(angle, courbure, amax)
                    assert V_MIN <= v <= V_NOMINALE, f"hors plage: v={v} pour ({angle},{courbure},{amax})"
    _run("vitesse_experte — toujours ∈ [V_MIN, V_NOMINALE]", _vitesse_experte_range)


    def _model_feature_count():
        # Le modèle attend exactement 3 features
        n_in = modele.n_features_in_
        assert n_in == 3, f"modèle attend {n_in} features, le code en extrait 3"
    _run("Modèle attend exactement 3 features", _model_feature_count)


# ============================================================
print("\n=== Section 4 : Fichiers, API, doc-code alignment ===")
# ============================================================

_run("contrat_trajectoire.md existe",
     lambda: (_ for _ in ()).throw(AssertionError("manquant")) if not (RACINE / "docs" / "contrat_trajectoire.md").exists() else None)

_run("data/modele_vitesse.joblib existe",
     lambda: (_ for _ in ()).throw(AssertionError("manquant")) if not (RACINE / "data" / "modele_vitesse.joblib").exists() else None)

_run("API publique ia_trajectoire : charger_piece, generer_trajectoire",
     lambda: __import__("ia_trajectoire").charger_piece and __import__("ia_trajectoire").generer_trajectoire)

_run("API publique ia_trajectoire_ml : charger_modele, generer_trajectoire_ml",
     lambda: __import__("ia_trajectoire_ml").charger_modele and __import__("ia_trajectoire_ml").generer_trajectoire_ml)


# ============================================================
# Synthèse
# ============================================================
print()
print("=" * 60)
print(f"Audit terminé : {len(PASSED)} OK / {len(FAILED)} FAIL")
print("=" * 60)

if FAILED:
    print("\nÉchecs détaillés :")
    for nom, msg in FAILED:
        print(f"  ✗ {nom}")
        print(f"      → {msg}")
    sys.exit(1)
else:
    print("\nTout est vert.")
    sys.exit(0)
