"""main.py — Orchestrateur SmartFactory (Module integration).

Branche les trois modules de l'equipe :
  IA (Angie)         : genere la trajectoire de soudage
  Robot (Louis)      : la fait executer par le robot ABB
  Qualite (Raphaella): verifie chaque point, trace le cordon, edite le rapport
"""
import time

from ia_trajectoire import charger_piece, generer_trajectoire
from robot_control import RobotControl
import detection_anomalies as qualite

SEUIL = 0.012   # ecart max tolere position reelle / theorique (12 mm)


def main():
    # 1. IA : charger la piece et generer la trajectoire
    piece = charger_piece("data/piece.json")
    trajectoire = generer_trajectoire(piece)
    print(f"IA : {len(trajectoire)} points de soudage generes.\n")

    # 2. Robot : connexion + preparation
    robot = RobotControl()
    sim = robot.sim
    robot.demarrer()

    # Objet de dessin pour le cordon (points rouges)
    cordon = sim.addDrawingObject(sim.drawing_spherepoints, 0.004, 0.0, -1, 10000, [1, 0, 0])

    # HOME : 8 cm au-dessus du 1er point
    p0 = trajectoire[0]["pos"]
    home = [p0[0], p0[1], p0[2] + 0.08]
    print("Deplacement vers HOME...")
    robot.aller_a(home, 0.10)

    # 3. Cycle de soudage
    positions_reelles = []
    print("Soudage en cours...\n")
    for i, point in enumerate(trajectoire):
        robot.aller_a(point["pos"], point["vitesse"])
        time.sleep(0.15)                       # laisser le bras se stabiliser
        reelle = robot.position_tip()
        positions_reelles.append(reelle)

        statut = qualite.verifier(reelle, point["pos"], SEUIL)
        qualite.afficher_statut_coppeliasim(sim, statut)
        qualite.tracer_point_cordon(sim, cordon, reelle)
        print(f"  point {i+1}/{len(trajectoire)} : {statut}")

    # 4. Retour HOME
    print("\nRetour HOME...")
    robot.aller_a(home, 0.10)
    robot.arreter()

    # 5. Rapport qualite final
    rapport = qualite.analyser_cycle(positions_reelles, trajectoire, SEUIL)
    qualite.afficher_rapport(rapport)
    qualite.exporter_rapport(rapport, "rapport_qualite.json")


if __name__ == "__main__":
    main()