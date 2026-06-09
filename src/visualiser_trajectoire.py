"""Visualisation 3D de la trajectoire générée par `ia_trajectoire`.

Trace les points en 3D, colorés par vitesse, et sauvegarde la figure dans
`media/<id_piece>[_ml].png`. Sert à tester les modules IA SANS CoppeliaSim.

Lancement (depuis la racine du dépôt) :
    python src/visualiser_trajectoire.py                       # v1 règles, piece.json
    python src/visualiser_trajectoire.py data/piece_arc.json   # v1 règles, pièce passée
    python src/visualiser_trajectoire.py data/piece.json --ml  # v2 sklearn
"""
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from ia_trajectoire import charger_piece, generer_trajectoire


def main():
    args = [a for a in sys.argv[1:]]
    utiliser_ml = "--ml" in args
    args = [a for a in args if a != "--ml"]

    racine = Path(__file__).resolve().parents[1]
    chemin = Path(args[0]) if args else racine / "data" / "piece.json"
    if not chemin.is_absolute():
        chemin = racine / chemin

    piece = charger_piece(chemin)

    if utiliser_ml:
        from ia_trajectoire_ml import charger_modele, generer_trajectoire_ml
        modele = charger_modele()
        traj = generer_trajectoire_ml(piece, modele)
        suffixe_titre = " (v2 sklearn)"
        suffixe_fichier = "_ml"
    else:
        traj = generer_trajectoire(piece)
        suffixe_titre = " (v1 règles)"
        suffixe_fichier = ""

    xs = [p["pos"][0] for p in traj]
    ys = [p["pos"][1] for p in traj]
    zs = [p["pos"][2] for p in traj]
    vs = [p["vitesse"] for p in traj]

    if piece.get("ferme", False) and traj:
        xs.append(traj[0]["pos"][0])
        ys.append(traj[0]["pos"][1])
        zs.append(traj[0]["pos"][2])

    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(xs, ys, zs, color="lightgray", linewidth=1, zorder=1)
    sc = ax.scatter(xs[:len(vs)], ys[:len(vs)], zs[:len(vs)], c=vs, cmap="viridis", s=35, zorder=2)
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")
    ax.set_title(
        f"Trajectoire — {piece.get('description', '')}{suffixe_titre}\n"
        f"{len(traj)} points · couleur = vitesse (m/s)"
    )
    fig.colorbar(sc, ax=ax, shrink=0.7, label="vitesse (m/s)")

    media = racine / "media"
    media.mkdir(exist_ok=True)
    chemin_png = media / f"{piece.get('id', 'trajectoire')}{suffixe_fichier}.png"
    fig.savefig(chemin_png, dpi=120, bbox_inches="tight")
    print(f"Figure sauvegardée : {chemin_png}")

    if matplotlib.get_backend().lower() not in ("agg", "pdf", "ps", "svg"):
        plt.show()


if __name__ == "__main__":
    main()
