**SmartFactory — CoppeliaSim Scene Documentation**  
**Module:** Simulation Engineering — Scene Foundation  
   
 **Author:** Delly Jean Jifferson  
   
 **Team:** ARCMIND ROBOTICS — Groupe 1  
   
 **File:** smart_factory_scene.ttt  
   
 **CoppeliaSim version:** 4.10.0 (Edu / Pro compatible)  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNBCkLfE07YGfHAiAU2QtIq6DIzW7UHAMBfnGt1V8fXEwAAXrse4eQF6VhvmPsAAAAASUVORK5CYII=)  
**What this scene contains**  
This is the base simulation scene for the SmartFactory welding cell. It provides the physical environment, the robot, the IK system, and all named objects that every other module depends on. Nothing else runs without this scene being open first.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OQQmAABRAsSdYxKa/jL0MIR7FCt5E2BJsmZmt2gMA4C+Otbqr8+sJAACvXQ85SAYUQNBTfQAAAABJRU5ErkJggg==)  
**Robot model note**  
The project specification calls for the **ABB IRB 1660ID**. This model is not available in the CoppeliaSim 4.10.0 built-in library. After team validation, the  **ABB IRB 140** was used as a substitute. Both robots are:  
- 6-axis (6 DOF) — IK behaviour is identical  
- 6 kg payload — same physical class  
- Controlled via the same ZMQ Remote API calls  
The only practical difference is reach (0.81 m vs 1.55 m), which is compensated by placing the table 0.35 m from the robot base instead of 0.5 m.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSNhYMEBIpD4ArCJDyywEZJWQZeZOaorAAD+4l6rrTq/ngAA8Nr+AEqmA1hl45m5AAAAAElFTkSuQmCC)  
**Complete object list**  
These are the **exact names** to use in all Python code via sim.getObject(...).  
| | | |  
|-|-|-|  
| **Object name** | **Type** | **Purpose** |   
| /ABB | Robot model | ABB IRB 140 — the 6-axis arm |   
| /ABB/tip | Dummy | Tool Center Point (TCP) — the IK tip |   
| /ABB/target | Dummy | IK target — Python moves this to drive the robot |   
| /ABB/torch | Cylinder shape | Visual welding torch attached to wrist |   
| /ABB/tip/weldTrail | Dummy | Placeholder for the weld bead drawing object |   
| /table | Cuboid shape | Work surface / positionneur |   
| /piece | Cuboid shape | The part being welded |   
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsScYxpg/jFnsYARvRrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA22QBcposvV4AAAAAElFTkSuQmCC)  
**How the IK system works**  
The scene uses CoppeliaSim's built-in **IK generator** (introduced in v4.4). An IK script was auto-generated and lives as a child of /ABB in the hierarchy.  
The link is:  
   
 /ABB/tip (tip) ↔ /ABB/target (target) with type **IK, tip-target**  
At runtime — both during simulation and when not simulating — the robot continuously solves joint angles to keep /ABB/tip aligned with /ABB/target.  
**To move the robot from Python:** only ever move /ABB/target. Never set joint positions directly.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNBCUrfD6LYGNDAgAU2QtIq6DIzW7UHAMBfHGt1V+fXEwAAXrseHDAF/orRG+cAAAAASUVORK5CYII=)  
**Python quick-start**  
Install the ZMQ client (one-time setup):  
pip install coppeliasim-zmqremoteapi-client  
   
Connect and get all object handles:  
from coppeliasim_zmqremoteapi_client import RemoteAPIClient  
   
 client = RemoteAPIClient()   # connects to localhost:23000 by default  
 sim = client.require('sim')  
   
 # Get handles to all scene objects  
 robot   = sim.getObject('/ABB')  
 tip     = sim.getObject('/ABB/tip')  
 target  = sim.getObject('/ABB/target')   # ← move this to drive the robot  
 torch   = sim.getObject('/ABB/torch')  
 trail   = sim.getObject('/ABB/tip/weldTrail')  
 table   = sim.getObject('/table')  
 piece   = sim.getObject('/piece')  
   
Move the robot to a position (example):  
sim.startSimulation()  
   
 # Move target to a position above the piece  
 position = [0.30, 0.0, 0.165]   # X, Y, Z in meters, world frame  
 sim.setObjectPosition(target, -1, position)  # -1 = world frame  
   
 # The robot will automatically follow via IK  
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OYQ1AABSAwc8mi5wvkwZyCKCAACr4Z7a7BLfMzFYdAQDwF+da3dX+9QQAgNeuB6feBdUJcyS2AAAAAElFTkSuQmCC)  
**Drawing object (weld bead trail)**  
The Drawing Object was removed from the CoppeliaSim 4.10.0 Add menu. It must be created at runtime from Python. The /ABB/tip/weldTrail dummy in the scene is a placeholder anchor — the actual drawing object is instantiated in code by the **Quality Monitoring module**:  
trail_handle = sim.addDrawingObject(  
     sim.drawing_lines,   # line type  
     0.005,               # line width in meters  
     0,                   # reserved — leave 0  
     -1,                  # max points (-1 = unlimited)  
     [1.0, 0.4, 0.0]     # RGB color — orange for weld bead  
 )  
   
 # Add a point to the trail at the current tip position  
 tip_pos = sim.getObjectPosition(tip, -1)  
 sim.addDrawingObjectItem(trail_handle, tip_pos)  
   
Call addDrawingObjectItem at each simulation step during welding to draw the bead.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OYQ1AABSAwY8JoIGqr4Z6Eoiggn9mu0twy8wc1RkAAH9xbdVa7V9PAAB47X4A9C4EIsmYmgsAAAAASUVORK5CYII=)  
**Simulation flow**  
Open smartfactory_scene.ttt  
         ↓  
 Start simulation (sim.startSimulation())  
         ↓  
 AI trajectory module generates target positions  
         ↓  
 Python moves /ABB/target step by step  
         ↓  
 IK script moves the robot joints automatically  
         ↓  
 Quality module reads /ABB/tip position → draws weld trail  
         ↓  
 End-of-cycle report generated  
         ↓  
 sim.stopSimulation()  
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsScYxpg/h5VMYARvRrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA224BcUMk6pDAAAAAElFTkSuQmCC)  
**Static objects — dynamics disabled**  
/table, /piece, and /ABB/torch all have **Respondable** and  **Dynamic** unchecked in their Body properties. This means:  
- They do not fall or move under physics  
- They have no mass and don't affect the physics engine  
- They are purely visual/positional references  
Do not re-enable dynamics on these objects.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNBCkLfE07YGfHAiAU2QtIq6DIzW7UHAMBfnGt1V8fXEwAAXrse4eQF6VhvmPsAAAAASUVORK5CYII=)  
**Important version notes for v4.10.0**  
- The **legacy remote API** (port 19997, simxStart) is  **discontinued** in v4.10. Use only the ZMQ Remote API.  
- Default ZMQ port is **23000** (not 19997).  
- The IK system uses the new **IK generator add-on**, not the old simIK Lua interface.  
- .ttt scene files are **fully compatible** between Edu (Linux) and Pro (Windows) on the same version.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OQQmAABRAsad4EEtY9QcxnUms4E2ELcGWmTmrKwAA/uLeqrU6vp4AAPDa/gDzXgM37EF77AAAAABJRU5ErkJggg==)  
**File layout in the repo**  
smartfactory/  
 ├── scenes/  
 │   └── smartfactory_scene.ttt    ← this file (open in CoppeliaSim)  
 ├── python/  
 │   ├── trajectory.py             ← AI trajectory module (teammate)  
 │   ├── controller.py             ← ZMQ controller (teammate)  
 │   └── quality.py                ← weld monitoring + trail (teammate)  
 └── README_scene.md               ← this file  
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OMQ2AABAAsSNhRAF6EPYDLhGADSywEZJWQZeZ2aszAAD+4l6rrTq+ngAA8Nr1AIWsBDYDm5cLAAAAAElFTkSuQmCC)  
**Troubleshooting**  
| | | |  
|-|-|-|  
| **Problem** | **Cause** | **Fix** |   
| sim.getObject returns -1 | Name typo or wrong path | Check exact spelling including / and case |   
| Robot doesn't follow target | IK not enabled | Confirm IK script is child of /ABB and Enabled is checked |   
| Torch detaches during simulation | Dynamics enabled on torch | Object Properties → Body → uncheck Dynamic + Respondable |   
| Connection refused on port 23000 | CoppeliaSim not open | Open the scene first, then run Python |   
| Scene opens with errors on Windows | Version mismatch | Confirm both machines run exactly v4.10.0 |   
| Table moves during simulation | Dynamics enabled on table | Same fix as torch above |   
   
