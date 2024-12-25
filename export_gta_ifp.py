import bpy

from dataclasses import dataclass
from mathutils import Euler, Matrix, Quaternion, Vector
from typing import Dict, List, Set, Tuple
from . ifp import Ifp, Keyframe, ANIM_CLASSES

@dataclass
class Transformation:
    location:            Vector
    rotation_quaternion: Quaternion
    rotation_euler:      Euler
    scale:               Vector


@dataclass
class PoseData:
    bone_id:        int
    bone:           bpy.types.PoseBone
    transfomations: Dict[int, Transformation]
    type:           List[str]


def invalid_active_object(self, context):
    self.layout.label(text='You need to select the armature to export animation')


def is_bone_taged(bone):
    return bone.get('bone_id') is not None


def translation_matrix(v):
    return Matrix.Translation(v)


def scale_matrix(v):
    mat = Matrix.Identity(4)
    mat[0][0], mat[1][1], mat[2][2] = v[0], v[1], v[2]
    return mat


def basis_to_local_matrix(basis_matrix, global_matrix, parent_matrix):
    return parent_matrix.inverted() @ global_matrix @ basis_matrix


def get_pose_data(arm_obj, act) -> Tuple[Dict[str, PoseData], Set[str]]:
    taged_bones = [bone for bone in arm_obj.data.bones if is_bone_taged(bone)]
    pose_data: Dict[str, PoseData] = {}
    missing_bone_ids = set()
    name_tag = 'bone_id:'

    for curve in act.fcurves:
        if 'pose.bones' not in curve.data_path:
            continue

        bone_name = curve.group.name
        real_bone_name = curve.data_path.split('"')[1]
        bone = arm_obj.data.bones.get(real_bone_name)

        if bone in taged_bones:
            bone_id = bone['bone_id']
        else:
            try:
                bone_id = int(bone_name[bone_name.index(name_tag)+len(name_tag):])
                bone_name = real_bone_name
            except ValueError:
                missing_bone_ids.add(real_bone_name)
                continue

        if bone_name not in pose_data:
            pose_data[bone_name] = PoseData(
                bone_id=bone_id,
                bone=bone,
                transfomations={},
                type=['K', 'R', '0', '0'])

        for kp in curve.keyframe_points:
            time = int(kp.co[0])
            if time not in pose_data[bone_name].transfomations:
                pose_data[bone_name].transfomations[time] = Transformation(
                    location=Vector(),
                    rotation_quaternion=Quaternion(),
                    rotation_euler=Euler(),
                    scale=Vector())

            if curve.data_path == 'pose.bones["%s"].location' % real_bone_name:
                pose_data[bone_name].transfomations[time].location[curve.array_index] = kp.co[1]
                pose_data[bone_name].type[2] = 'T'

            elif curve.data_path == 'pose.bones["%s"].rotation_quaternion' % real_bone_name:
                pose_data[bone_name].transfomations[time].rotation_quaternion[curve.array_index] = kp.co[1]

            elif curve.data_path == 'pose.bones["%s"].rotation_euler' % real_bone_name:
                pose_data[bone_name].transfomations[time].rotation_euler[curve.array_index] = kp.co[1]

            elif curve.data_path == 'pose.bones["%s"].scale' % real_bone_name:
                pose_data[bone_name].transfomations[time].scale[curve.array_index] = kp.co[1]
                pose_data[bone_name].type[3] = 'S'

    return pose_data, missing_bone_ids


def create_ifp_animations(arm_obj, ifp_cls, actions, fps):
    anim_cls = ifp_cls.get_animation_class()
    bone_cls = anim_cls.get_bone_class()
    animations = []
    missing_bone_ids = set()

    for act in actions:
        anim = anim_cls(act.name, [])
        pose_data, mbi = get_pose_data(arm_obj, act)

        for bone_name, data in pose_data.items():
            bone = data.bone
            if bone:
                rest_mat = bone.matrix_local
                if bone.parent:
                    parent_mat = bone.parent.matrix_local
                    local_rot = (parent_mat.inverted_safe() @ rest_mat).to_quaternion()
                else:
                    parent_mat = Matrix.Identity(4)
                    local_rot = rest_mat.to_quaternion()

            keyframes = []
            for time, tr in data.transfomations.items():
                kf_pos = tr.location
                if bone and arm_obj.pose.bones[bone.name].rotation_mode == 'QUATERNION':
                    kf_rot = tr.rotation_quaternion
                else:
                    kf_rot = tr.rotation_euler.to_quaternion()
                kf_scl = tr.scale

                if bone:
                    basis_mat = translation_matrix(kf_pos) @ scale_matrix(kf_scl)
                    local_mat = basis_to_local_matrix(basis_mat, rest_mat, parent_mat)

                    kf_pos = local_mat.to_translation()
                    kf_rot = local_rot.inverted().rotation_difference(kf_rot)
                    kf_scl = local_mat.to_scale()

                kf = Keyframe(time / fps, kf_pos, kf_rot, kf_scl)
                keyframes.append(kf)

            anim.bones.append(bone_cls(bone_name, ''.join(data.type), True, data.bone_id, 0, 0, keyframes))

        animations.append(anim)
        missing_bone_ids.update(mbi)

    if missing_bone_ids:
        bpy.ops.message.missing_bone_ids('INVOKE_DEFAULT', message='\n'.join(missing_bone_ids))

    return animations


def save(context, filepath, name, version, fps):
    arm_obj = context.view_layer.objects.active
    if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
        context.window_manager.popup_menu(invalid_active_object, title='Error', icon='ERROR')
        return {'CANCELLED'}

    ifp_cls = ANIM_CLASSES[version]
    if version == 'ANP3':
        fps = 1.0

    animations = create_ifp_animations(arm_obj, ifp_cls, bpy.data.actions, fps)
    data = ifp_cls(name, animations)
    ifp = Ifp(version, data)
    ifp.save(filepath)

    return {'FINISHED'}
