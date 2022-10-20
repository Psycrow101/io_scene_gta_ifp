import bpy
from bpy.props import (
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
    "version": (0, 0, 1),
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

    message: StringProperty(
        name = "message",
        description = "message",
        default = ''
    )

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

        keywords = self.as_keywords(ignore=("filter_glob",
                                            ))

        return import_gta_ifp.load(context, **keywords)


class ExportGtaIfp(bpy.types.Operator, ExportHelper):
    bl_idname = "export_scene.gta_ifp"
    bl_label = "Export GTA Animation"
    bl_options = {'PRESET'}

    filter_glob: StringProperty(default="*.ifp", options={'HIDDEN'})
    filename_ext = ".ifp"

    def execute(self, context):
        from . import export_gta_ifp

        return export_gta_ifp.save(context, self.filepath, 'RYDER', 'ANP3')


def menu_func_import(self, context):
    self.layout.operator(ImportGtaIfp.bl_idname,
                         text="GTA Animation (.ifp)")


def menu_func_export(self, context):
    self.layout.operator(ExportGtaIfp.bl_idname,
                         text="GTA Animation (.ifp)")


classes = (
    ImportGtaIfp,
    ExportGtaIfp,
    MissingBonesAlert,
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
