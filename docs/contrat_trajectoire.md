# Contrat technique — Module IA / Trajectoire

> Document de cadrage entre les modules **IA / trajectoire** (Leddycia) et **Intégration / contrôle robot** (Louis).
> Sert aussi de référence pour le module **Qualité** (Raphaëlla) qui consomme la trajectoire comme position théorique.
>
> **Version 1** — basée sur le doc de répartition des tâches du formateur.

---

## 1. Format d'entrée — `piece.json`

Décrit la géométrie de la pièce à souder. Repère **monde CoppeliaSim**, unités **mètres**.

```json
{
  "id": "piece_demo_L_01",
  "description": "Cordon en L — pièce de démonstration",
  "joints": [
    { "type": "ligne", "debut": [0.5, 0.2, 0.8], "fin": [0.5, 0.4, 0.8] },
    { "type": "ligne", "debut": [0.5, 0.4, 0.8], "fin": [0.7, 0.4, 0.8] }
  ],
  "parametres": {
    "pas_mm": 10,
    "vitesse_nominale": 0.05,
    "vitesse_angle": 0.02,
    "seuil_angle_deg": 30
  },
  "ferme": false
}
```

### Champs racine

| Champ          | Type            | Obligatoire | Description                                                                 |
|----------------|-----------------|-------------|-----------------------------------------------------------------------------|
| `id`           | string          | oui         | Identifiant unique de la pièce.                                             |
| `description`  | string          | non         | Libellé humain.                                                             |
| `joints`       | list[object]    | oui         | Segments à souder, dans l'ordre d'exécution. Voir [types de joints](#types-de-joints). |
| `parametres`   | object          | oui         | Paramètres de génération. Voir [paramètres](#paramètres).                    |
| `ferme`        | bool            | non (déf. `false`) | Si `true`, la trajectoire est traitée comme un contour fermé : l'analyse d'angles boucle (le dernier point ralentit avec le premier), et le doublon de fermeture est retiré. |

### Types de joints

#### `"type": "ligne"`

Segment droit entre deux points.

| Champ    | Type            | Description                            |
|----------|-----------------|----------------------------------------|
| `debut`  | list[float, 3]  | Position de départ `[x, y, z]` (m).    |
| `fin`    | list[float, 3]  | Position d'arrivée `[x, y, z]` (m).    |

#### `"type": "arc"`

**Plus court arc** entre `debut` et `fin`, centré sur `centre`. Le plan de l'arc est défini par les trois points.

| Champ    | Type            | Description                                              |
|----------|-----------------|----------------------------------------------------------|
| `debut`  | list[float, 3]  | Point de départ de l'arc (m). Doit être à distance `r` de `centre`. |
| `fin`    | list[float, 3]  | Point d'arrivée de l'arc (m). Doit aussi être à distance `r` de `centre`. |
| `centre` | list[float, 3]  | Centre du cercle qui porte l'arc (m).                    |

Cas dégénérés (lèvent `ValueError`) : `debut == fin`, distances `debut/centre` et `fin/centre` différentes (> 0.1 mm), ou `debut` et `fin` diamétralement opposés (angle 180° → plan ambigu, à découper en deux arcs).

### Paramètres

| Champ                          | Type            | Description                                                                 |
|--------------------------------|-----------------|-----------------------------------------------------------------------------|
| `parametres.pas_mm`            | int             | Espacement entre points de la trajectoire (en mm).                          |
| `parametres.vitesse_nominale`  | float           | Vitesse sur les segments droits (m/s).                                      |
| `parametres.vitesse_angle`     | float           | Vitesse réduite aux changements de cap (m/s).                               |
| `parametres.seuil_angle_deg`   | float           | Angle (degrés) au-delà duquel on ralentit. Défaut : 30°.                    |

---

## 2. Format de sortie — la trajectoire

C'est l'objet qui circule entre les modules. **À ne pas modifier sans accord d'équipe.**

```python
trajectoire = [
    {"pos": [0.500, 0.200, 0.800], "vitesse": 0.05},
    {"pos": [0.500, 0.210, 0.800], "vitesse": 0.05},
    ...
    {"pos": [0.500, 0.390, 0.800], "vitesse": 0.02},  # ralenti dans l'angle
    {"pos": [0.500, 0.400, 0.800], "vitesse": 0.02},
    ...
]
```

### Sémantique

- `pos` : `list[float]` à 3 éléments — `[x, y, z]` en mètres, repère **monde CoppeliaSim**.
- `vitesse` : `float` positif — m/s. Vitesse du segment qui mène à ce point.
- L'**ordre** de la liste = l'ordre d'exécution.

### Garanties fournies par `generer_trajectoire`

1. `len(trajectoire) >= 2`.
2. Pas de doublons consécutifs : `traj[i]["pos"] != traj[i+1]["pos"]`.
3. Espacement ≈ `pas_mm` entre deux points consécutifs (à `±` un pas d'échantillonnage).
4. `vitesse > 0` pour tout point.
5. Les angles internes au cordon (> `seuil_angle_deg`) déclenchent un ralentissement automatique sur 3 points consécutifs autour de l'angle.
6. Si `ferme=true`, l'analyse d'angles boucle (le point 0 ralentit si la jonction avec le dernier point forme un angle), et le doublon final éventuel est retiré.

---

## 3. API publique du module

```python
from ia_trajectoire import charger_piece, generer_trajectoire

piece = charger_piece("data/piece.json")
trajectoire = generer_trajectoire(piece)
# trajectoire est prête à être passée à suivre_trajectoire()
```

| Fonction                          | Signature                              | Rôle                                                    |
|-----------------------------------|----------------------------------------|---------------------------------------------------------|
| `charger_piece(chemin)`           | `(str | Path) -> dict`                 | Lit le fichier JSON et renvoie le dict de la pièce.     |
| `generer_trajectoire(piece_data)` | `(dict) -> list[dict]`                 | Produit la trajectoire au format ci-dessus.             |

---

## 4. Côté Louis — ce qui est attendu

`suivre_trajectoire(trajectoire)` doit :

1. Itérer sur la liste dans l'ordre.
2. Pour chaque point `i` : déplacer le `target` IK à `trajectoire[i]["pos"]` à la vitesse `trajectoire[i]["vitesse"]`.
3. Attendre la stabilisation (ou utiliser un sleep proportionnel à la distance / vitesse) avant le point suivant.
4. Ne **pas** gérer le retour HOME ici — c'est le cycle complet (`main.py`) qui s'en charge.

Exemple consommateur (côté Louis) :

```python
from ia_trajectoire import charger_piece, generer_trajectoire
import robot_control

piece = charger_piece("data/piece.json")
traj = generer_trajectoire(piece)

robot_control.aller_a_home()
robot_control.suivre_trajectoire(traj)
robot_control.aller_a_home()
```

---

## 5. Côté Raphaëlla — ce qui est attendu

`verifier(pos_reelle, pos_theorique, seuil)` :

- `pos_theorique` = `trajectoire[i]["pos"]` (référence générée par l'IA).
- `pos_reelle` = position lue dans CoppeliaSim au même pas.
- Retourne `"OK"` si `distance(pos_reelle, pos_theorique) < seuil`, sinon `"ANOMALIE"`.

---

## 6. Points ouverts à valider en équipe

- [ ] **Unité de la vitesse** — m/s confirmé ? (l'API ZMQ travaille parfois en pas-par-pas plutôt qu'en m/s — à clarifier par Louis).
- [ ] **Repère** — `pos` exprimées dans le repère monde de CoppeliaSim, ou dans un repère pièce attaché à la table ? À fixer avec Delly une fois la scène prête.
- [ ] **Approach point** — faut-il un point de pré-positionnement (~5 cm au-dessus du 1er point) pour amener la torche en douceur ? À discuter avec Louis.
- [ ] **Seuil d'anomalie** (`seuil` dans `verifier`) — à fixer avec Raphaëlla, ordre de grandeur 1 à 2 mm probablement.
- [ ] **Comportement sur type de joint inconnu** — actuellement le module skip silencieusement. OK ou faut-il lever une exception ?
- [ ] **Pas de soudure (`pas_mm`)** — 10 mm choisi en v1, à valider par rapport à la précision attendue.

---

## 7. Version 2 — IA scikit-learn

Module séparé `ia_trajectoire_ml.py` qui produit **le même format de sortie**
que la v1, mais ajuste les vitesses via un modèle ML.

### API publique

```python
from ia_trajectoire_ml import charger_modele, generer_trajectoire_ml

modele = charger_modele()                          # data/modele_vitesse.joblib
traj = generer_trajectoire_ml(piece_data, modele)  # même format que v1
```

### Features utilisées

Pour chaque point i de la trajectoire :

| Feature              | Description                                                            |
|----------------------|------------------------------------------------------------------------|
| `angle_local`        | Angle interne (rad) entre (i-1, i, i+1). 0 = ligne droite.             |
| `courbure_locale`    | 1 / rayon du cercle circonscrit aux 3 points. ≈ 0 sur une ligne droite. |
| `angle_max_fenetre`  | Angle interne max sur la fenêtre `i ± 2`. Permet d'**anticiper** un coin proche. |

### Modèle

- `sklearn.ensemble.RandomForestRegressor` (80 arbres, profondeur max 10).
- Entraîné sur ~2 250 points issus de 52 pièces synthétiques (lignes, L à angles divers, arcs de rayons divers, contours rectangulaires).
- Cible : `vitesse_experte(angle_local, courbure_locale, angle_max_fenetre)` — fonction non-linéaire qui réduit la vitesse de façon **progressive** (vs. binaire en v1).
- Fichier : `data/modele_vitesse.joblib` (~144 Ko, versionné).

### Métriques obtenues

| Métrique | Valeur       | Interprétation |
|----------|--------------|----------------|
| R²       | **0.9922**   | Le modèle explique 99.2 % de la variance des vitesses cibles. |
| MAE      | **9×10⁻⁵ m/s** | Erreur moyenne absolue négligeable (~0.2 % de la vitesse nominale). |

### Importance des features (apprise par le modèle)

| Feature              | Importance | Interprétation |
|----------------------|------------|----------------|
| `angle_max_fenetre`  | **81.4 %** | Le modèle valorise l'**anticipation** (regarder ±2 points autour). |
| `angle_local`        | 11.0 %     | L'angle au point lui-même. |
| `courbure_locale`    | 7.5 %      | Permet de détecter les arcs serrés (que v1 ignore). |

### Effet observé sur les pièces de test (chiffres mesurés)

| Pièce                              | v1 (règles)                  | v2 (sklearn)                                                   |
|------------------------------------|------------------------------|----------------------------------------------------------------|
| `piece.json` (cordon en L, 90°)    | 3 points ralentis            | **5 points** (transition douce autour du coude)                |
| `piece_contour.json` (rectangle 4×90°) | 12 points (3 par coin)   | **20 points** (5 par coin)                                     |
| `piece_arc.json` (arc r=20 cm)     | Vitesse constante            | Vitesse constante (équivalent — arc large = pas de ralentissement) |
| `piece_mixte.json` (ligne + arc r=10 cm + ligne) | Vitesse constante | **17 points ralentis** sur l'arc serré (la v1 ne le voit pas)   |
| `piece_angle_vif.json` (jonction non tangente + arc r=7,5 cm) | 3 points | **19 points** (combine jonction + courbure)                    |

Insight clé pour l'oral : **la v2 capture deux comportements que la v1 ignore** :
1. transition progressive autour des coins (au lieu d'un saut binaire),
2. ralentissement sur les **arcs serrés** (rayon < 20 cm) grâce à la feature `courbure_locale`.

### Ré-entraînement

```bash
python src/entrainement_modele.py
```

Génère le dataset synthétique, entraîne le modèle et écrase
`data/modele_vitesse.joblib`. Reproductible (`random_state=42`).

---

## 8. Versions futures

- Validation : ajout d'une fonction `valider_trajectoire(traj)` levant une exception en cas de violation des garanties.
- Support du sens « long » sur les arcs (actuellement seul le plus court arc est supporté).
- Support des cercles complets (à découper en deux arcs pour l'instant).
- v2 ML entraînée sur **vraies données** (mesures de qualité de Raphaëlla) plutôt que sur la fonction expert synthétique.
