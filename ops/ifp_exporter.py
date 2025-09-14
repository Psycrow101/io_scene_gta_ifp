import bpy

from dataclasses import dataclass
from mathutils import Euler, Matrix, Quaternion, Vector
from typing import Dict, List

from .common import translation_matrix, scale_matrix
from ..gtaLib.ifp import Keyframe

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
    overridden:     bool


def basis_to_local_matrix(basis_matrix, global_matrix, parent_matrix):
    return parent_matrix.inverted() @ global_matrix @ basis_matrix


def get_pose_data(arm_obj, act) -> Dict[str, PoseData]:
    pose_data: Dict[str, PoseData] = {}
    ifp_group = act.groups.get('ifp')

    taged_bones_map = {}

    # Collect active keyframes
    if arm_obj:
        for curve in act.fcurves:
            if curve.group == ifp_group:
                continue

            if 'pose.bones' not in curve.data_path:
                continue

            bone_name = curve.data_path.split('"')[1]
            bone = arm_obj.data.bones.get(bone_name)

            bone_id = bone.get('bone_id')
            if bone_id is None:
                continue

            bone_key = bone_id if bone_id != -1 else bone_name

            pd = taged_bones_map.get(bone_key)
            if pd is None:
                pd = PoseData(
                    bone_id=bone_id,
                    bone=bone,
                    transfomations={},
                    type=['K', 'R', '0', '0'],
                    overridden=False,
                )

            for kp in curve.keyframe_points:
                time = int(kp.co[0])
                if time not in pd.transfomations:
                    pd.transfomations[time] = Transformation(
                        location=Vector(),
                        rotation_quaternion=Quaternion(),
                        rotation_euler=Euler(),
                        scale=Vector())

                if curve.data_path == f'pose.bones["{bone_name}"].location':
                    pd.transfomations[time].location[curve.array_index] = kp.co[1]
                    pd.type[2] = 'T'

                elif curve.data_path == f'pose.bones["{bone_name}"].rotation_quaternion':
                    pd.transfomations[time].rotation_quaternion[curve.array_index] = kp.co[1]

                elif curve.data_path == f'pose.bones["{bone_name}"].rotation_euler':
                    pd.transfomations[time].rotation_euler[curve.array_index] = kp.co[1]

                elif curve.data_path == f'pose.bones["{bone_name}"].scale':
                    pd.transfomations[time].scale[curve.array_index] = kp.co[1]
                    pd.type[3] = 'S'

            taged_bones_map[bone_key] = pd

    # Merge with IFP stored keyframes
    for curve in act.fcurves:
        if curve.group != ifp_group:
            continue

        _, bone_name, bone_id, movement = curve.data_path.split('//')
        use_bone_id = bone_id != 'None'
        bone_id = int(bone_id) if use_bone_id else -1
        bone_key = bone_id if bone_id != -1 else bone_name

        pd = taged_bones_map.get(bone_key)
        if pd is not None:
            pd.overridden = True
            pose_data[bone_name] = pd
            continue

        pd = pose_data.get(bone_name)
        if pd is None:
            pd = PoseData(
                bone_id=bone_id,
                bone=None,
                transfomations={},
                type=['K', 'R', '0', '0'],
                overridden=True,
            )

        for kp in curve.keyframe_points:
            time = int(kp.co[0])
            if time not in pd.transfomations:
                pd.transfomations[time] = Transformation(
                    location=Vector(),
                    rotation_quaternion=Quaternion(),
                    rotation_euler=Euler(),
                    scale=Vector())

            if movement == 'L':
                pd.transfomations[time].location[curve.array_index] = kp.co[1]
                pd.type[2] = 'T'

            elif movement == 'R':
                pd.transfomations[time].rotation_quaternion[curve.array_index] = kp.co[1]

            elif movement == 'S':
                pd.transfomations[time].scale[curve.array_index] = kp.co[1]
                pd.type[3] = 'S'

        pose_data[bone_name] = pd

    # Merge with remaining active keyframes
    for pd in taged_bones_map.values():
        if not pd.overridden:
            pose_data[pd.bone.name] = pd

    return pose_data


def create_ifp_animations(context, ifp_cls, actions, fps):
    anim_cls = ifp_cls.get_animation_class()
    bone_cls = anim_cls.get_bone_class()
    animations = []

    for act in actions:
        arm_obj = act.ifp.target_armature

        # If there is no IFP data, use an active armature
        if not arm_obj and 'ifp' not in act.groups:
            arm_obj = context.object
            if arm_obj and type(arm_obj.data) != bpy.types.Armature:
                arm_obj = None

        anim = anim_cls(act.name, [])
        pose_data = get_pose_data(arm_obj, act)

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

    return animations
