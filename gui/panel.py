import bpy

from .operator import (
    SCENE_OT_ifp_construct_armature,
    OBJECT_OT_ifp_retarget_action,
    OBJECT_OT_ifp_untarget_action,
)


class VIEW3D_PT_IFP_Tools(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_ifp_tools"
    bl_label  = "GTA IFP"

    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "GTA IFP"

    def draw(self, context):
        layout = self.layout
        layout.operator(SCENE_OT_ifp_construct_armature.bl_idname, icon="ARMATURE_DATA")
        layout.operator(OBJECT_OT_ifp_retarget_action.bl_idname, icon="ACTION")
        layout.operator(OBJECT_OT_ifp_untarget_action.bl_idname, icon="REMOVE")

        arm_obj = context.object
        if arm_obj and type(arm_obj.data) != bpy.types.Armature:
            arm_obj = None

        act = None
        if arm_obj and arm_obj.animation_data:
            act = arm_obj.animation_data.action

        box = layout.box()
        box.label(text=f"Active Armature: {arm_obj.name if arm_obj else None}")
        box.label(text=f"Active Action: {act.name if act else None}")

        if act:
            action_target_arm = act.ifp.target_armature
            box.label(text=f"Target Armature: {action_target_arm.name if action_target_arm else None}")
