# diagnostic.py
from coppeliasim_zmqremoteapi_client import RemoteAPIClient
import time

client = RemoteAPIClient()
sim = client.require('sim')

tip    = sim.getObject('/ABB/tip')
piece1 = sim.getObject('/piece1')
target = sim.getObject('/ABB/target')

sim.startSimulation()

# Move target directly to first weld point
sim.setObjectPosition(target, -1, [0.28, 0.0, 0.200])
time.sleep(2)  # wait for IK to settle

tip_pos   = sim.getObjectPosition(tip, -1)
piece_pos = sim.getObjectPosition(piece1, -1)

print(f"Target Z        : 0.200")
print(f"Tip Z réel      : {tip_pos[2]:.6f}")
print(f"Tip X réel      : {tip_pos[0]:.6f}")
print(f"Tip Y réel      : {tip_pos[1]:.6f}")
print(f"Piece1 Z surface: {piece_pos[2] + 0.010:.6f}")
print(f"STANDOFF Z réel : {tip_pos[2] - (piece_pos[2] + 0.010):.6f}")

sim.stopSimulation()