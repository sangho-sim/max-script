# -*- coding: utf-8 -*-
"""Scene 에 붙는 UI 상태(프롬프트, 모드, 레시피 선택, 마지막 생성 결과 상태)."""

import bpy

from . import recipes

_ITEMS_CACHE = []


def _recipe_items(self, context):
    # EnumProperty 콜백이 돌려준 문자열은 파이썬 쪽에서 참조를 유지해야 한다.
    _ITEMS_CACHE[:] = [(r.id, r.name, r.description) for r in recipes.all_recipes()]
    return _ITEMS_CACHE


class GeoPromptSettings(bpy.types.PropertyGroup):
    prompt: bpy.props.StringProperty(
        name="키워드",
        description="예: '문어다리', '문어다리 6개 길게', '나선', '사슬', '바위', '복셀', '분해', '덩굴', '풀 흩뿌리기'",
        default="",
    )
    mode: bpy.props.EnumProperty(
        name="모드",
        items=[
            ("OFFLINE", "레시피만", "내장 레시피로만 매칭, 네트워크 사용 안 함"),
            ("HYBRID", "레시피 우선, 없으면 AI", "레시피에 없는 키워드는 Claude API로 보냄 (환경설정에서 AI 허용 필요)"),
            ("AI", "AI 강제 사용", "레시피 매칭을 건너뛰고 항상 Claude API 사용 (환경설정에서 AI 허용 필요)"),
        ],
        default="HYBRID",
    )
    recipe_choice: bpy.props.EnumProperty(name="레시피", items=_recipe_items)
    suggestions: bpy.props.StringProperty(name="후보 레시피", default="")
    last_status: bpy.props.StringProperty(name="상태", default="")
    last_modifier_name: bpy.props.StringProperty(name="마지막 생성된 모디파이어", default="")
    last_object_name: bpy.props.StringProperty(name="마지막 생성 대상 오브젝트", default="")
    last_ai_spec: bpy.props.StringProperty(name="마지막 AI 스펙", default="")
    last_ai_prompt: bpy.props.StringProperty(name="마지막 AI 프롬프트", default="")


def register():
    bpy.utils.register_class(GeoPromptSettings)
    bpy.types.Scene.geo_prompt = bpy.props.PointerProperty(type=GeoPromptSettings)


def unregister():
    del bpy.types.Scene.geo_prompt
    bpy.utils.unregister_class(GeoPromptSettings)
