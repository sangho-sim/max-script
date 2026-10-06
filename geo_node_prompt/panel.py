# -*- coding: utf-8 -*-
"""3D 뷰포트 N패널 > 'Geo Prompt' 탭."""

import bpy

from . import recipes

EXAMPLES = "예: 문어다리 · 나선 · 사슬 · 바위 · 복셀 · 분해 · 덩굴 · 풀 흩뿌리기 · 울퉁불퉁"


class VIEW3D_PT_geo_node_prompt(bpy.types.Panel):
    bl_label = "Geo Prompt"
    bl_idname = "VIEW3D_PT_geo_node_prompt"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Geo Prompt"

    def draw(self, context):
        layout = self.layout
        settings = context.scene.geo_prompt

        layout.prop(settings, "mode")
        layout.prop(settings, "prompt", text="")
        layout.operator("geo_node_prompt.generate", icon="PLAY")
        layout.label(text=EXAMPLES)

        if settings.suggestions:
            box = layout.box()
            box.label(text="이걸 찾으셨나요?", icon="QUESTION")
            for recipe_id in settings.suggestions.split(","):
                recipe = recipes.get(recipe_id)
                if recipe is not None:
                    box.operator("geo_node_prompt.apply_recipe", text=recipe.name).recipe_id = recipe_id

        box = layout.box()
        box.label(text="레시피 목록에서 바로 만들기", icon="NODETREE")
        row = box.row(align=True)
        row.prop(settings, "recipe_choice", text="")
        row.operator("geo_node_prompt.apply_recipe", text="", icon="ADD").recipe_id = ""

        if settings.last_status:
            box = layout.box()
            col = box.column(align=True)
            for i in range(0, len(settings.last_status), 40):
                col.label(text=settings.last_status[i:i + 40])

        if settings.last_ai_spec:
            layout.operator("geo_node_prompt.save_ai_recipe", icon="FILE_TICK")

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
