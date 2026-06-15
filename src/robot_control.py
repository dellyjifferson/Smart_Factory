"""Module 2 — Integration / controle robot (SmartFactory, Groupe 1).

Pilote le robot ABB de la scene via la cible de cinematique inverse
'/ABB/target', depuis Python (ZMQ Remote API). Consomme le contrat
commun de l'equipe :

    trajectoire = [{"pos": [x, y, z], "vitesse": v}, ...]

Auteur : Louis Dulze Hkloe Sassie Shaikelta.
"""
import time
import math
from coppeliasim_zmqremoteapi_client import RemoteAPIClient


class RobotControl:
    def __init__(self):
        self.client = RemoteAPIClient()
        self.sim = self.client.require('sim')
        self.target = self.sim.getObject('/ABB/target')
        self.tip = self._trouver_tip()

    def _trouver_tip(self):
        """Retrouve le dummy 'tip' sans coder son chemin complet."""
        for h in self.sim.getObjectsInTree(self.sim.handle_scene,
                                           self.sim.object_dummy_type, 0):
            if self.sim.getObjectAlias(h, -1) == 'tip':
                return h
        return None

    def position_tip(self):
        """Position reelle du bout de l'outil (repere monde)."""
        return self.sim.getObjectPosition(self.tip)

    def aller_a(self, point, vitesse=0.05):
        """Deplace la cible vers 'point' [x, y, z] a 'vitesse' (m/s).

        La duree d'attente est calculee a partir de la distance a parcourir,
        pour respecter approximativement la vitesse demandee.
        """
        depart = self.sim.getObjectPosition(self.target)
        distance = math.dist(depart, point)
        duree = distance / vitesse if vitesse > 0 else 0.0
        # ordre 4.10 : (handle, position)
        self.sim.setObjectPosition(self.target, point)
        time.sleep(max(duree, 0.05))

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


# --- Test autonome : petite trajectoire SURE, dans la zone atteignable ---
if __name__ == "__main__":
    robot = RobotControl()
    robot.demarrer()

    base = robot.position_tip()          # la ou le bras est = forcement atteignable
    print("Zone de test (tip actuel) :", [round(v, 3) for v in base])

    home = [base[0], base[1], base[2] + 0.05]   # HOME de test : 5 cm au-dessus

    # Mini-trajectoire : une ligne en Y (axe libre), +/- 4 cm
    traj = [
        {"pos": [base[0], base[1] - 0.04, base[2]], "vitesse": 0.03},
        {"pos": [base[0], base[1] - 0.02, base[2]], "vitesse": 0.03},
        {"pos": [base[0], base[1] + 0.00, base[2]], "vitesse": 0.03},
        {"pos": [base[0], base[1] + 0.02, base[2]], "vitesse": 0.03},
        {"pos": [base[0], base[1] + 0.04, base[2]], "vitesse": 0.03},
    ]

    print("Depart HOME...")
    robot.aller_a(home, 0.1)
    print("Suivi de la trajectoire de test...")
    robot.suivre_trajectoire(traj)
    print("Retour HOME...")
    robot.aller_a(home, 0.1)

    robot.arreter()
    print("Termine : robot_control teste sur le vrai robot.")
