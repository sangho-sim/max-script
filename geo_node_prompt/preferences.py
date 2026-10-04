# -*- coding: utf-8 -*-
"""애드온 환경설정: Claude API 사용 여부, API 키, 모델 이름."""

import bpy


class GeoPromptPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    enable_ai: bpy.props.BoolProperty(
        name="AI(Claude) 사용 허용",
        description="켜면 오프라인 규칙에 매칭되지 않는 프롬프트를 Claude API로 보내 노드 구조를 생성합니다. "
                    "인터넷 연결과 API 키, API 사용 요금이 필요합니다.",
        default=False,
    )
    api_key: bpy.props.StringProperty(
        name="Anthropic API Key",
        description="https://console.anthropic.com 에서 발급받은 API 키",
        subtype="PASSWORD",
        default="",
    )
    model: bpy.props.StringProperty(
        name="모델",
        description="사용할 Claude 모델 ID",
        default="claude-sonnet-5-5",
    )
    max_tokens: bpy.props.IntProperty(
        name="Max Tokens",
        default=2000,
        min=256,
        max=8000,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "enable_ai")
        col = layout.column()
        col.enabled = self.enable_ai
        col.prop(self, "api_key")
        col.prop(self, "model")
        col.prop(self, "max_tokens")
        layout.label(text="AI를 끄면 내장된 오프라인 규칙 템플릿만으로 동작합니다.", icon="INFO")


def get_preferences(context):
    return context.preferences.addons[__package__].preferences
