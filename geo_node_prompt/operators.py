# -*- coding: utf-8 -*-
"""프롬프트 생성 오퍼레이터 + 마지막 생성 모디파이어 on/off 토글."""

import bpy

from .templates import match_template
from .ai_backend import generate_spec_via_ai
from .node_builder import build_node_tree
from .preferences import get_preferences


class GEONODEPROMPT_OT_generate(bpy.types.Operator):
    bl_idname = "geo_node_prompt.generate"
    bl_label = "지오메트리 노드 생성"
    bl_description = "입력한 프롬프트로 지오메트리 노드 구조를 만들어 선택한 오브젝트에 모디파이어로 추가합니다"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == "MESH"

    def execute(self, context):
        settings = context.scene.geo_prompt
        obj = context.active_object
        prompt = settings.prompt.strip()

        if not prompt:
            self.report({"ERROR"}, "프롬프트를 입력하세요.")
            return {"CANCELLED"}

        mode = settings.mode
        spec = None
        source = ""

        if mode in {"OFFLINE", "HYBRID"}:
            template = match_template(prompt)
            if template is not None:
                spec = template["builder"](prompt)
                source = "규칙 템플릿: {}".format(template["label"])

        if spec is None and mode in {"HYBRID", "AI"}:
            prefs = get_preferences(context)
            if not prefs.enable_ai:
                msg = ("일치하는 오프라인 규칙이 없습니다. 환경설정에서 'AI 사용 허용'을 켜면 "
                       "Claude API로 생성할 수 있습니다." if mode == "HYBRID"
                       else "AI 모드를 쓰려면 환경설정에서 'AI 사용 허용'을 켜고 API 키를 입력하세요.")
                self.report({"ERROR"}, msg)
                return {"CANCELLED"}
            if not prefs.api_key:
                self.report({"ERROR"}, "환경설정에 Anthropic API 키가 입력되어 있지 않습니다.")
                return {"CANCELLED"}
            try:
                spec = generate_spec_via_ai(
                    prompt, prefs.api_key, prefs.model, prefs.max_tokens
                )
                source = "AI(Claude) 생성"
            except Exception as exc:  # noqa: BLE001 - 외부 API/네트워크 오류 표면화
                self.report({"ERROR"}, "AI 생성 실패: {}".format(exc))
                return {"CANCELLED"}

        if spec is None:
            self.report({"ERROR"}, "일치하는 규칙을 찾지 못했습니다. 다른 표현으로 시도해보세요.")
            return {"CANCELLED"}

        warnings = []
        try:
            tree, modifier = build_node_tree(spec, obj, warnings)
        except Exception as exc:  # noqa: BLE001
            self.report({"ERROR"}, "노드 트리 생성 실패: {}".format(exc))
            return {"CANCELLED"}

        settings.last_modifier_name = modifier.name
        settings.last_object_name = obj.name

        status = "{} → 모디파이어 '{}' 생성 완료".format(source, modifier.name)
        if warnings:
            status += " (경고 {}건, 콘솔 참고)".format(len(warnings))
            for w in warnings:
                print("[geo_node_prompt]", w)
        settings.last_status = status
        self.report({"INFO"}, status)
        return {"FINISHED"}


class GEONODEPROMPT_OT_toggle_last(bpy.types.Operator):
    bl_idname = "geo_node_prompt.toggle_last"
    bl_label = "마지막 생성 결과 켜기/끄기"
    bl_description = "가장 최근에 생성한 지오메트리 노드 모디파이어를 뷰포트/렌더에서 켜거나 끕니다"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        settings = context.scene.geo_prompt
        obj = bpy.data.objects.get(settings.last_object_name)
        if obj is None:
            self.report({"ERROR"}, "최근에 생성된 오브젝트를 찾을 수 없습니다.")
            return {"CANCELLED"}
        modifier = obj.modifiers.get(settings.last_modifier_name)
        if modifier is None:
            self.report({"ERROR"}, "최근에 생성된 모디파이어를 찾을 수 없습니다.")
            return {"CANCELLED"}

        new_state = not modifier.show_viewport
        modifier.show_viewport = new_state
        modifier.show_render = new_state
        self.report({"INFO"}, "'{}' {}".format(modifier.name, "켜짐" if new_state else "꺼짐"))
        return {"FINISHED"}


CLASSES = (
    GEONODEPROMPT_OT_generate,
    GEONODEPROMPT_OT_toggle_last,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
