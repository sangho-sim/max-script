# -*- coding: utf-8 -*-
"""3D 뷰포트 N패널 > 'Geo Prompt' 탭."""

import bpy


class VIEW3D_PT_geo_node_prompt(bpy.types.Panel):
    bl_label = "Geo Prompt"
    bl_idname = "VIEW3D_PT_geo_node_prompt"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Geo Prompt"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.geo_prompt

        obj = context.active_object
        if obj is None or obj.type != "MESH":
            layout.label(text="메쉬 오브젝트를 선택하세요.", icon="ERROR")
            return

        layout.prop(settings, "mode")
        layout.prop(settings, "prompt", text="")
        layout.operator("geo_node_prompt.generate", icon="PLAY")

        if settings.last_status:
            box = layout.box()
            col = box.column(align=True)
            for i in range(0, len(settings.last_status), 40):
                col.label(text=settings.last_status[i:i + 40])

        if settings.last_modifier_name:
            target = bpy.data.objects.get(settings.last_object_name)
            modifier = target.modifiers.get(settings.last_modifier_name) if target else None
            row = layout.row()
            if modifier is not None:
                icon = "HIDE_OFF" if modifier.show_viewport else "HIDE_ON"
                row.operator("geo_node_prompt.toggle_last", icon=icon)
            else:
                row.operator("geo_node_prompt.toggle_last")


CLASSES = (VIEW3D_PT_geo_node_prompt,)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
