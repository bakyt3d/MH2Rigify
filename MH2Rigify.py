bl_info = {
    "name": "MH2Rigify",
    "author": "You",
    "version": (0, 1, 0),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > MH2Rigify",
    "description": "Utilities for converting MetaHuman armatures to Rigify-compatible rigs",
    "category": "Object",
}

import re
import bpy
from mathutils import Vector

# Matches: root, root.001, root.002, ... (case-insensitive, optional numeric suffix)
ROOT_NAME_PATTERN = re.compile(r"^root(\.\d+)?$", re.IGNORECASE)


def find_root_armatures(context):
    """Return all Armature objects in the current scene whose name matches
    'root', 'root.001', 'root.002', etc."""
    return [
        obj for obj in context.scene.objects
        if obj.type == 'ARMATURE' and ROOT_NAME_PATTERN.match(obj.name)
    ]


class ROOTTOOLS_OT_unparent_roots(bpy.types.Operator):
    """Select all armatures named root, root.001, root.002... and clear their parent"""
    bl_idname = "roottools.unparent_roots"
    bl_label = "Unparent Root Armatures"
    bl_options = {'REGISTER', 'UNDO'}

    keep_transform: bpy.props.BoolProperty(
        name="Keep Transform",
        description="Clear parent but keep the object's current world-space transform",
        default=True,
    )

    def execute(self, context):
        targets = find_root_armatures(context)

        if not targets:
            self.report({'WARNING'}, "No armatures matching 'root', 'root.001', ... found")
            return {'CANCELLED'}

        # Deselect everything first, then select only our targets
        bpy.ops.object.select_all(action='DESELECT')
        for obj in targets:
            obj.select_set(True)
        context.view_layer.objects.active = targets[0]

        # Clear parent (respecting the keep_transform toggle)
        clear_type = 'CLEAR_KEEP_TRANSFORM' if self.keep_transform else 'CLEAR'
        bpy.ops.object.parent_clear(type=clear_type)

        names = ", ".join(o.name for o in targets)
        self.report({'INFO'}, f"Unparented {len(targets)} armature(s): {names}")
        return {'FINISHED'}


class ROOTTOOLS_OT_delete_empties(bpy.types.Operator):
    """Select all Empty objects in the scene and delete them"""
    bl_idname = "roottools.delete_empties"
    bl_label = "Select & Delete All Empties"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        targets = [obj for obj in context.scene.objects if obj.type == 'EMPTY']

        if not targets:
            self.report({'WARNING'}, "No empties found")
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')
        for obj in targets:
            obj.select_set(True)
        context.view_layer.objects.active = targets[0]

        count = len(targets)
        bpy.ops.object.delete()

        self.report({'INFO'}, f"Deleted {count} empt{'y' if count == 1 else 'ies'}")
        return {'FINISHED'}


class ROOTTOOLS_OT_unparent_meshes(bpy.types.Operator):
    """Select all Mesh objects in the scene and clear their parent"""
    bl_idname = "roottools.unparent_meshes"
    bl_label = "Unparent All Meshes"
    bl_options = {'REGISTER', 'UNDO'}

    keep_transform: bpy.props.BoolProperty(
        name="Keep Transform",
        description="Clear parent but keep the object's current world-space transform",
        default=True,
    )

    def execute(self, context):
        targets = [obj for obj in context.scene.objects if obj.type == 'MESH']

        if not targets:
            self.report({'WARNING'}, "No mesh objects found")
            return {'CANCELLED'}

        bpy.ops.object.select_all(action='DESELECT')
        for obj in targets:
            obj.select_set(True)
        context.view_layer.objects.active = targets[0]

        clear_type = 'CLEAR_KEEP_TRANSFORM' if self.keep_transform else 'CLEAR'
        bpy.ops.object.parent_clear(type=clear_type)

        self.report({'INFO'}, f"Unparented {len(targets)} mesh(es)")
        return {'FINISHED'}


class ROOTTOOLS_OT_delete_extra_roots(bpy.types.Operator):
    """Keep the first root armature (alphabetically) and delete the rest"""
    bl_idname = "roottools.delete_extra_roots"
    bl_label = "Delete All But First Root Armature"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        targets = find_root_armatures(context)

        if not targets:
            self.report({'WARNING'}, "No armatures matching 'root', 'root.001', ... found")
            return {'CANCELLED'}

        if len(targets) == 1:
            self.report({'INFO'}, "Only one root armature found, nothing to delete")
            return {'CANCELLED'}

        # Sort so "root" comes before "root.001", "root.002", etc.
        targets.sort(key=lambda o: o.name)
        keep = targets[0]
        to_delete = targets[1:]

        bpy.ops.object.select_all(action='DESELECT')
        for obj in to_delete:
            obj.select_set(True)
        context.view_layer.objects.active = to_delete[0]

        count = len(to_delete)
        bpy.ops.object.delete()

        self.report({'INFO'}, f"Kept '{keep.name}', deleted {count} other root armature(s)")
        return {'FINISHED'}


class ROOTTOOLS_OT_parent_meshes_to_root(bpy.types.Operator):
    """Select all meshes, then the root armature, and parent with Empty Groups (Ctrl+P)"""
    bl_idname = "roottools.parent_meshes_to_root"
    bl_label = "Parent Meshes to Root (Empty Groups)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        meshes = [obj for obj in context.scene.objects if obj.type == 'MESH']
        armatures = find_root_armatures(context)

        if not meshes:
            self.report({'WARNING'}, "No mesh objects found")
            return {'CANCELLED'}
        if not armatures:
            self.report({'WARNING'}, "No root armature found")
            return {'CANCELLED'}

        armature = armatures[0]

        bpy.ops.object.select_all(action='DESELECT')
        for obj in meshes:
            obj.select_set(True)
        # Armature must be selected last so it becomes the active object
        armature.select_set(True)
        context.view_layer.objects.active = armature

        bpy.ops.object.parent_set(type='ARMATURE_NAME')

        self.report({'INFO'}, f"Parented {len(meshes)} mesh(es) to '{armature.name}' (Empty Groups)")
        return {'FINISHED'}


def build_main_bone_names():
    """Build the full list of main bone names, expanding left/right pairs."""
    names = [
        # 1. Root & Torso (The Core Chain)
        "pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05",
        "neck_01", "neck_02", "head",
    ]

    sided_singles = [
        # 2. Upper Body & Arms
        "clavicle", "upperarm", "lowerarm", "hand",
        # 3. Lower Body & Legs
        "thigh", "calf", "foot", "ball",
    ]

    finger_chains = [
        ["thumb_01", "thumb_02", "thumb_03"],
        ["index_metacarpal", "index_01", "index_02", "index_03"],
        ["middle_metacarpal", "middle_01", "middle_02", "middle_03"],
        ["ring_metacarpal", "ring_01", "ring_02", "ring_03"],
        ["pinky_metacarpal", "pinky_01", "pinky_02", "pinky_03"],
    ]

    for side in ("l", "r"):
        for base in sided_singles:
            names.append(f"{base}_{side}")
        for chain in finger_chains:
            for base in chain:
                names.append(f"{base}_{side}")

    return names


MAIN_BONE_NAMES = build_main_bone_names()


class ROOTTOOLS_OT_select_main_bones(bpy.types.Operator):
    """Enter Edit Mode on the root armature and select the main bone chain"""
    bl_idname = "roottools.select_main_bones"
    bl_label = "Edit Mode: Select Main Bones"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armatures = find_root_armatures(context)
        if not armatures:
            self.report({'WARNING'}, "No root armature found")
            return {'CANCELLED'}

        armature = armatures[0]

        # Make sure we're in Object Mode first so mode_set behaves predictably
        if context.object is not None and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.select_all(action='DESELECT')
        armature.select_set(True)
        context.view_layer.objects.active = armature

        bpy.ops.object.mode_set(mode='EDIT')

        edit_bones = armature.data.edit_bones
        for bone in edit_bones:
            bone.select = False
            bone.select_head = False
            bone.select_tail = False

        found = 0
        missing = []
        last_bone = None
        for name in MAIN_BONE_NAMES:
            bone = edit_bones.get(name)
            if bone is None:
                missing.append(name)
                continue
            bone.select = True
            bone.select_head = True
            bone.select_tail = True
            found += 1
            last_bone = bone

        if last_bone is not None:
            edit_bones.active = last_bone

        if missing:
            preview = ", ".join(missing[:6])
            more = f" (+{len(missing) - 6} more)" if len(missing) > 6 else ""
            self.report({'WARNING'}, f"Selected {found} bone(s). Missing: {preview}{more}")
        else:
            self.report({'INFO'}, f"Selected {found} main bone(s) in '{armature.name}'")

        return {'FINISHED'}


class ROOTTOOLS_OT_show_armature_in_front(bpy.types.Operator):
    """Switch the Properties editor to the Object tab and enable
    Viewport Display > In Front on the root armature"""
    bl_idname = "roottools.show_armature_in_front"
    bl_label = "Object Properties: Viewport Display > In Front"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object if (context.object is not None and context.object.type == 'ARMATURE') else None

        if obj is None:
            armatures = find_root_armatures(context)
            if not armatures:
                self.report({'WARNING'}, "No root armature found")
                return {'CANCELLED'}
            obj = armatures[0]

        obj.show_in_front = True

        # Best effort: point any visible Properties editor at the Object tab,
        # mirroring "go to Object Properties" in the UI
        screen = getattr(context, "screen", None)
        if screen is not None:
            for area in screen.areas:
                if area.type == 'PROPERTIES':
                    for space in area.spaces:
                        if space.type == 'PROPERTIES':
                            space.context = 'OBJECT'

        self.report({'INFO'}, f"Enabled Viewport Display > In Front on '{obj.name}'")
        return {'FINISHED'}


class ROOTTOOLS_OT_assign_bone_collection(bpy.types.Operator):
    """Create/find a bone collection and assign the currently selected bones to it"""
    bl_idname = "roottools.assign_bone_collection"
    bl_label = "Assign Selected Bones to Collection"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty(
        name="Collection Name",
        description="Name of the bone collection to create (or reuse) and assign selected bones to",
        default="Main Bones",
    )

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode with bones selected")
            return {'CANCELLED'}

        armature_data = obj.data
        selected_bones = [b for b in armature_data.edit_bones if b.select]

        if not selected_bones:
            self.report({'WARNING'}, "No bones selected")
            return {'CANCELLED'}

        collection = armature_data.collections.get(self.collection_name)
        if collection is None:
            collection = armature_data.collections.new(self.collection_name)

        for bone in selected_bones:
            collection.assign(bone)

        self.report(
            {'INFO'},
            f"Assigned {len(selected_bones)} bone(s) to collection '{self.collection_name}'"
        )
        return {'FINISHED'}


class ROOTTOOLS_OT_invert_and_delete_bones(bpy.types.Operator):
    """Invert the current bone selection then delete the newly selected
    bones (equivalent to Select > Inverse, then X > Delete Bones). Meant to
    run right after the main bones are selected & collected, to remove
    everything else."""
    bl_idname = "roottools.invert_and_delete_bones"
    bl_label = "Select Invert and Delete"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        before_count = len(edit_bones)

        bpy.ops.armature.select_all(action='INVERT')
        to_delete = len([b for b in edit_bones if b.select])

        if to_delete == 0:
            self.report({'WARNING'}, "No bones selected to delete after inverting")
            return {'CANCELLED'}

        bpy.ops.armature.delete()

        deleted = before_count - len(edit_bones)
        self.report({'INFO'}, f"Deleted {deleted} bone(s), {len(edit_bones)} remaining")
        return {'FINISHED'}


class ROOTTOOLS_OT_align_ball_to_foot(bpy.types.Operator):
    """For ball_l/ball_r: snap foot's tail to ball's head, point ball
    parallel to foot (keeping ball's own length), level ball's tail to
    the same height (Z) as its head, then extend the tail further out
    along the bone's own axis to ~N times its (now-leveled) length.
    Runs for both sides."""
    bl_idname = "roottools.align_ball_to_foot"
    bl_label = "Align Ball Bones to Feet"
    bl_options = {'REGISTER', 'UNDO'}

    extend_factor: bpy.props.FloatProperty(
        name="Extend Factor",
        description="Multiply the leveled bone's length by this factor when extending the tail",
        default=5.0,
        min=0.0001,
    )

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = []

        for side in ("l", "r"):
            ball = edit_bones.get(f"ball_{side}")
            foot = edit_bones.get(f"foot_{side}")

            if ball is None or foot is None:
                names = [n for n, b in ((f"ball_{side}", ball), (f"foot_{side}", foot)) if b is None]
                missing.extend(names)
                continue

            # 1. Snap foot's tail to ball's head (equivalent to Cursor to
            #    Selected on ball head, then Selection to Cursor on foot tail)
            foot.tail = ball.head.copy()

            # 2. Point ball parallel to foot, keeping ball's own length
            #    (root/head stays fixed, only the tail moves)
            foot_dir = foot.tail - foot.head
            if foot_dir.length > 0:
                foot_dir.normalize()
                ball_length = (ball.tail - ball.head).length
                new_tail = ball.head + foot_dir * ball_length

                # 3. Raise/lower the tail so its height (Z) matches the head
                new_tail.z = ball.head.z

                ball.tail = new_tail

                # 4. Extend the tail further out along the bone's own
                #    (now-leveled) axis to ~extend_factor times its length
                current_vec = ball.tail - ball.head
                current_length = current_vec.length
                if current_length > 0:
                    axis_dir = current_vec / current_length
                    ball.tail = ball.head + axis_dir * (current_length * self.extend_factor)

            done.append(side)

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(missing)}")
            return {'CANCELLED'}

        msg = f"Aligned & extended ball bone(s) x{self.extend_factor} for side(s): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(missing)})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_snap_calf_to_foot(bpy.types.Operator):
    """For calf_l/foot_l and calf_r/foot_r: snap calf's tail to foot's
    head (equivalent to Cursor to Selected on the foot head, then
    Selection to Cursor on the calf tail). Runs for both sides."""
    bl_idname = "roottools.snap_calf_to_foot"
    bl_label = "Snap Calf Tail to Foot Head"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = []

        for side in ("l", "r"):
            calf = edit_bones.get(f"calf_{side}")
            foot = edit_bones.get(f"foot_{side}")

            if calf is None or foot is None:
                names = [n for n, b in ((f"calf_{side}", calf), (f"foot_{side}", foot)) if b is None]
                missing.extend(names)
                continue

            calf.tail = foot.head.copy()
            done.append(side)

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(missing)}")
            return {'CANCELLED'}

        msg = f"Snapped calf tail to foot head for side(s): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(missing)})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_snap_thigh_to_calf(bpy.types.Operator):
    """For thigh_l/calf_l and thigh_r/calf_r: snap thigh's tail to calf's
    head (equivalent to Cursor to Selected on the calf head, then
    Selection to Cursor on the thigh tail). Runs for both sides."""
    bl_idname = "roottools.snap_thigh_to_calf"
    bl_label = "Snap Thigh Tail to Calf Head"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = []

        for side in ("l", "r"):
            thigh = edit_bones.get(f"thigh_{side}")
            calf = edit_bones.get(f"calf_{side}")

            if thigh is None or calf is None:
                names = [n for n, b in ((f"thigh_{side}", thigh), (f"calf_{side}", calf)) if b is None]
                missing.extend(names)
                continue

            thigh.tail = calf.head.copy()
            done.append(side)

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(missing)}")
            return {'CANCELLED'}

        msg = f"Snapped thigh tail to calf head for side(s): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(missing)})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_snap_pelvis_to_spine01(bpy.types.Operator):
    """Snap pelvis's head to spine_01's head (equivalent to Cursor to
    Selected on the spine_01 head, then Selection to Cursor on the
    pelvis head)"""
    bl_idname = "roottools.snap_pelvis_to_spine01"
    bl_label = "Snap Pelvis Head to Spine_01 Head"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        pelvis = edit_bones.get("pelvis")
        spine_01 = edit_bones.get("spine_01")

        missing = [n for n, b in (("pelvis", pelvis), ("spine_01", spine_01)) if b is None]
        if missing:
            self.report({'WARNING'}, f"Missing bone(s): {', '.join(missing)}")
            return {'CANCELLED'}

        pelvis.head = spine_01.head.copy()

        self.report({'INFO'}, "Snapped pelvis head to spine_01 head")
        return {'FINISHED'}


class ROOTTOOLS_OT_snap_spine05_to_neck01(bpy.types.Operator):
    """Snap spine_05's tail to neck_01's head (equivalent to Cursor to
    Selected on the neck_01 head, then Selection to Cursor on the
    spine_05 tail)"""
    bl_idname = "roottools.snap_spine05_to_neck01"
    bl_label = "Snap Spine_05 Tail to Neck_01 Head"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        spine_05 = edit_bones.get("spine_05")
        neck_01 = edit_bones.get("neck_01")

        missing = [n for n, b in (("spine_05", spine_05), ("neck_01", neck_01)) if b is None]
        if missing:
            self.report({'WARNING'}, f"Missing bone(s): {', '.join(missing)}")
            return {'CANCELLED'}

        spine_05.tail = neck_01.head.copy()

        self.report({'INFO'}, "Snapped spine_05 tail to neck_01 head")
        return {'FINISHED'}


class ROOTTOOLS_OT_snap_upperarm_to_lowerarm(bpy.types.Operator):
    """For upperarm_l/lowerarm_l and upperarm_r/lowerarm_r: snap
    upperarm's tail to lowerarm's head (equivalent to Cursor to Selected
    on the lowerarm head, then Selection to Cursor on the upperarm tail).
    Runs for both sides."""
    bl_idname = "roottools.snap_upperarm_to_lowerarm"
    bl_label = "Snap Upperarm Tail to Lowerarm Head"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = []

        for side in ("l", "r"):
            upperarm = edit_bones.get(f"upperarm_{side}")
            lowerarm = edit_bones.get(f"lowerarm_{side}")

            if upperarm is None or lowerarm is None:
                names = [n for n, b in ((f"upperarm_{side}", upperarm), (f"lowerarm_{side}", lowerarm)) if b is None]
                missing.extend(names)
                continue

            upperarm.tail = lowerarm.head.copy()
            done.append(side)

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(missing)}")
            return {'CANCELLED'}

        msg = f"Snapped upperarm tail to lowerarm head for side(s): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(missing)})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_extend_hand_tail(bpy.types.Operator):
    """For hand_l and hand_r: extend the tail further out along the
    bone's own axis to ~N times its current length (root/head stays
    fixed). Runs for both sides."""
    bl_idname = "roottools.extend_hand_tail"
    bl_label = "Extend Hand Tail Along Own Axis"
    bl_options = {'REGISTER', 'UNDO'}

    extend_factor: bpy.props.FloatProperty(
        name="Extend Factor",
        description="Multiply the bone's current length by this factor when extending the tail",
        default=2.0,
        min=0.0001,
    )

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = []

        for side in ("l", "r"):
            hand = edit_bones.get(f"hand_{side}")

            if hand is None:
                missing.append(f"hand_{side}")
                continue

            current_vec = hand.tail - hand.head
            current_length = current_vec.length
            if current_length > 0:
                axis_dir = current_vec / current_length
                hand.tail = hand.head + axis_dir * (current_length * self.extend_factor)

            done.append(side)

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(missing)}")
            return {'CANCELLED'}

        msg = f"Extended hand tail x{self.extend_factor} for side(s): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(missing)})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_snap_lowerarm_to_hand(bpy.types.Operator):
    """For lowerarm_l/hand_l and lowerarm_r/hand_r: snap lowerarm's tail
    to hand's head (equivalent to Cursor to Selected on the hand head,
    then Selection to Cursor on the lowerarm tail). Runs for both sides."""
    bl_idname = "roottools.snap_lowerarm_to_hand"
    bl_label = "Snap Lowerarm Tail to Hand Head"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = []

        for side in ("l", "r"):
            lowerarm = edit_bones.get(f"lowerarm_{side}")
            hand = edit_bones.get(f"hand_{side}")

            if lowerarm is None or hand is None:
                names = [n for n, b in ((f"lowerarm_{side}", lowerarm), (f"hand_{side}", hand)) if b is None]
                missing.extend(names)
                continue

            lowerarm.tail = hand.head.copy()
            done.append(side)

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(missing)}")
            return {'CANCELLED'}

        msg = f"Snapped lowerarm tail to hand head for side(s): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(missing)})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_align_index_finger(bpy.types.Operator):
    """For the index finger chain (index_metacarpal -> index_01 ->
    index_02 -> index_03): snap each bone's tail to the next bone's head
    down the chain, then blend index_03's direction halfway between its
    current position and fully-parallel-to-index_02, then extend
    index_03's tail further out along its own axis to ~N times its
    length. Runs for both sides."""
    bl_idname = "roottools.align_index_finger"
    bl_label = "Align Index Finger Chain"
    bl_options = {'REGISTER', 'UNDO'}

    parallel_blend: bpy.props.FloatProperty(
        name="Parallel Blend",
        description="0 = keep index_03's current direction, 1 = fully parallel to index_02, 0.667 = 2/3 parallel / 1/3 current",
        default=2.0 / 3.0,
        min=0.0,
        max=1.0,
    )

    extend_factor: bpy.props.FloatProperty(
        name="Extend Factor",
        description="Multiply index_03's length by this factor when extending its tail",
        default=4.0,
        min=0.0001,
    )

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = []

        for side in ("l", "r"):
            names = (
                f"index_metacarpal_{side}",
                f"index_01_{side}",
                f"index_02_{side}",
                f"index_03_{side}",
            )
            metacarpal, idx01, idx02, idx03 = (edit_bones.get(n) for n in names)

            side_missing = [n for n, b in zip(names, (metacarpal, idx01, idx02, idx03)) if b is None]
            if side_missing:
                missing.extend(side_missing)
                continue

            # Snap tails down the chain
            metacarpal.tail = idx01.head.copy()
            idx01.tail = idx02.head.copy()
            idx02.tail = idx03.head.copy()

            # Blend idx03's tail halfway between its current position and
            # fully-parallel-to-idx02 (keeping idx03's own length for the
            # fully-parallel reference point)
            current_tail = idx03.tail.copy()
            idx02_dir = idx02.tail - idx02.head
            if idx02_dir.length > 0:
                idx02_dir.normalize()
                idx03_length = (idx03.tail - idx03.head).length
                fully_parallel_tail = idx03.head + idx02_dir * idx03_length
                idx03.tail = current_tail.lerp(fully_parallel_tail, self.parallel_blend)

                # Extend idx03's tail along its own (now-blended) axis
                current_vec = idx03.tail - idx03.head
                current_length = current_vec.length
                if current_length > 0:
                    axis_dir = current_vec / current_length
                    idx03.tail = idx03.head + axis_dir * (current_length * self.extend_factor)

            done.append(side)

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(missing)}")
            return {'CANCELLED'}

        msg = f"Aligned index finger chain for side(s): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(missing)})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_align_middle_finger(bpy.types.Operator):
    """For the middle finger chain (middle_metacarpal -> middle_01 ->
    middle_02 -> middle_03): snap each bone's tail to the next bone's
    head down the chain, then blend middle_03's direction between its
    current position and fully-parallel-to-middle_02, then extend
    middle_03's tail further out along its own axis to ~N times its
    length. Runs for both sides."""
    bl_idname = "roottools.align_middle_finger"
    bl_label = "Align Middle Finger Chain"
    bl_options = {'REGISTER', 'UNDO'}

    parallel_blend: bpy.props.FloatProperty(
        name="Parallel Blend",
        description="0 = keep middle_03's current direction, 1 = fully parallel to middle_02, 0.75 = 3/4 parallel / 1/4 current",
        default=3.0 / 4.0,
        min=0.0,
        max=1.0,
    )

    extend_factor: bpy.props.FloatProperty(
        name="Extend Factor",
        description="Multiply middle_03's length by this factor when extending its tail",
        default=4.0,
        min=0.0001,
    )

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = []

        for side in ("l", "r"):
            names = (
                f"middle_metacarpal_{side}",
                f"middle_01_{side}",
                f"middle_02_{side}",
                f"middle_03_{side}",
            )
            metacarpal, mid01, mid02, mid03 = (edit_bones.get(n) for n in names)

            side_missing = [n for n, b in zip(names, (metacarpal, mid01, mid02, mid03)) if b is None]
            if side_missing:
                missing.extend(side_missing)
                continue

            # Snap tails down the chain
            metacarpal.tail = mid01.head.copy()
            mid01.tail = mid02.head.copy()
            mid02.tail = mid03.head.copy()

            # Blend mid03's tail between its current position and
            # fully-parallel-to-mid02 (keeping mid03's own length for the
            # fully-parallel reference point)
            current_tail = mid03.tail.copy()
            mid02_dir = mid02.tail - mid02.head
            if mid02_dir.length > 0:
                mid02_dir.normalize()
                mid03_length = (mid03.tail - mid03.head).length
                fully_parallel_tail = mid03.head + mid02_dir * mid03_length
                mid03.tail = current_tail.lerp(fully_parallel_tail, self.parallel_blend)

                # Extend mid03's tail along its own (now-blended) axis
                current_vec = mid03.tail - mid03.head
                current_length = current_vec.length
                if current_length > 0:
                    axis_dir = current_vec / current_length
                    mid03.tail = mid03.head + axis_dir * (current_length * self.extend_factor)

            done.append(side)

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(missing)}")
            return {'CANCELLED'}

        msg = f"Aligned middle finger chain for side(s): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(missing)})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_align_ring_finger(bpy.types.Operator):
    """For the ring finger chain (ring_metacarpal -> ring_01 -> ring_02
    -> ring_03): snap each bone's tail to the next bone's head down the
    chain, then blend ring_03's direction between its current position
    and fully-parallel-to-ring_02, then extend ring_03's tail further
    out along its own axis to ~N times its length. Runs for both sides."""
    bl_idname = "roottools.align_ring_finger"
    bl_label = "Align Ring Finger Chain"
    bl_options = {'REGISTER', 'UNDO'}

    parallel_blend: bpy.props.FloatProperty(
        name="Parallel Blend",
        description="0 = keep ring_03's current direction, 1 = fully parallel to ring_02, 0.667 = 2/3 parallel / 1/3 current",
        default=2.0 / 3.0,
        min=0.0,
        max=1.0,
    )

    extend_factor: bpy.props.FloatProperty(
        name="Extend Factor",
        description="Multiply ring_03's length by this factor when extending its tail",
        default=4.0,
        min=0.0001,
    )

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = []

        for side in ("l", "r"):
            names = (
                f"ring_metacarpal_{side}",
                f"ring_01_{side}",
                f"ring_02_{side}",
                f"ring_03_{side}",
            )
            metacarpal, r01, r02, r03 = (edit_bones.get(n) for n in names)

            side_missing = [n for n, b in zip(names, (metacarpal, r01, r02, r03)) if b is None]
            if side_missing:
                missing.extend(side_missing)
                continue

            metacarpal.tail = r01.head.copy()
            r01.tail = r02.head.copy()
            r02.tail = r03.head.copy()

            current_tail = r03.tail.copy()
            r02_dir = r02.tail - r02.head
            if r02_dir.length > 0:
                r02_dir.normalize()
                r03_length = (r03.tail - r03.head).length
                fully_parallel_tail = r03.head + r02_dir * r03_length
                r03.tail = current_tail.lerp(fully_parallel_tail, self.parallel_blend)

                current_vec = r03.tail - r03.head
                current_length = current_vec.length
                if current_length > 0:
                    axis_dir = current_vec / current_length
                    r03.tail = r03.head + axis_dir * (current_length * self.extend_factor)

            done.append(side)

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(missing)}")
            return {'CANCELLED'}

        msg = f"Aligned ring finger chain for side(s): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(missing)})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_align_pinky_finger(bpy.types.Operator):
    """For the pinky finger chain (pinky_metacarpal -> pinky_01 ->
    pinky_02 -> pinky_03): snap each bone's tail to the next bone's head
    down the chain, then blend pinky_03's direction between its current
    position and fully-parallel-to-pinky_02, then extend pinky_03's tail
    further out along its own axis to ~N times its length. Runs for both
    sides."""
    bl_idname = "roottools.align_pinky_finger"
    bl_label = "Align Pinky Finger Chain"
    bl_options = {'REGISTER', 'UNDO'}

    parallel_blend: bpy.props.FloatProperty(
        name="Parallel Blend",
        description="0 = keep pinky_03's current direction, 1 = fully parallel to pinky_02, 0.833 = 5/6 parallel / 1/6 current",
        default=5.0 / 6.0,
        min=0.0,
        max=1.0,
    )

    extend_factor: bpy.props.FloatProperty(
        name="Extend Factor",
        description="Multiply pinky_03's length by this factor when extending its tail",
        default=5.0,
        min=0.0001,
    )

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = []

        for side in ("l", "r"):
            names = (
                f"pinky_metacarpal_{side}",
                f"pinky_01_{side}",
                f"pinky_02_{side}",
                f"pinky_03_{side}",
            )
            metacarpal, p01, p02, p03 = (edit_bones.get(n) for n in names)

            side_missing = [n for n, b in zip(names, (metacarpal, p01, p02, p03)) if b is None]
            if side_missing:
                missing.extend(side_missing)
                continue

            metacarpal.tail = p01.head.copy()
            p01.tail = p02.head.copy()
            p02.tail = p03.head.copy()

            current_tail = p03.tail.copy()
            p02_dir = p02.tail - p02.head
            if p02_dir.length > 0:
                p02_dir.normalize()
                p03_length = (p03.tail - p03.head).length
                fully_parallel_tail = p03.head + p02_dir * p03_length
                p03.tail = current_tail.lerp(fully_parallel_tail, self.parallel_blend)

                current_vec = p03.tail - p03.head
                current_length = current_vec.length
                if current_length > 0:
                    axis_dir = current_vec / current_length
                    p03.tail = p03.head + axis_dir * (current_length * self.extend_factor)

            done.append(side)

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(missing)}")
            return {'CANCELLED'}

        msg = f"Aligned pinky finger chain for side(s): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(missing)})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_align_thumb(bpy.types.Operator):
    """For the thumb chain (thumb_01 -> thumb_02 -> thumb_03, no
    metacarpal): snap each bone's tail to the next bone's head down the
    chain, then blend thumb_03's direction between its current position
    and fully-parallel-to-thumb_02, then extend thumb_03's tail further
    out along its own axis to ~N times its length. Runs for both sides."""
    bl_idname = "roottools.align_thumb"
    bl_label = "Align Thumb Chain"
    bl_options = {'REGISTER', 'UNDO'}

    parallel_blend: bpy.props.FloatProperty(
        name="Parallel Blend",
        description="0 = keep thumb_03's current direction, 1 = fully parallel to thumb_02, 0.75 = 3/4 parallel / 1/4 current",
        default=3.0 / 4.0,
        min=0.0,
        max=1.0,
    )

    extend_factor: bpy.props.FloatProperty(
        name="Extend Factor",
        description="Multiply thumb_03's length by this factor when extending its tail",
        default=5.0,
        min=0.0001,
    )

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = []

        for side in ("l", "r"):
            names = (
                f"thumb_01_{side}",
                f"thumb_02_{side}",
                f"thumb_03_{side}",
            )
            t01, t02, t03 = (edit_bones.get(n) for n in names)

            side_missing = [n for n, b in zip(names, (t01, t02, t03)) if b is None]
            if side_missing:
                missing.extend(side_missing)
                continue

            t01.tail = t02.head.copy()
            t02.tail = t03.head.copy()

            current_tail = t03.tail.copy()
            t02_dir = t02.tail - t02.head
            if t02_dir.length > 0:
                t02_dir.normalize()
                t03_length = (t03.tail - t03.head).length
                fully_parallel_tail = t03.head + t02_dir * t03_length
                t03.tail = current_tail.lerp(fully_parallel_tail, self.parallel_blend)

                current_vec = t03.tail - t03.head
                current_length = current_vec.length
                if current_length > 0:
                    axis_dir = current_vec / current_length
                    t03.tail = t03.head + axis_dir * (current_length * self.extend_factor)

            done.append(side)

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(missing)}")
            return {'CANCELLED'}

        msg = f"Aligned thumb chain for side(s): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(missing)})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_align_head_up(bpy.types.Operator):
    """Point the 'head' bone's tail straight up along the world Z axis
    (converted into the armature's local space) and scale its length by
    a factor. Only the tail moves; the head/root stays in place."""
    bl_idname = "roottools.align_head_up"
    bl_label = "Align Head Bone to World Up"
    bl_options = {'REGISTER', 'UNDO'}

    scale_factor: bpy.props.FloatProperty(
        name="Length Scale",
        description="Multiply the head bone's original length by this factor",
        default=3.0,
        min=0.0001,
    )

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        head_bone = edit_bones.get("head")

        if head_bone is None:
            self.report({'WARNING'}, "Bone 'head' not found")
            return {'CANCELLED'}

        length = (head_bone.tail - head_bone.head).length
        new_length = length * self.scale_factor

        # Convert the world "up" direction (world Z) into the armature's
        # local (object) space, since edit-bone coordinates are local.
        world_up = obj.matrix_world.to_3x3().inverted() @ Vector((0.0, 0.0, 1.0))
        if world_up.length > 0:
            world_up.normalize()
            head_bone.tail = head_bone.head + world_up * new_length

        self.report({'INFO'}, f"Aligned 'head' bone to world up, scaled x{self.scale_factor}")
        return {'FINISHED'}


class ROOTTOOLS_OT_create_heel_bones(bpy.types.Operator):
    """Duplicate ball_l as heel_l, rotate the new bone's tail 90 degrees
    sideways (perpendicular to the original direction, in the horizontal
    plane), pull the tail back toward the head by a percentage, move the
    whole bone backward (opposite the original forward direction), then
    move the whole bone sideways (to the left) by a fraction of its
    original length. The right side is then generated from heel_l using
    Blender's built-in Armature > Symmetrize."""
    bl_idname = "roottools.create_heel_bones"
    bl_label = "Create Heel Bones from Ball Bones"
    bl_options = {'REGISTER', 'UNDO'}

    tail_pull_factor: bpy.props.FloatProperty(
        name="Tail Pull Toward Head",
        description="Move the tail this fraction of the way from its perpendicular position back toward the head (0 = stay at full length, 1 = collapse onto head)",
        default=0.4,
        min=0.0,
        max=1.0,
    )

    back_factor: bpy.props.FloatProperty(
        name="Back Offset Factor",
        description="Move heel_l's whole body backward by this multiple of ball_l's original length",
        default=2.0,
        min=0.0,
    )

    side_offset_factor: bpy.props.FloatProperty(
        name="Sideways (Left) Offset Factor",
        description="Move heel_l's whole body sideways (to the left) by this multiple of ball_l's original length",
        default=0.3,
        min=0.0,
    )

    symmetrize_direction: bpy.props.EnumProperty(
        name="Symmetrize Direction",
        description="Which way Blender's Symmetrize should copy (flip if heel_r ends up on the wrong side)",
        items=(
            ('NEGATIVE_X', "-X to +X", "Copy from -X side to +X side"),
            ('POSITIVE_X', "+X to -X", "Copy from +X side to -X side"),
        ),
        default='NEGATIVE_X',
    )

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        ball = edit_bones.get("ball_l")

        if ball is None:
            self.report({'WARNING'}, "Bone 'ball_l' not found")
            return {'CANCELLED'}

        if edit_bones.get("heel_l") is not None:
            self.report({'WARNING'}, "'heel_l' already exists")
            return {'CANCELLED'}

        original_dir = ball.tail - ball.head
        length = original_dir.length
        if length == 0:
            self.report({'WARNING'}, "'ball_l' has zero length")
            return {'CANCELLED'}

        forward_dir = original_dir / length
        # Rotate 90 degrees sideways around the vertical (Z) axis
        perpendicular_dir = Vector((-forward_dir.y, forward_dir.x, forward_dir.z))

        heel = edit_bones.new("heel_l")
        heel.head = ball.head.copy()
        heel.tail = ball.head + perpendicular_dir * length
        heel.parent = ball.parent
        heel.roll = ball.roll

        # Pull the tail back toward the head by tail_pull_factor
        remaining_fraction = 1.0 - self.tail_pull_factor
        heel.tail = heel.head + perpendicular_dir * (length * remaining_fraction)

        # Move the whole bone (head and tail) backward, opposite the
        # original forward direction, by back_factor * original length
        back_offset = -forward_dir * (length * self.back_factor)
        heel.head = heel.head + back_offset
        heel.tail = heel.tail + back_offset

        # Move the whole bone sideways (to the left, i.e. against the same
        # perpendicular axis used for the tail) by side_offset_factor * original length
        side_offset = -perpendicular_dir * (length * self.side_offset_factor)
        heel.head = heel.head + side_offset
        heel.tail = heel.tail + side_offset

        # Generate heel_r from heel_l using Blender's built-in Symmetrize
        for bone in edit_bones:
            bone.select = False
            bone.select_head = False
            bone.select_tail = False
        heel.select = True
        heel.select_head = True
        heel.select_tail = True
        edit_bones.active = heel

        bpy.ops.armature.symmetrize(direction=self.symmetrize_direction)

        created_r = edit_bones.get("heel_r") is not None
        msg = "Created 'heel_l'"
        msg += " and mirrored 'heel_r' via Symmetrize" if created_r else " (Symmetrize did not produce 'heel_r' — check the Symmetrize Direction option)"
        self.report({'INFO'} if created_r else {'WARNING'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_connect_leg_chain(bpy.types.Operator):
    """Parent ball_l to foot_l, foot_l to calf_l, and calf_l to thigh_l,
    each with 'Connected' (equivalent to Ctrl+P > Connected — the
    child's head is locked to the parent's tail). Runs for both sides."""
    bl_idname = "roottools.connect_leg_chain"
    bl_label = "Connect Leg Chain (Ball-Foot-Calf-Thigh)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = []

        for side in ("l", "r"):
            names = (f"ball_{side}", f"foot_{side}", f"calf_{side}", f"thigh_{side}")
            ball, foot, calf, thigh = (edit_bones.get(n) for n in names)

            side_missing = [n for n, b in zip(names, (ball, foot, calf, thigh)) if b is None]
            if side_missing:
                missing.extend(side_missing)
                continue

            # child.parent = parent_bone; use_connect locks child's head
            # to the parent's tail (equivalent to Ctrl+P > Connected)
            ball.parent = foot
            ball.use_connect = True

            foot.parent = calf
            foot.use_connect = True

            calf.parent = thigh
            calf.use_connect = True

            done.append(side)

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(missing)}")
            return {'CANCELLED'}

        msg = f"Connected leg chain for side(s): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(missing)})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_connect_arm_chain(bpy.types.Operator):
    """Parent hand to lowerarm and lowerarm to upperarm (Connected), then
    connect all finger chains (thumb, index, middle, ring, pinky) distal
    to proximal, each with 'Connected' (equivalent to Ctrl+P > Connected —
    the child's head is locked to the parent's tail). Runs for both sides."""
    bl_idname = "roottools.connect_arm_chain"
    bl_label = "Connect Arm & Finger Chains"
    bl_options = {'REGISTER', 'UNDO'}

    # (child_base, parent_base) pairs for the arm, in connect order
    ARM_PAIRS = (
        ("hand", "lowerarm"),
        ("lowerarm", "upperarm"),
    )

    # Finger chains, ordered proximal -> distal (metacarpal first where present)
    FINGER_CHAINS = {
        "thumb": ("thumb_01", "thumb_02", "thumb_03"),
        "index": ("index_metacarpal", "index_01", "index_02", "index_03"),
        "middle": ("middle_metacarpal", "middle_01", "middle_02", "middle_03"),
        "ring": ("ring_metacarpal", "ring_01", "ring_02", "ring_03"),
        "pinky": ("pinky_metacarpal", "pinky_01", "pinky_02", "pinky_03"),
    }

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = set()

        for side in ("l", "r"):
            # Build the full (child_name, parent_name) list for this side
            side_pairs = [
                (f"{child}_{side}", f"{parent}_{side}")
                for child, parent in self.ARM_PAIRS
            ]
            for chain in self.FINGER_CHAINS.values():
                names = [f"{base}_{side}" for base in chain]
                # chain is proximal -> distal; connect distal's parent = the
                # bone before it, so pair up (child, parent) = (names[i+1], names[i])
                for parent_name, child_name in zip(names, names[1:]):
                    side_pairs.append((child_name, parent_name))

            names_needed = {n for pair in side_pairs for n in pair}
            side_missing = [n for n in names_needed if edit_bones.get(n) is None]

            if side_missing:
                missing.update(side_missing)
                continue

            for child_name, parent_name in side_pairs:
                child = edit_bones.get(child_name)
                parent = edit_bones.get(parent_name)
                child.parent = parent
                child.use_connect = True

            done.append(side)

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(sorted(missing))}")
            return {'CANCELLED'}

        msg = f"Connected arm & finger chains for side(s): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(sorted(missing))})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_parent_heel_and_thigh_offset(bpy.types.Operator):
    """Parent heel to foot (per side) and both thighs to spine_01, each with
    'Keep Offset' (equivalent to Ctrl+P > Keep Offset — the parent is set
    without moving the child bone or snapping it to the parent's tail)."""
    bl_idname = "roottools.parent_heel_and_thigh_offset"
    bl_label = "Parent Heel & Thigh (Keep Offset)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if obj is None or obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object is not an armature")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Armature must be in Edit Mode")
            return {'CANCELLED'}

        edit_bones = obj.data.edit_bones
        done = []
        missing = set()

        # (child_name, parent_name) pairs to set with Keep Offset
        pairs = []
        for side in ("l", "r"):
            pairs.append((f"heel_{side}", f"foot_{side}"))
            pairs.append((f"thigh_{side}", "spine_01"))

        for child_name, parent_name in pairs:
            child = edit_bones.get(child_name)
            parent = edit_bones.get(parent_name)

            if child is None or parent is None:
                if child is None:
                    missing.add(child_name)
                if parent is None:
                    missing.add(parent_name)
                continue

            # Keep Offset: set the parent without snapping the child's head
            # to the parent's tail (leave use_connect False, don't move head/tail)
            child.parent = parent
            child.use_connect = False
            done.append(f"{child_name} -> {parent_name}")

        if not done:
            self.report({'WARNING'}, f"No matching bones found. Missing: {', '.join(sorted(missing))}")
            return {'CANCELLED'}

        msg = f"Parented (Keep Offset): {', '.join(done)}"
        if missing:
            msg += f" (skipped, missing: {', '.join(sorted(missing))})"
        self.report({'INFO'}, msg)
        return {'FINISHED'}


# --- Group definitions & batch runners --------------------------------
# Each entry is the suffix after "roottools." (i.e. bpy.ops.roottools.<name>)
GROUP_CLEANUP_SETUP = (
    "unparent_roots",
    "delete_empties",
    "unparent_meshes",
    "delete_extra_roots",
    "parent_meshes_to_root",
    "select_main_bones",
    "show_armature_in_front",
    "assign_bone_collection",
    "invert_and_delete_bones",
)

GROUP_ALIGN_SNAP = (
    "align_ball_to_foot",
    "snap_calf_to_foot",
    "snap_thigh_to_calf",
    "snap_pelvis_to_spine01",
    "snap_spine05_to_neck01",
    "snap_upperarm_to_lowerarm",
    "extend_hand_tail",
    "snap_lowerarm_to_hand",
    "align_head_up",
)

GROUP_FINGER_ALIGNMENT = (
    "align_index_finger",
    "align_middle_finger",
    "align_ring_finger",
    "align_pinky_finger",
    "align_thumb",
)

GROUP_BONE_CHAINS = (
    "create_heel_bones",
    "connect_leg_chain",
    "connect_arm_chain",
    "parent_heel_and_thigh_offset",
)


def _ensure_root_armature_edit_mode(context):
    """Select the first root armature, make it active, and switch it into
    Edit Mode. Returns the armature, or None if no root armature exists."""
    armatures = find_root_armatures(context)
    if not armatures:
        return None

    armature = armatures[0]

    if context.object is not None and context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='DESELECT')
    armature.select_set(True)
    context.view_layer.objects.active = armature

    if armature.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    return armature


def _run_ops(op_names):
    """Call each bpy.ops.roottools.<name>() in order. Returns (ran, skipped)
    lists of names, where 'skipped' covers both CANCELLED results and
    operators that raised (e.g. wrong mode, poll failure)."""
    ran = []
    skipped = []
    for name in op_names:
        op = getattr(bpy.ops.roottools, name)
        try:
            result = op()
        except RuntimeError:
            skipped.append(name)
            continue
        if 'FINISHED' in result:
            ran.append(name)
        else:
            skipped.append(name)
    return ran, skipped


class ROOTTOOLS_OT_run_cleanup_setup(bpy.types.Operator):
    """Run every button in the Cleanup & Setup group, in order"""
    bl_idname = "roottools.run_cleanup_setup"
    bl_label = "Run Cleanup & Setup"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ran, skipped = _run_ops(GROUP_CLEANUP_SETUP)
        msg = f"Cleanup & Setup: ran {len(ran)}/{len(GROUP_CLEANUP_SETUP)} step(s)"
        if skipped:
            msg += f" (skipped: {', '.join(skipped)})"
            self.report({'WARNING'}, msg)
        else:
            self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_run_align_snap(bpy.types.Operator):
    """Run every button in the Align & Snap group, in order"""
    bl_idname = "roottools.run_align_snap"
    bl_label = "Run Align & Snap"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if _ensure_root_armature_edit_mode(context) is None:
            self.report({'WARNING'}, "No root armature found")
            return {'CANCELLED'}

        ran, skipped = _run_ops(GROUP_ALIGN_SNAP)
        msg = f"Align & Snap: ran {len(ran)}/{len(GROUP_ALIGN_SNAP)} step(s)"
        if skipped:
            msg += f" (skipped: {', '.join(skipped)})"
            self.report({'WARNING'}, msg)
        else:
            self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_run_finger_alignment(bpy.types.Operator):
    """Run every button in the Finger Alignment group, in order"""
    bl_idname = "roottools.run_finger_alignment"
    bl_label = "Run Finger Alignment"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if _ensure_root_armature_edit_mode(context) is None:
            self.report({'WARNING'}, "No root armature found")
            return {'CANCELLED'}

        ran, skipped = _run_ops(GROUP_FINGER_ALIGNMENT)
        msg = f"Finger Alignment: ran {len(ran)}/{len(GROUP_FINGER_ALIGNMENT)} step(s)"
        if skipped:
            msg += f" (skipped: {', '.join(skipped)})"
            self.report({'WARNING'}, msg)
        else:
            self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_run_bone_chains(bpy.types.Operator):
    """Run every button in the Bone Chains group, in order"""
    bl_idname = "roottools.run_bone_chains"
    bl_label = "Run Bone Chains"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if _ensure_root_armature_edit_mode(context) is None:
            self.report({'WARNING'}, "No root armature found")
            return {'CANCELLED'}

        ran, skipped = _run_ops(GROUP_BONE_CHAINS)
        msg = f"Bone Chains: ran {len(ran)}/{len(GROUP_BONE_CHAINS)} step(s)"
        if skipped:
            msg += f" (skipped: {', '.join(skipped)})"
            self.report({'WARNING'}, msg)
        else:
            self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_OT_run_all(bpy.types.Operator):
    """Run every group from beginning to end: Cleanup & Setup, Align & Snap,
    Finger Alignment, then Bone Chains"""
    bl_idname = "roottools.run_all"
    bl_label = "Run All (Full Pipeline)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        all_groups = (
            ("Cleanup & Setup", GROUP_CLEANUP_SETUP),
            ("Align & Snap", GROUP_ALIGN_SNAP),
            ("Finger Alignment", GROUP_FINGER_ALIGNMENT),
            ("Bone Chains", GROUP_BONE_CHAINS),
        )

        if find_root_armatures(context):
            total_ran = 0
            total_ops = 0
            skipped_all = []

            for label, op_names in all_groups:
                # Cleanup & Setup ends in Edit Mode via select_main_bones;
                # the other groups need Edit Mode entered up front.
                if op_names is not GROUP_CLEANUP_SETUP:
                    if _ensure_root_armature_edit_mode(context) is None:
                        skipped_all.extend(op_names)
                        continue

                ran, skipped = _run_ops(op_names)
                total_ran += len(ran)
                total_ops += len(op_names)
                skipped_all.extend(skipped)
        else:
            self.report({'WARNING'}, "No root armature found")
            return {'CANCELLED'}

        msg = f"Full pipeline: ran {total_ran}/{total_ops} step(s)"
        if skipped_all:
            msg += f" (skipped: {', '.join(skipped_all)})"
            self.report({'WARNING'}, msg)
        else:
            self.report({'INFO'}, msg)
        return {'FINISHED'}


class ROOTTOOLS_PT_panel(bpy.types.Panel):
    bl_label = "MH2Rigify"
    bl_idname = "ROOTTOOLS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MH2Rigify"

    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.operator(ROOTTOOLS_OT_run_all.bl_idname, icon='PLAY')
        layout.separator()

        # --- Folder: Cleanup & Setup ---
        header, panel = layout.panel("ROOTTOOLS_folder_cleanup_setup", default_closed=False)
        header.label(text="Cleanup & Setup")
        if panel:
            panel.operator(ROOTTOOLS_OT_run_cleanup_setup.bl_idname, icon='PLAY')
            panel.separator()
            panel.operator(ROOTTOOLS_OT_unparent_roots.bl_idname, icon='UNLINKED')
            panel.operator(ROOTTOOLS_OT_delete_empties.bl_idname, icon='EMPTY_AXIS')
            panel.operator(ROOTTOOLS_OT_unparent_meshes.bl_idname, icon='MESH_DATA')
            panel.operator(ROOTTOOLS_OT_delete_extra_roots.bl_idname, icon='ARMATURE_DATA')
            panel.operator(ROOTTOOLS_OT_parent_meshes_to_root.bl_idname, icon='CON_ARMATURE')
            panel.operator(ROOTTOOLS_OT_select_main_bones.bl_idname, icon='BONE_DATA')
            panel.operator(ROOTTOOLS_OT_show_armature_in_front.bl_idname, icon='OVERLAY')
            panel.operator(ROOTTOOLS_OT_assign_bone_collection.bl_idname, icon='GROUP_BONE')
            panel.operator(ROOTTOOLS_OT_invert_and_delete_bones.bl_idname, icon='TRASH')

        # --- Folder: Align & Snap ---
        header, panel = layout.panel("ROOTTOOLS_folder_align_snap", default_closed=False)
        header.label(text="Align & Snap")
        if panel:
            panel.operator(ROOTTOOLS_OT_run_align_snap.bl_idname, icon='PLAY')
            panel.separator()
            panel.operator(ROOTTOOLS_OT_align_ball_to_foot.bl_idname, icon='CON_TRACKTO')
            panel.operator(ROOTTOOLS_OT_snap_calf_to_foot.bl_idname, icon='PIVOT_CURSOR')
            panel.operator(ROOTTOOLS_OT_snap_thigh_to_calf.bl_idname, icon='PIVOT_CURSOR')
            panel.operator(ROOTTOOLS_OT_snap_pelvis_to_spine01.bl_idname, icon='PIVOT_CURSOR')
            panel.operator(ROOTTOOLS_OT_snap_spine05_to_neck01.bl_idname, icon='PIVOT_CURSOR')
            panel.operator(ROOTTOOLS_OT_snap_upperarm_to_lowerarm.bl_idname, icon='PIVOT_CURSOR')
            panel.operator(ROOTTOOLS_OT_extend_hand_tail.bl_idname, icon='CON_STRETCHTO')
            panel.operator(ROOTTOOLS_OT_snap_lowerarm_to_hand.bl_idname, icon='PIVOT_CURSOR')
            panel.operator(ROOTTOOLS_OT_align_head_up.bl_idname, icon='SORT_DESC')

        # --- Folder: Finger Alignment ---
        header, panel = layout.panel("ROOTTOOLS_folder_finger_align", default_closed=False)
        header.label(text="Finger Alignment")
        if panel:
            panel.operator(ROOTTOOLS_OT_run_finger_alignment.bl_idname, icon='PLAY')
            panel.separator()
            panel.operator(ROOTTOOLS_OT_align_index_finger.bl_idname, icon='CON_TRACKTO')
            panel.operator(ROOTTOOLS_OT_align_middle_finger.bl_idname, icon='CON_TRACKTO')
            panel.operator(ROOTTOOLS_OT_align_ring_finger.bl_idname, icon='CON_TRACKTO')
            panel.operator(ROOTTOOLS_OT_align_pinky_finger.bl_idname, icon='CON_TRACKTO')
            panel.operator(ROOTTOOLS_OT_align_thumb.bl_idname, icon='CON_TRACKTO')

        # --- Folder: Bone Chains ---
        header, panel = layout.panel("ROOTTOOLS_folder_bone_chains", default_closed=False)
        header.label(text="Bone Chains")
        if panel:
            panel.operator(ROOTTOOLS_OT_run_bone_chains.bl_idname, icon='PLAY')
            panel.separator()
            panel.operator(ROOTTOOLS_OT_create_heel_bones.bl_idname, icon='BONE_DATA')
            panel.operator(ROOTTOOLS_OT_connect_leg_chain.bl_idname, icon='CONSTRAINT_BONE')
            panel.operator(ROOTTOOLS_OT_connect_arm_chain.bl_idname, icon='CONSTRAINT_BONE')
            panel.operator(ROOTTOOLS_OT_parent_heel_and_thigh_offset.bl_idname, icon='CON_CHILDOF')



classes = (
    ROOTTOOLS_OT_unparent_roots,
    ROOTTOOLS_OT_delete_empties,
    ROOTTOOLS_OT_unparent_meshes,
    ROOTTOOLS_OT_delete_extra_roots,
    ROOTTOOLS_OT_parent_meshes_to_root,
    ROOTTOOLS_OT_select_main_bones,
    ROOTTOOLS_OT_show_armature_in_front,
    ROOTTOOLS_OT_assign_bone_collection,
    ROOTTOOLS_OT_invert_and_delete_bones,
    ROOTTOOLS_OT_align_ball_to_foot,
    ROOTTOOLS_OT_snap_calf_to_foot,
    ROOTTOOLS_OT_snap_thigh_to_calf,
    ROOTTOOLS_OT_snap_pelvis_to_spine01,
    ROOTTOOLS_OT_snap_spine05_to_neck01,
    ROOTTOOLS_OT_snap_upperarm_to_lowerarm,
    ROOTTOOLS_OT_extend_hand_tail,
    ROOTTOOLS_OT_snap_lowerarm_to_hand,
    ROOTTOOLS_OT_align_index_finger,
    ROOTTOOLS_OT_align_middle_finger,
    ROOTTOOLS_OT_align_ring_finger,
    ROOTTOOLS_OT_align_pinky_finger,
    ROOTTOOLS_OT_align_thumb,
    ROOTTOOLS_OT_align_head_up,
    ROOTTOOLS_OT_create_heel_bones,
    ROOTTOOLS_OT_connect_leg_chain,
    ROOTTOOLS_OT_connect_arm_chain,
    ROOTTOOLS_OT_parent_heel_and_thigh_offset,
    ROOTTOOLS_OT_run_cleanup_setup,
    ROOTTOOLS_OT_run_align_snap,
    ROOTTOOLS_OT_run_finger_alignment,
    ROOTTOOLS_OT_run_bone_chains,
    ROOTTOOLS_OT_run_all,
    ROOTTOOLS_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
