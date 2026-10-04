# -*- coding: utf-8 -*-
bl_info = {
    "name": "Geo Node Prompt",
    "author": "max-script",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Geo Prompt",
    "description": "자연어 프롬프트로 지오메트리 노드 구조를 생성 (오프라인 규칙 + 선택적 Claude API 하이브리드)",
    "category": "Node",
}

from . import preferences
from . import properties
from . import operators
from . import panel

_PREF_CLASSES = (preferences.GeoPromptPreferences,)


def register():
    import bpy

    for cls in _PREF_CLASSES:
        bpy.utils.register_class(cls)
    properties.register()
    operators.register()
    panel.register()


def unregister():
    import bpy

    panel.unregister()
    operators.unregister()
    properties.unregister()
    for cls in reversed(_PREF_CLASSES):
        bpy.utils.unregister_class(cls)
