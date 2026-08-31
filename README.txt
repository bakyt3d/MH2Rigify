MH2Rigify
A Blender addon that automates the tedious parts of converting a MetaHuman armature into a rig compatible with Rigify — cleaning up import junk, snapping joints into place, connecting bone chains, and aligning fingers — from a single sidebar panel instead of dozens of manual Ctrl+P / Shift+S steps.
Why
Bringing a MetaHuman skeleton into Blender gets you an armature, but not one Rigify (or a clean animation rig in general) is happy with out of the box: extra root empties, disconnected bone chains, joints that don't quite line up, and finger bones that need to be tapered and aligned by hand, one bone at a time. MH2Rigify turns that manual checklist into a set of one-click operators, grouped by stage, that can be run individually or as a full pipeline.
Requirements
Blender 5.2 or newer (uses the collapsible sub-panel API)
A MetaHuman armature already imported into the scene, with its standard bone naming (`hand_l`, `lowerarm_l`, `thumb_01_l`, `spine_01`, etc.)
Installation
Download `MH2Rigify.py` from this repo.
In Blender: Edit > Preferences > Add-ons > Install..., select the file.
Enable the addon in the list.
Open the 3D Viewport, press N to open the sidebar, and select the MH2Rigify tab.
Usage
All operators live in View3D > Sidebar > MH2Rigify, organized into four collapsible groups, each with its own "Run" button to execute every step in that group in order. A Run All (Full Pipeline) button at the top runs all four groups start to finish.
1. Cleanup & Setup
Prepares the imported rig: removes leftover empties and extra root armatures, reparents meshes to a single root, selects the bones Rigify actually needs, flags the armature to display In Front in the viewport, assigns the selected bones to a bone collection, then deletes everything that wasn't selected.
2. Align & Snap
Straightens out joint placement across the skeleton — feet, calves, thighs, pelvis, spine, and arm — snapping tails and heads together where MetaHuman's proportions leave a gap, and aligns the head bone to world up.
3. Finger Alignment
Straightens and tapers each finger chain (index, middle, ring, pinky, thumb) by snapping each segment's head to the previous segment's tail, blending the tip bone's direction toward parallel with its parent, and extending the tip along its own axis to a natural fingertip length. Runs for both sides in one click.
4. Bone Chains
Creates heel bones from the ball bones, connects the leg chain (ball → foot → calf → thigh) and the arm + finger chains with Connected parenting, and parents the heel and thighs with Keep Offset.
Notes
Every operator works on the first "root" armature it finds in the scene (or the active object, where relevant) and handles both `_l` and `_r` sides automatically.
Group-runner and pipeline buttons call each step's default settings — adjusting an individual operator's properties (visible in the redo panel after running it) changes what the group and pipeline buttons do too.
Steps that can't find their expected bones are skipped with a warning rather than stopping the whole run, so a partial or non-standard rig won't halt the pipeline.
