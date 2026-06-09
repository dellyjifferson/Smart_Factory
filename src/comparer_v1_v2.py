"""Comparaison visuelle v1 (règles) vs v2 (sklearn) sur une même pièce.

Génère un PNG avec deux sous-graphiques 3D côte à côte (même échelle de
couleur) pour montrer l'effet du modèle ML sur le profil de vitesse.

Lancement (depuis la racine du dépôt) :
    python src/comparer_v1_v2.py                       # piece.json par défaut
    python src/comparer_v1_v2.py data/piece_arc.json

Auteure : Saint-Vil Angie-Reyna Leddycia — Groupe 1 SmartFactory.
"""
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from ia_trajectoire import charger_piece, generer_trajectoire
from ia_trajectoire_ml import V_MIN, V_NOMINALE, charger_modele, generer_trajectoire_ml


def _tracer(ax, traj, titre, vmin, vmax):
    xs = [p["pos"][0] for p in traj]
    ys = [p["pos"][1] for p in traj]
    zs = [p["pos"][2] for p in traj]
    vs = [p["vitesse"] for p in traj]
    ax.plot(xs, ys, zs, color="lightgray", linewidth=1, zorder=1)
    sc = ax.scatter(xs, ys, zs, c=vs, cmap="viridis", s=30, vmin=vmin, vmax=vmax, zorder=2)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_title(titre, fontsize=10)
    return sc


def main():
    racine = Path(__file__).resolve().parents[1]
    chemin = Path(sys.argv[1]) if len(sys.argv) > 1 else racine / "data" / "piece.json"
    if not chemin.is_absolute():
        chemin = racine / chemin

    piece = charger_piece(chemin)
    modele = charger_modele()

    traj_v1 = generer_trajectoire(piece)
    traj_v2 = generer_trajectoire_ml(piece, modele)

    vmin = V_MIN
    vmax = V_NOMINALE

    fig = plt.figure(figsize=(14, 6))
    ax1 = fig.add_subplot(121, projection="3d")
    sc1 = _tracer(ax1, traj_v1, f"v1 règles — {len(traj_v1)} points", vmin, vmax)
    ax2 = fig.add_subplot(122, projection="3d")
    _tracer(ax2, traj_v2, f"v2 sklearn — {len(traj_v2)} points", vmin, vmax)

    fig.suptitle(f"Comparaison v1 vs v2 — {piece.get('description', '')}", fontsize=12)
    fig.colorbar(sc1, ax=[ax1, ax2], shrink=0.6, label="vitesse (m/s)")

    media = racine / "media"
    media.mkdir(exist_ok=True)
    chemin_png = media / f"{piece.get('id', 'comparaison')}_v1_vs_v2.png"
    fig.savefig(chemin_png, dpi=120, bbox_inches="tight")
    print(f"Figure sauvegardée : {chemin_png}")

    if matplotlib.get_backend().lower() not in ("agg", "pdf", "ps", "svg"):
        plt.show()


if __name__ == "__main__":
    main()
