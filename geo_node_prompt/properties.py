# -*- coding: utf-8 -*-
"""Scene 에 붙는 UI 상태(프롬프트, 모드, 마지막 생성 결과 상태)."""

import bpy


class GeoPromptSettings(bpy.types.PropertyGroup):
    prompt: bpy.props.StringProperty(
        name="프롬프트",
        description="예: '표면에 노이즈로 울퉁불퉁하게 해줘', '풀을 스캐터해줘'",
        default="",
    )
    mode: bpy.props.EnumProperty(
        name="모드",
        items=[
            ("OFFLINE", "오프라인 규칙만", "내장된 규칙 템플릿으로만 매칭, 네트워크 사용 안 함"),
            ("HYBRID", "하이브리드(규칙 우선, 실패 시 AI)", "규칙에 안 맞으면 Claude API로 보냄 (환경설정에서 AI 허용 필요)"),
            ("AI", "AI 강제 사용", "규칙 매칭을 건너뛰고 항상 Claude API 사용 (환경설정에서 AI 허용 필요)"),
        ],
        default="HYBRID",
    )
    last_status: bpy.props.StringProperty(name="상태", default="")
    last_modifier_name: bpy.props.StringProperty(name="마지막 생성된 모디파이어", default="")
    last_object_name: bpy.props.StringProperty(name="마지막 생성 대상 오브젝트", default="")


def register():
    bpy.utils.register_class(GeoPromptSettings)
    bpy.types.Scene.geo_prompt = bpy.props.PointerProperty(type=GeoPromptSettings)


def unregister():
    del bpy.types.Scene.geo_prompt
    bpy.utils.unregister_class(GeoPromptSettings)
