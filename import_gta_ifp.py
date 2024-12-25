import bpy

from mathutils import Matrix, Quaternion
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


def translation_matrix(v):
    return Matrix.Translation(v)


def scale_matrix(v):
    mat = Matrix.Identity(4)
    mat[0][0], mat[1][1], mat[2][2] = v[0], v[1], v[2]
    return mat


def local_to_basis_matrix(local_matrix, global_matrix, parent_matrix):
    return global_matrix.inverted() @ (parent_matrix @ local_matrix)


def create_action(arm_obj, anim, fps):
    act = bpy.data.actions.new(anim.name)
    missing_bones = set()

    for b in anim.bones:
        bone = find_bone_by_id(arm_obj, b.bone_id) if b.use_bone_id else None
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

            rest_mat = bone.matrix_local
            if bone.parent:
                parent_mat = bone.parent.matrix_local
                local_rot = (parent_mat.inverted_safe() @ rest_mat).to_quaternion()
            else:
                parent_mat = Matrix.Identity(4)
                local_rot = rest_mat.to_quaternion()

        else:
            g = act.groups.new(name='%s bone_id:%d' % (b.name, b.bone_id))
            bone_name = b.name
            local_rot = Quaternion()
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

        prev_rot = None
        for kf in b.keyframes:
            time = kf.time * fps

            if b.keyframe_type[2] == 'T':
                if bone:
                    mat = translation_matrix(kf.pos)
                    mat_basis = local_to_basis_matrix(mat, rest_mat, parent_mat)
                    loc = mat_basis.to_translation()
                else:
                    loc = kf.pos
                set_keyframe(cl, time, loc)

            if b.keyframe_type[3] == 'S':
                if bone:
                    mat = scale_matrix(kf.scl)
                    mat_basis = local_to_basis_matrix(mat, rest_mat, parent_mat)
                    scl = mat_basis.to_scale()
                else:
                    scl = kf.scl
                set_keyframe(cs, time, scl)

            rot = local_rot.rotation_difference(kf.rot)

            if prev_rot:
                alt_rot = rot.copy()
                alt_rot.negate()
                if rot.rotation_difference(prev_rot).angle > alt_rot.rotation_difference(prev_rot).angle:
                    rot = alt_rot
            prev_rot = rot

            set_keyframe(cr, time, rot)

    return act, missing_bones


def load(context, filepath, *, fps):
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
        act, mb = create_action(arm_obj, anim, fps)
        act.name = anim.name
        animation_data.action = act
        missing_bones.update(mb)

    if missing_bones:
        bpy.ops.message.missing_bones('INVOKE_DEFAULT', message='\n'.join(missing_bones))


    return {'FINISHED'}
