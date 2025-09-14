from collections import defaultdict
from mathutils import Matrix, Quaternion

from .common import set_keyframe, translation_matrix, scale_matrix


POSEDATA_PREFIX = 'pose.bones["%s"].'


def find_bone_by_id(arm_obj, bone_id):
    for bone in arm_obj.data.bones:
        if bone.get('bone_id') == bone_id:
            return bone


def local_to_basis_matrix(local_matrix, global_matrix, parent_matrix):
    return global_matrix.inverted() @ (parent_matrix @ local_matrix)


def untarget_action(act):
    act.ifp.target_armature = None

    ifp_group = act.groups.get('ifp')
    if not ifp_group:
        return

    # Clear fcurves
    for c in list(act.fcurves):
        if c.group != ifp_group:
            act.fcurves.remove(c)

    for group in list(act.groups):
        if group != ifp_group:
            act.groups.remove(group)


def retarget_action(act, arm_obj):
    untarget_action(act)

    act.ifp.target_armature = arm_obj

    missing_bones = set()

    ifp_group = act.groups.get('ifp')
    if not ifp_group:
        return missing_bones

    act_bones = {}
    for c in act.fcurves:
        _, bone_name, bone_id, movement = c.data_path.split('//')
        use_bone_id = bone_id != 'None'
        bone_id = int(bone_id) if use_bone_id else None

        bone_data = act_bones.get(bone_name)
        if not bone_data:
            bone_data = (bone_id, defaultdict(list), defaultdict(list), defaultdict(list))

        chan = bone_data[{'R':1, 'T':2, 'S':3}[movement]]
        for kp in c.keyframe_points:
            k, v = kp.co
            chan[k].append(v)

        act_bones[bone_name] = bone_data

    for bone_name, bone_data in act_bones.items():
        bone_id, rots, locs, scls = bone_data

        bone = None
        if bone_id is not None and bone_id != -1:
            bone = find_bone_by_id(arm_obj, bone_id)
        if not bone:
            bone = arm_obj.data.bones.get(bone_name)

        if not bone:
            missing_bones.add(bone_name)
            continue

        group = act.groups.new(name=bone_name)
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

        cr = [act.fcurves.new(data_path=(POSEDATA_PREFIX % bone_name) + 'rotation_quaternion', index=i) for i in range(4)]
        for c in cr:
            c.group = group

        if locs:
            cl = [act.fcurves.new(data_path=(POSEDATA_PREFIX % bone_name) + 'location', index=i) for i in range(3)]
            for c in cl:
                c.group = group

        if scls:
            cs = [act.fcurves.new(data_path=(POSEDATA_PREFIX % bone_name) + 'scale', index=i) for i in range(3)]
            for c in cs:
                c.group = group

        prev_rot = None
        for time in sorted(rots.keys()):
            rot = local_rot.rotation_difference(Quaternion(rots[time]))
            if prev_rot:
                alt_rot = rot.copy()
                alt_rot.negate()
                if rot.rotation_difference(prev_rot).angle > alt_rot.rotation_difference(prev_rot).angle:
                    rot = alt_rot
            prev_rot = rot
            set_keyframe(cr, time, rot)

        for time in sorted(locs.keys()):
            mat = translation_matrix(locs[time])
            mat_basis = local_to_basis_matrix(mat, rest_mat, parent_mat)
            loc = mat_basis.to_translation()
            set_keyframe(cl, time, loc)

        for time in sorted(scls.keys()):
            mat = scale_matrix(scls[time])
            mat_basis = local_to_basis_matrix(mat, rest_mat, parent_mat)
            scl = mat_basis.to_scale()
            set_keyframe(cs, time, scl)

    return missing_bones
