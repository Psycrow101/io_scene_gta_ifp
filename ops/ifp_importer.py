import bpy

from .common import set_keyframe
from ..gtaLib.ifp import Animation


def create_action(anim:Animation, fps:float):
    act = bpy.data.actions.new(anim.name)

    group = act.groups.new(name='ifp')
    group.mute = group.lock = True

    for b in anim.bones:
        bone_name = b.name
        bone_id = b.bone_id if b.use_bone_id else None

        data_path_prefix = f"ifp//{bone_name}//{bone_id}//"

        has_location = b.keyframe_type[2] == 'T'
        has_scale = b.keyframe_type[3] == 'S'

        cr = [act.fcurves.new(data_path=data_path_prefix + 'R', index=i) for i in range(4)]
        for c in cr:
            c.mute = c.lock = True
            c.group = group

        if has_location:
            cl = [act.fcurves.new(data_path=data_path_prefix + 'T', index=i) for i in range(3)]
            for c in cl:
                c.mute = c.lock = True
                c.group = group

        if has_scale:
            cs = [act.fcurves.new(data_path=data_path_prefix + 'S', index=i) for i in range(3)]
            for c in cs:
                c.mute = c.lock = True
                c.group = group

        for kf in b.keyframes:
            time = kf.time * fps

            if has_location:
                set_keyframe(cl, time, kf.pos)

            if has_scale:
                set_keyframe(cs, time, kf.scl)

            set_keyframe(cr, time, kf.rot)

    return act
