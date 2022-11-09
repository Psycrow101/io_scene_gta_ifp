import bpy

from mathutils import Vector, Quaternion
from . ifp import Ifp, Anp3Bone, Keyframe, ANIM_CLASSES


def invalid_active_object(self, context):
    self.layout.label(text='You need to select the armature to export animation')


def is_bone_taged(bone):
    return bone.get('bone_id') is not None


def get_pose_data(arm_obj, act):
    all_bones = [bone for bone in arm_obj.data.bones if is_bone_taged(bone)]
    pose_data = {}

    for curve in act.fcurves:
        if 'pose.bones' not in curve.data_path:
            continue

        bone_name = curve.data_path.split('"')[1]
        bone = arm_obj.data.bones.get(bone_name)
        if bone not in all_bones:
            continue

        if bone not in pose_data:
            pose_data[bone] = {'kfs': {}, 'type': ['K', 'R', '0', '0']}

        for kp in curve.keyframe_points:
            time = int(kp.co[0])
            if time not in pose_data[bone]['kfs']:
                pose_data[bone]['kfs'][time] = (Vector(), Quaternion(), Vector())

            if curve.data_path == 'pose.bones["%s"].location' % bone_name:
                pose_data[bone]['kfs'][time][0][curve.array_index] = kp.co[1]
                pose_data[bone]['type'][2] = 'T'

            if curve.data_path == 'pose.bones["%s"].rotation_quaternion' % bone_name:
                pose_data[bone]['kfs'][time][1][curve.array_index] = kp.co[1]

            if curve.data_path == 'pose.bones["%s"].scale' % bone_name:
                pose_data[bone]['kfs'][time][2][curve.array_index] = kp.co[1]
                pose_data[bone]['type'][3] = 'S'

    return pose_data


def create_ifp_animations(arm_obj, ifp_cls, actions, fps, use_bone_id):
    anim_cls = ifp_cls.get_animation_class()
    bone_cls = anim_cls.get_bone_class()
    animations = []

    for act in actions:
        anim = anim_cls(act.name, [])

        pose_mats = get_pose_data(arm_obj, act)
        for bone, data in pose_mats.items():
            loc_mat = bone.matrix_local.copy()
            if bone.parent:
                loc_mat = bone.parent.matrix_local.inverted_safe() @ loc_mat

            keyframes = []
            for time, tr in data['kfs'].items():
                loc, rot, scale = tr

                kf_pos = loc + loc_mat.to_translation()
                kf_rot = loc_mat.inverted_safe().to_quaternion().rotation_difference(rot)
                kf_scl = scale + loc_mat.to_scale() - Vector((1, 1, 1))

                kf = Keyframe(time / fps, kf_pos, kf_rot, kf_scl)
                keyframes.append(kf)

            anim.bones.append(bone_cls(bone.name, ''.join(data['type']), use_bone_id, bone['bone_id'], 0, 0, keyframes))

        animations.append(anim)
    return animations


def save(context, filepath, name, version, fps, use_bone_id):
    arm_obj = context.view_layer.objects.active
    if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
        context.window_manager.popup_menu(invalid_active_object, title='Error', icon='ERROR')
        return {'CANCELLED'}

    ifp_cls = ANIM_CLASSES[version]
    if version == 'ANP3':
        fps, use_bone_id = 1.0, True

    animations = create_ifp_animations(arm_obj, ifp_cls, bpy.data.actions, fps, use_bone_id)
    data = ifp_cls(name, animations)
    ifp = Ifp(version, data)
    ifp.save(filepath)

    return {'FINISHED'}
