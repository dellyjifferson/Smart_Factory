"""Module 2 — Intégration / contrôle robot (SmartFactory, Groupe 1).
Pilote le robot ABB de la scène via la cible de cinématique inverse
'/ABB/target', depuis Python (ZMQ Remote API). Consomme le contrat
commun de l'équipe :
    trajectoire = [{"pos": [x, y, z], "vitesse": v}, ...]
Auteur : Louis Dulze Hkloe Sassie Shaikelta.
"""
import time
import math
from coppeliasim_zmqremoteapi_client import RemoteAPIClient


class RobotControl:

    HOME = [0.280, 0.000, 0.360]  # position de repos sauvegardée dans la scène

    def __init__(self):
        self.client = RemoteAPIClient()
        self.sim    = self.client.require('sim')
        self.target = self.sim.getObject('/ABB/target')
        self.tip    = self._trouver_tip()

    def _trouver_tip(self):
        """Retrouve le dummy 'tip' sans coder son chemin complet."""
        for h in self.sim.getObjectsInTree(self.sim.handle_scene,
                                            self.sim.object_dummy_type, 0):
            if self.sim.getObjectAlias(h, -1) == 'tip':
                return h
        return None

    def position_tip(self):
        """Position réelle du bout de l'outil (repère monde)."""
        return self.sim.getObjectPosition(self.tip)

    def aller_a(self, point, vitesse=0.05):
        """Déplace la cible vers 'point' [x, y, z] à 'vitesse' (m/s)
        avec interpolation linéaire pour un mouvement fluide.
        """
        depart   = self.sim.getObjectPosition(self.target)
        distance = math.dist(depart, point)

        if distance < 0.001:  # déjà sur place
            return

        duree  = distance / vitesse if vitesse > 0 else 0.0

        # 1 pas tous les 2 mm, minimum 10 pas
        NB_PAS = max(int(distance / 0.002), 10)

        for i in range(1, NB_PAS + 1):
            t = i / NB_PAS  # progression 0.0 → 1.0
            pos_intermediaire = [
                depart[0] + t * (point[0] - depart[0]),
                depart[1] + t * (point[1] - depart[1]),
                depart[2] + t * (point[2] - depart[2]),
            ]
            self.sim.setObjectPosition(self.target, pos_intermediaire)
            time.sleep(duree / NB_PAS)

    def aller_home(self, vitesse=0.08):
        """Retour à la position HOME avec mouvement fluide."""
        print("  → Retour HOME...")
        self.aller_a(self.HOME, vitesse)

    def suivre_trajectoire(self, trajectoire):
        """Parcourt une liste de points au format du contrat commun."""
        n = len(trajectoire)
        for i, p in enumerate(trajectoire):
            print(f"  point {i+1}/{n} -> {[round(v, 3) for v in p['pos']]}"
                  f"  (v={p.get('vitesse', 0.05)} m/s)")
            self.aller_a(p["pos"], p.get("vitesse", 0.05))

    def demarrer(self):
        self.sim.startSimulation()
        time.sleep(1.0)

    def arreter(self):
        self.sim.stopSimulation()


# --- Test autonome : petite trajectoire SÛRE, dans la zone atteignable ---
if __name__ == "__main__":
    robot = RobotControl()
    robot.demarrer()

    base = robot.position_tip()
    print("Zone de test (tip actuel) :", [round(v, 3) for v in base])

    # Mini-trajectoire : une ligne en Y (axe libre), +/- 4 cm
    traj = [
        {"pos": [base[0], base[1] - 0.04, base[2]], "vitesse": 0.03},
        {"pos": [base[0], base[1] - 0.02, base[2]], "vitesse": 0.03},
        {"pos": [base[0], base[1] + 0.00, base[2]], "vitesse": 0.03},
        {"pos": [base[0], base[1] + 0.02, base[2]], "vitesse": 0.03},
        {"pos": [base[0], base[1] + 0.04, base[2]], "vitesse": 0.03},
    ]

    print("Départ HOME...")
    robot.aller_home()

    print("Suivi de la trajectoire de test...")
    robot.suivre_trajectoire(traj)

    print("Retour HOME...")
    robot.aller_home()

    robot.arreter()
    print("Terminé : robot_control testé sur le vrai robot.")