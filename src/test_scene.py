# test_scene.py — test your scene independently
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
import time

client = RemoteAPIClient()
sim = client.require('sim')

# Verify all your objects are found
objects = {
    'robot':  '/ABB',
    'tip':    '/ABB/tip',
    'target': '/ABB/target',        # adjust if /ABB/target
    'torch':  '/ABB/torch',
    'table':  '/table',
    'piece':  '/piece',
    'trail':  '/ABB/tip/weldTrail'
}

print("=== Vérification des objets ===")
all_ok = True
for name, path in objects.items():
    try:
        handle = sim.getObject(path)
        print(f"  ✅ {name} ({path}) → handle {handle}")
    except Exception:
        print(f"  ❌ {name} ({path}) → INTROUVABLE")
        all_ok = False

if all_ok:
    print("\nTous les objets sont trouvés — scène OK ✅")
else:
    print("\nCertains objets manquent — vérifier les noms dans la scène ⚠️")

# Quick movement test
print("\n=== Test mouvement ===")
sim.startSimulation()
target = sim.getObject('/ABB/target')

positions = [
    [0.30,  0.04, 0.178],
    [0.30,  0.00, 0.178],
    [0.30, -0.04, 0.178],
]

for i, pos in enumerate(positions):
    sim.setObjectPosition(target, -1, pos)
    time.sleep(0.5)
    real = sim.getObjectPosition(sim.getObject('/ABB/tip'), -1)
    print(f"  Point {i+1} → tip à {[round(v,4) for v in real]}")

sim.stopSimulation()
print("\nTest terminé ✅")