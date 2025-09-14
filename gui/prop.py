import bpy

from bpy.props import (
    BoolProperty,
    PointerProperty,
)


class IFP_ActionProps(bpy.types.PropertyGroup):

    use_export: BoolProperty(name="Use Export", default=True)
    target_armature: PointerProperty(name="Target Armature", type=bpy.types.Object)

    def register():
        bpy.types.Action.ifp = bpy.props.PointerProperty(type=IFP_ActionProps)
