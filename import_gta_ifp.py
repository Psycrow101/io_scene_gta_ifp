import bpy

from . ifp import Ifp

POSEDATA_PREFIX = 'pose.bones["%s"].'


def invalid_active_object(self, context):
    self.layout.label(text='You need to select the armature to import animation')


def set_keyframe(curves, frame, values):
    for i, c in enumerate(curves):
        c.keyframe_points.add(1)
        c.keyframe_points[-1].co = frame, values[i]
        c.keyframe_points[-1].interpolation = 'LINEAR'


def find_bone_by_id(arm_obj, bone_id):
    for bone in arm_obj.data.bones:
        if bone.get('bone_id') == bone_id:
            return bone


def create_action(arm_obj, anim):
    act = bpy.data.actions.new(anim.name)

    for b in anim.bones:
        bone = find_bone_by_id(arm_obj, b.bone_id)
        if not bone:
            continue
        pose_bone = arm_obj.pose.bones[bone.name]

        g = act.groups.new(name=bone.name)

        cr = [act.fcurves.new(data_path=(POSEDATA_PREFIX % bone.name) + 'rotation_quaternion', index=i) for i in range(4)]
        for c in cr:
            c.group = g

        if b.keyframe_type == 4:
            cl = [act.fcurves.new(data_path=(POSEDATA_PREFIX % bone.name) + 'location', index=i) for i in range(3)]
            for c in cl:
                c.group = g

        pose_bone.rotation_mode = 'QUATERNION'
        pose_bone.location = (0, 0, 0)
        pose_bone.rotation_quaternion = (1, 0, 0, 0)
        pose_bone.scale = (1, 1, 1)

        for kf in b.keyframes:
            loc_mat = bone.matrix_local.copy()
            if bone.parent:
                loc_mat = bone.parent.matrix_local.inverted_safe() @ loc_mat

            if b.keyframe_type == 4:
                set_keyframe(cl, kf.time, kf.pos - loc_mat.to_translation())
            set_keyframe(cr, kf.time, loc_mat.to_quaternion().rotation_difference(kf.rot))

    return act


def load(context, filepath):
    arm_obj = context.view_layer.objects.active
    if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
        context.window_manager.popup_menu(invalid_active_object, title='Error', icon='ERROR')
        return {'CANCELLED'}

    ifp = Ifp.load(filepath)
    if not ifp.animations:
        return {'CANCELLED'}

    animation_data = arm_obj.animation_data
    if not animation_data:
        animation_data = arm_obj.animation_data_create()

    context.scene.frame_start = 0
    for anim in ifp.animations:
        act = create_action(arm_obj, anim)
        act.name = anim.name
        animation_data.action = act

    return {'FINISHED'}
