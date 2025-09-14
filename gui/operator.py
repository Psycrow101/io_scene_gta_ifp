import bpy

from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper,
)

from ..ops.armature_constructor import ArmatureConstructor
from ..ops.action_retargeter import retarget_action, untarget_action
from ..ops.ifp_importer import create_action
from ..ops.ifp_exporter import create_ifp_animations
from ..gtaLib.ifp import Ifp, ANIM_CLASSES


class SCENE_OT_ifp_construct_armature(bpy.types.Operator):
    bl_idname           = "scene.ifp_construct_armature"
    bl_description      = "Construct an armature from a hierarchy of objects"
    bl_label            = "Construct Armature"

    def execute(self, context):
        root_objects = []
        for obj in context.selected_objects:
            if obj.parent and obj.parent in context.selected_objects:
                continue

            if obj.type == 'EMPTY' and obj.children:
                root_objects.append(obj)

        for root_obj in root_objects:
            ArmatureConstructor.construct_armature(context, root_obj)

        return {'FINISHED'}


class OBJECT_OT_ifp_retarget_action(bpy.types.Operator):
    bl_idname           = "object.ifp_retarget_action"
    bl_description      = "Adjust the active action to the selected armature"
    bl_label            = "Retarget Action"

    @classmethod
    def poll(cls, context):
        arm_obj = context.object

        if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
            return False

        if not arm_obj.animation_data:
            return False

        act = arm_obj.animation_data.action
        if not act:
            return False

        return True

    def execute(self, context):
        arm_obj = context.object
        act = arm_obj.animation_data.action

        missing_bones = retarget_action(act, arm_obj)

        if missing_bones:
            bpy.ops.message.ifp_import_report('INVOKE_DEFAULT',
                                              missing_bones_message='\n'.join(missing_bones),
                                              created_actions=0)

        return {'FINISHED'}


class OBJECT_OT_ifp_untarget_action(bpy.types.Operator):
    bl_idname           = "object.ifp_untarget_action"
    bl_description      = "Clear the active action from the targeted armature"
    bl_label            = "Untarget Action"

    @classmethod
    def poll(cls, context):
        arm_obj = context.object

        if not arm_obj or type(arm_obj.data) != bpy.types.Armature:
            return False

        if not arm_obj.animation_data:
            return False

        act = arm_obj.animation_data.action
        if not act:
            return False

        return True

    def execute(self, context):
        arm_obj = context.object
        act = arm_obj.animation_data.action

        untarget_action(act)
        return {'FINISHED'}


class ImportReport(bpy.types.Operator):
    bl_idname = "message.ifp_import_report"
    bl_label = "IFP Import Report"

    missing_bones_message: StringProperty(default='')
    created_actions: IntProperty(default=0)

    def execute(self, context):
        if self.created_actions > 0:
            self.report({'INFO'}, f'Created {self.created_actions} IFP actions')
        if self.missing_bones_message:
            self.report({'WARNING'}, 'Missing bones:\n' + self.missing_bones_message)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=240)

    def draw(self, context):
        layout = self.layout
        if self.created_actions > 0:
            layout.label(text=f'Created {self.created_actions} IFP actions', icon='INFO')

        if self.missing_bones_message:
            layout.label(text='Missing bones:')
            box = layout.box()
            for text in self.missing_bones_message.split('\n'):
                if text:
                    box.label(text=text, icon='BONE_DATA')


class ImportGtaIfp(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.gta_ifp"
    bl_label = "Import GTA Animation"
    bl_options = {'PRESET', 'UNDO'}

    filter_glob: StringProperty(default="*.ifp", options={'HIDDEN'})
    filename_ext = ".ifp"

    fps: FloatProperty(
        name="FPS",
        description="Value by which the keyframe time is multiplied (GTA 3/VC)",
        default=30.0,
    )

    use_armature: BoolProperty(
        name="Use Active Armature",
        description="Adjust all actions to the active armature",
        default=True,
    )

    def execute(self, context):
        fps = self.fps
        use_armature = self.use_armature
        arm_obj = None

        if use_armature:
            arm_obj = context.view_layer.objects.active
            if arm_obj and type(arm_obj.data) != bpy.types.Armature:
                arm_obj = None

        ifp = Ifp.load(self.filepath)
        if not ifp.data:
            return {'CANCELLED'}

        if ifp.version == 'ANP3':
            fps = 1.0

        missing_bones = set()
        actions_count = 0

        for anim in ifp.data.animations:
            act = create_action(anim, fps)
            act.name = anim.name
            actions_count += 1

            if arm_obj:
                mb = retarget_action(act, arm_obj)
                missing_bones.update(mb)

                animation_data = arm_obj.animation_data
                if not animation_data:
                    animation_data = arm_obj.animation_data_create()
                animation_data.action = act

        bpy.ops.message.ifp_import_report('INVOKE_DEFAULT',
                                            missing_bones_message='\n'.join(missing_bones),
                                            created_actions=actions_count)

        return {'FINISHED'}


class ExportGtaIfp(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.gta_ifp"
    bl_label = "Export GTA Animation"
    bl_options = {'PRESET'}

    filter_glob: StringProperty(default="*.ifp", options={'HIDDEN'})
    filename_ext = ".ifp"

    ifp_version: EnumProperty(
        name='Version',
        description='IFP version',
        items={
            ('ANP3', 'GTA SA', 'IFP version for GTA San Andreas'),
            ('ANPK', 'GTA 3/VC', 'IFP version for GTA 3 and GTA Vice City')},
        default='ANP3',
    )

    ifp_name: StringProperty(
        name="Name",
        description="IFP name",
        default='Model',
        maxlen=23,
    )

    fps: FloatProperty(
        name="FPS",
        description="Value by which the keyframe time is divided (GTA 3/VC)",
        default=30.0,
    )

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "ifp_version")
        layout.prop(self, "ifp_name")
        layout.prop(self, "fps")

        box = layout.box()
        box.label(text="Actions to Export:")

        if bpy.data.actions:
            for act in bpy.data.actions:
                row = box.row()
                row.prop(act.ifp, "use_export", text="")
                row.prop(act, "name", text="")
        else:
            box.label(text="No actions found", icon='INFO')

    def execute(self, context):
        name = self.ifp_name
        version = self.ifp_version
        fps = self.fps

        ifp_cls = ANIM_CLASSES[version]
        if version == 'ANP3':
            fps = 1.0

        actions = [act for act in bpy.data.actions if act.ifp.use_export]

        animations = create_ifp_animations(context, ifp_cls, actions, fps)
        data = ifp_cls(name, animations)
        ifp = Ifp(version, data)
        ifp.save(self.filepath)

        return {'FINISHED'}


def menu_func_import(self, context):
    self.layout.operator(ImportGtaIfp.bl_idname,
                         text="GTA Animation (.ifp)")


def menu_func_export(self, context):
    self.layout.operator(ExportGtaIfp.bl_idname,
                         text="GTA Animation (.ifp)")
