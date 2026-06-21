# Documentation de la scène CoppeliaSim SmartFactory

- **Module :** Ingénierie de simulation — fondation de scène
- **Auteur :** Delly Jean Jifferson
- **Équipe :** ARCMIND ROBOTICS — Groupe 1
- **Fichier :** smart_factory_scene.ttt
- **Version de CoppeliaSim :** 4.10.0 (compatible Edu / Pro)

## Contenu de la scène

Cette scène est la base de simulation de la cellule de soudage SmartFactory. Elle fournit l’environnement physique, le robot, le système IK et tous les objets nommés dont dépendent les autres modules. Rien d’autre ne fonctionne tant que cette scène n’est pas ouverte.

## Remarque sur le modèle de robot

La spécification du projet imposait l’**ABB IRB 1660ID**. Ce modèle n’est **pas disponible** dans la bibliothèque de modèles intégrée de CoppeliaSim 4.10.0. Après validation par l’équipe, l’**ABB IRB 140** a été retenu comme substitut approuvé. Les deux robots sont :

- 6 axes (6 DOF) : comportement IK identique
- charge utile de 6 kg : même classe physique
- commandés de la même manière via l’API distante ZMQ

La seule différence pratique concerne la portée (0,81 m contre 1,55 m), compensée en plaçant la table à X = 0,30 m au lieu de 0,50 m.

## Liste complète des objets

Voici les noms exacts à utiliser dans tout le code Python via `sim.getObject(...)`.

| Nom de l’objet | Type | Rôle |
| --- | --- | --- |
| `/ABB` | Modèle de robot | ABB IRB 140 — bras 6 axes |
| `/ABB/tip` | Dummy | Point central outil (TCP) — extrémité IK |
| `/ABB/target` | Dummy | Cible IK — Python la déplace pour piloter le robot |
| `/ABB/torch` | Forme cylindrique | Torche de soudage visuelle fixée au poignet |
| `/ABB/tip/weldTrail` | Dummy | Ancre de substitution pour l’objet de dessin du cordon |
| `/table` | Forme cuboïde | Surface de travail / positionneur |
| `/piece1` | Forme cuboïde | Première plaque métallique, position Y = -0,05 |
| `/piece2` | Forme cuboïde | Seconde plaque métallique, position Y = +0,05 |

Le cordon de soudure se situe entre `/piece1` et `/piece2`, avec un joint au centre sur Y = 0.

## Fonctionnement du système IK

La scène utilise le **générateur IK** intégré de CoppeliaSim (introduit en v4.4). Un script IK a été généré automatiquement et se trouve comme enfant de `/ABB` dans la hiérarchie.

Le lien est le suivant : `/ABB/tip (tip)` ↔ `/ABB/target (target)` avec le type **IK, tip-target**.

À l’exécution, pendant la simulation comme à l’arrêt, le robot résout en continu ses angles articulaires pour maintenir `/ABB/tip` aligné avec `/ABB/target`.

### Déplacement depuis Python

Pour piloter le robot depuis Python, déplacez uniquement la cible IK `/ABB/target`. Ne définissez jamais directement les positions articulaires.

## Démarrage rapide Python

Installer le client ZMQ (configuration initiale) :

```bash
pip install coppeliasim-zmqremoteapi-client
```

Connexion et récupération des objets de la scène :

```python
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

client = RemoteAPIClient()  # se connecte par défaut à localhost:23000
sim = client.require('sim')

# Récupération des objets de la scène
robot = sim.getObject('/ABB')
tip = sim.getObject('/ABB/tip')
target = sim.getObject('/ABB/target')  # c’est cet objet qu’il faut déplacer
torch = sim.getObject('/ABB/torch')
trail = sim.getObject('/ABB/tip/weldTrail')
table = sim.getObject('/table')
piece1 = sim.getObject('/piece1')
piece2 = sim.getObject('/piece2')
```

Déplacement du robot vers une position d’exemple :

```python
sim.startSimulation()

# Déplacer la cible au-dessus du joint de soudure
position = [0.30, 0.0, 0.178]  # X, Y, Z en mètres, repère monde
sim.setObjectPosition(target, -1, position)  # -1 = repère monde

# Le robot suivra automatiquement via l’IK
```

## Objet de dessin (cordon de soudure)

L’objet de dessin a été retiré du menu Add de CoppeliaSim 4.10.0. Il doit donc être créé à l’exécution depuis Python. Le dummy `/ABB/tip/weldTrail` présent dans la scène sert de point d’ancrage ; l’objet de dessin réel est instancié dans le code par le module de supervision qualité :

```python
trail_handle = sim.addDrawingObject(
    sim.drawing_lines,   # type de ligne
    0.005,               # largeur de ligne en mètres
    0,                   # réservé - laisser à 0
    -1,                  # nombre max de points (-1 = illimité)
    [1.0, 0.4, 0.0]      # couleur RGB - orange pour le cordon
)

# Ajouter un point au trajet au niveau courant de l’extrémité
tip_pos = sim.getObjectPosition(tip, -1)
sim.addDrawingObjectItem(trail_handle, tip_pos)
```

Appeler `addDrawingObjectItem` à chaque cycle de simulation pendant la soudure pour dessiner le cordon.

## Déroulement de la simulation

```mermaid
graph TD
    A[Ouvrir smart_factory_scene.ttt] --> B[Lancer la simulation (sim.startSimulation())]
    B --> C[Le module de trajectoire IA génère les positions cibles]
    C --> D[Python déplace /ABB/target pas à pas]
    D --> E[Le script IK déplace automatiquement les articulations du robot]
    E --> F[Le module qualité lit la position de /ABB/tip et dessine le cordon]
    F --> G[Le rapport de fin de cycle est généré]
    G --> H[sim.stopSimulation()]
```

## Objets statiques — dynamique désactivée

`/table`, `/piece1`, `/piece2` et `/ABB/torch` ont les options **Respondable** et **Dynamic** décochées dans leurs propriétés de corps. Cela signifie :

- Ils ne tombent pas et ne se déplacent pas sous l’effet de la physique
- Ils n’ont pas de masse et n’influencent pas le moteur physique
- Ils servent uniquement de repères visuels et de positionnement

Ne réactivez pas la dynamique sur ces objets.

## Notes importantes pour la v4.10.0

- L’**ancienne API distante** (port 19997, `simxStart`) est **abandonnée** depuis la v4.10. Utilisez uniquement l’API distante ZMQ.
- Le port ZMQ par défaut est **23000** (et non 19997).
- Le système IK utilise le nouvel **add-on IK generator**, pas l’ancienne interface Lua `simIK`.
- Les fichiers de scène `.ttt` sont **pleinement compatibles** entre Edu (Linux) et Pro (Windows) à version identique.

## Arborescence du dépôt

```text
smartfactory/
├── scenes/
│   └── smart_factory_scene.ttt    ← ce fichier (à ouvrir dans CoppeliaSim)
├── python/
│   ├── trajectory.py             ← module IA de trajectoire (équipier)
│   ├── controller.py             ← contrôleur ZMQ (équipier)
│   └── quality.py                ← supervision de soudure + cordon (équipier)
└── README_scene.md               ← ce fichier
```

## Dépannage

| Problème | Cause | Correctif |
| --- | --- | --- |
| `sim.getObject` renvoie -1 | Nom mal saisi ou mauvais chemin | Vérifier l’orthographe exacte, y compris `/` et la casse |
| Le robot ne suit pas la cible | IK non activé | Vérifier que le script IK est enfant de `/ABB` et que `Enabled` est coché |
| La torche se détache pendant la simulation | Dynamique activée sur la torche | Propriétés de l’objet → Body → décocher `Dynamic` et `Respondable` |
| Connexion refusée sur le port 23000 | CoppeliaSim n’est pas ouvert | Ouvrir d’abord la scène, puis lancer Python |
| La scène s’ouvre avec des erreurs sous Windows | Version différente | Vérifier que les deux machines utilisent exactement la v4.10.0 |
| La table bouge pendant la simulation | Dynamique activée sur la table | Même correctif que pour la torche |

## État du module 1

| Tâche | Statut |
| --- | --- |
| Scène créée, robot chargé | ✅ Terminé |
| IK configurée et testée | ✅ Terminé (confirmé par l'équipe) |
| Correction accessibilité (table et cible) | ✅ Terminé |
| Deux pièces à souder ajoutées | ✅ Terminé |
| Cordon de soudure (weldTrail placeholder) | ✅ Terminé |
| Scène poussée sur Git | ✅ Terminé |

## Historique des modifications

- v1.0 : Scène initiale — robot, table, pièce unique, IK configurée
- v1.1 : Correction accessibilité — table remontée à Z=0.13, rapprochée à X=0.30
- v1.2 : Deux pièces — `/piece` remplacée par `/piece1` et `/piece2` pour simuler un vrai assemblage de soudage
