import bpy

from mathutils import Matrix, Vector
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


def create_action(arm_obj, anim, fps, global_matrix):
    act = bpy.data.actions.new(anim.name)
    missing_bones = set()

    for b in anim.bones:
        bone = find_bone_by_id(arm_obj, b.bone_id)
        if not bone:
            bone = arm_obj.data.bones.get(b.name)

        if bone:
            g = act.groups.new(name=b.name)
            bone_name = bone.name
            pose_bone = arm_obj.pose.bones[bone_name]
            pose_bone.rotation_mode = 'QUATERNION'
            pose_bone.location = (0, 0, 0)
            pose_bone.rotation_quaternion = (1, 0, 0, 0)
            pose_bone.scale = (1, 1, 1)
            loc_mat = bone.matrix_local.copy()
            if bone.parent:
                loc_mat = bone.parent.matrix_local.inverted_safe() @ loc_mat
            else:
                loc_mat = global_matrix @ loc_mat
        else:
            g = act.groups.new(name='%s %d' % (b.name, b.bone_id))
            bone_name = b.name
            loc_mat = Matrix.Identity(4)
            missing_bones.add(bone_name)

        cr = [act.fcurves.new(data_path=(POSEDATA_PREFIX % bone_name) + 'rotation_quaternion', index=i) for i in range(4)]
        for c in cr:
            c.group = g

        if b.keyframe_type[2] == 'T':
            cl = [act.fcurves.new(data_path=(POSEDATA_PREFIX % bone_name) + 'location', index=i) for i in range(3)]
            for c in cl:
                c.group = g

        if b.keyframe_type[3] == 'S':
            cs = [act.fcurves.new(data_path=(POSEDATA_PREFIX % bone_name) + 'scale', index=i) for i in range(3)]
            for c in cs:
                c.group = g

        for kf in b.keyframes:
            time = kf.time * fps

            if b.keyframe_type[2] == 'T':
                set_keyframe(cl, time, kf.pos - loc_mat.to_translation())
            if b.keyframe_type[3] == 'S':
                set_keyframe(cl, time, Vector((1, 1, 1)) + kf.scl - loc_mat.to_scale())

            rot = loc_mat.to_quaternion().rotation_difference(kf.rot)
            set_keyframe(cr, time, rot)

    return act, missing_bones


def load(context, filepath, *, fps, global_matrix):
    arm_obj = context.view_layer.objects.active
    if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
        context.window_manager.popup_menu(invalid_active_object, title='Error', icon='ERROR')
        return {'CANCELLED'}

    ifp = Ifp.load(filepath)
    if not ifp.data:
        return {'CANCELLED'}

    animation_data = arm_obj.animation_data
    if not animation_data:
        animation_data = arm_obj.animation_data_create()

    if ifp.version == 'ANP3':
        fps = 1.0

    missing_bones = set()
    for anim in ifp.data.animations:
        act, mb = create_action(arm_obj, anim, fps, global_matrix)
        act.name = anim.name
        animation_data.action = act
        missing_bones = missing_bones.union(mb)

    if missing_bones:
        bpy.ops.message.missing_bones('INVOKE_DEFAULT', message='\n'.join(missing_bones))


    return {'FINISHED'}
