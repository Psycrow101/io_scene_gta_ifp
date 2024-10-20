import bpy

from dataclasses import dataclass
from mathutils import Euler, Quaternion, Vector
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
    transfomations: dict[int, Transformation]
    type:           list[str]


def invalid_active_object(self, context):
    self.layout.label(text='You need to select the armature to export animation')


def is_bone_taged(bone):
    return bone.get('bone_id') is not None


def get_pose_data(arm_obj, act) -> tuple[dict[str, PoseData], set[str]]:
    taged_bones = [bone for bone in arm_obj.data.bones if is_bone_taged(bone)]
    pose_data: dict[str, PoseData] = {}
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


def create_ifp_animations(arm_obj, ifp_cls, actions, fps, global_matrix):
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
                loc_mat = bone.matrix_local.copy()
                if bone.parent:
                    loc_mat = bone.parent.matrix_local.inverted_safe() @ loc_mat
                else:
                    loc_mat = global_matrix @ loc_mat

            keyframes = []
            for time, tr in data.transfomations.items():
                kf_pos = tr.location
                if bone and arm_obj.pose.bones[bone.name].rotation_mode == 'QUATERNION':
                    kf_rot = tr.rotation_quaternion
                else:
                    kf_rot = tr.rotation_euler.to_quaternion()
                kf_scl = tr.scale

                if bone:
                    kf_pos += loc_mat.to_translation()
                    kf_rot = loc_mat.inverted_safe().to_quaternion().rotation_difference(kf_rot)
                    kf_scl += loc_mat.to_scale() - Vector((1, 1, 1))

                kf = Keyframe(time / fps, kf_pos, kf_rot, kf_scl)
                keyframes.append(kf)

            anim.bones.append(bone_cls(bone_name, ''.join(data.type), True, data.bone_id, 0, 0, keyframes))

        animations.append(anim)
        missing_bone_ids.update(mbi)

    if missing_bone_ids:
        bpy.ops.message.missing_bone_ids('INVOKE_DEFAULT', message='\n'.join(missing_bone_ids))

    return animations


def save(context, filepath, name, version, fps, global_matrix):
    arm_obj = context.view_layer.objects.active
    if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
        context.window_manager.popup_menu(invalid_active_object, title='Error', icon='ERROR')
        return {'CANCELLED'}

    ifp_cls = ANIM_CLASSES[version]
    if version == 'ANP3':
        fps = 1.0

    animations = create_ifp_animations(arm_obj, ifp_cls, bpy.data.actions, fps, global_matrix)
    data = ifp_cls(name, animations)
    ifp = Ifp(version, data)
    ifp.save(filepath)

    return {'FINISHED'}
