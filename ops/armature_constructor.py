import bpy

from mathutils import Matrix, Vector


def clear_extension(string):
    k = string.rfind('.')
    return string if k < 0 else string[:k]


class ArmatureConstructor:

    arm_obj = None
    bones_map = {}

    @staticmethod
    def construct_bone(obj, root_bone=None):
        self = ArmatureConstructor

        if obj.type == 'MESH' and not obj.dff.is_frame:
            self.bones_map[obj] = root_bone.name
            return

        bone_name = clear_extension(obj.name)
        mat = self.arm_obj.matrix_world.inverted() @ obj.matrix_world

        bone = self.arm_obj.data.edit_bones.new(bone_name)
        bone.head = mat.translation
        bone.tail = mat @ Vector((0, 0.05, 0))
        bone.parent = root_bone
        bone.use_connect = False
        bone['bone_id'] = -1

        self.bones_map[obj] = bone.name

        for ch_obj in obj.children:
            self.construct_bone(ch_obj, bone)


    @staticmethod
    def construct_armature(context, root_obj):
        self = ArmatureConstructor

        arm_name = root_obj.name
        root_obj.name += "_csobj"

        arm_data = bpy.data.armatures.new(arm_name)
        arm_obj = bpy.data.objects.new(arm_name, arm_data)
        arm_obj.matrix_world = root_obj.matrix_world

        self.arm_obj = arm_obj
        self.bones_map = {}

        context.collection.objects.link(arm_obj)
        context.view_layer.objects.active = arm_obj
        bpy.ops.object.mode_set(mode='EDIT')

        for obj in root_obj.children:
            self.construct_bone(obj)

        bpy.ops.object.mode_set(mode='OBJECT')

        for obj, bone_name in self.bones_map.items():
            if obj.type == 'EMPTY':
                bpy.data.objects.remove(obj)
                continue

            obj.parent = arm_obj
            obj.parent_type = 'BONE'
            obj.parent_bone = bone_name
            obj.matrix_local = Matrix()
            obj.matrix_parent_inverse = arm_obj.matrix_world.inverted() @ Matrix.Translation((0, -0.05, 0))
            obj.dff.is_frame = False

        collections = []
        for col in bpy.data.collections:
            if root_obj.name in col.objects:
                col.objects.unlink(root_obj)
                collections.append(col)

        if collections:
            context.collection.objects.unlink(arm_obj)
            for col in collections:
                col.objects.link(arm_obj)

        bpy.data.objects.remove(root_obj)

    # TODO: Armature deconstrictor
