import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    StringProperty,
)
from bpy_extras.io_utils import (
    ImportHelper,
    ExportHelper,
)

bl_info = {
    "name": "GTA Animation",
    "author": "Psycrow",
    "version": (0, 0, 6),
    "blender": (2, 81, 0),
    "location": "File > Import-Export",
    "description": "Import / Export GTA Animation (.ifp)",
    "warning": "",
    "wiki_url": "",
    "support": 'COMMUNITY',
    "category": "Import-Export"
}

if "bpy" in locals():
    import importlib
    if "import_gta_ifp" in locals():
        importlib.reload(import_gta_ifp)
    if "export_gta_ifp" in locals():
        importlib.reload(export_gta_ifp)


class MissingBonesAlert(bpy.types.Operator):
    bl_idname = "message.missing_bones"
    bl_label = "Missing bones"

    message: StringProperty(default='')

    def execute(self, context):
        self.report({'WARNING'}, 'Missing bones:\n' + self.message)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=240)

    def draw(self, context):
        layout = self.layout
        for text in self.message.split('\n'):
            if text:
                layout.label(text=text, icon='BONE_DATA')


class MissingBoneIds(bpy.types.Operator):
    bl_idname = "message.missing_bone_ids"
    bl_label = "Missing bone ids"

    message: StringProperty(default='')

    def execute(self, context):
        self.report({'WARNING'}, 'Missing bone ids:\n' + self.message)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=240)

    def draw(self, context):
        layout = self.layout
        for text in self.message.split('\n'):
            if text:
                layout.label(text=text, icon='BONE_DATA')


class IFP_ActionProps(bpy.types.PropertyGroup):

    use_export: BoolProperty(name="Use Export", default=True)

    def register():
        bpy.types.Action.ifp = bpy.props.PointerProperty(type=IFP_ActionProps)


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

    def execute(self, context):
        from . import import_gta_ifp

        keywords = self.as_keywords(ignore=("axis_forward",
                                            "axis_up",
                                            "filter_glob",
                                            ))
        return import_gta_ifp.load(context, **keywords)


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
        from . import export_gta_ifp

        return export_gta_ifp.save(context, self.filepath, self.ifp_name, self.ifp_version, self.fps)


def menu_func_import(self, context):
    self.layout.operator(ImportGtaIfp.bl_idname,
                         text="GTA Animation (.ifp)")


def menu_func_export(self, context):
    self.layout.operator(ExportGtaIfp.bl_idname,
                         text="GTA Animation (.ifp)")


classes = (
    IFP_ActionProps,
    ImportGtaIfp,
    ExportGtaIfp,
    MissingBonesAlert,
    MissingBoneIds,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
