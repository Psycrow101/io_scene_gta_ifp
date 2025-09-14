import bpy

from .gui import gui


bl_info = {
    "name": "GTA Animation",
    "author": "Psycrow",
    "version": (0, 1, 0),
    "blender": (2, 81, 0),
    "location": "File > Import-Export",
    "description": "Import / Export GTA Animation (.ifp)",
    "warning": "",
    "wiki_url": "",
    "support": 'COMMUNITY',
    "category": "Import-Export"
}

classes = (
    gui.SCENE_OT_ifp_construct_armature,
    gui.OBJECT_OT_ifp_retarget_action,
    gui.OBJECT_OT_ifp_untarget_action,
    gui.VIEW3D_PT_IFP_Tools,
    gui.IFP_ActionProps,
    gui.ImportGtaIfp,
    gui.ExportGtaIfp,
    gui.ImportReport,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(gui.menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(gui.menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(gui.menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(gui.menu_func_export)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
