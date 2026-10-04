# -*- coding: utf-8 -*-
"""Blender(bpy) 안에서 애드온을 실제로 켜고 생성 결과를 평가해보는 검사 스크립트.

- 내장 템플릿 8종을 각각 큐브/그리드에 빌드해서, 링크가 모두 유효한지와
  평가된 지오메트리가 기대대로 바뀌는지 확인한다.
- 애드온을 등록하고 오퍼레이터(OFFLINE 생성, 토글, AI 모드)를 실행해본다.
  AI 모드는 네트워크 대신 가짜 응답을 돌려준다.

실행 (둘 중 하나, 저장소 루트에서):
    blender -b --factory-startup --python geo_node_prompt/tests/check_templates.py
    python geo_node_prompt/tests/check_templates.py   # pip install bpy==4.2.0 (Python 3.11)
"""

import io
import json
import os
import sys
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

import bpy  # noqa: E402
import addon_utils  # noqa: E402  (bpy 를 먼저 import 해야 경로에 잡힌다)

from geo_node_prompt.templates import TEMPLATES  # noqa: E402
from geo_node_prompt.node_builder import build_node_tree  # noqa: E402


def _reset_scene(primitive="grid"):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if primitive == "grid":
        bpy.ops.mesh.primitive_grid_add()  # Blender 기본 그리드 그대로 (10x10, size 2)
    else:
        bpy.ops.mesh.primitive_cube_add()
    return bpy.context.active_object


def _evaluate(obj):
    """(정점 수, 면 수, 인스턴스 수, z 최소, z 최대)"""
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    zs = [v.co.z for v in mesh.vertices] or [0.0]
    result = (len(mesh.vertices), len(mesh.polygons))
    evaluated.to_mesh_clear()
    instances = sum(1 for inst in depsgraph.object_instances
                    if inst.is_instance and inst.parent and inst.parent.original == obj)
    return result + (instances, min(zs), max(zs))


def _set_modifier_input(modifier, name, value):
    for item in modifier.node_group.interface.items_tree:
        if getattr(item, "in_out", None) == "INPUT" and item.name == name:
            modifier[item.identifier] = value
            return
    raise KeyError(name)


# 템플릿 id -> (기반 프리미티브, 사전 준비, 평가 결과 검사)
def _prep_boolean(obj):
    # 커터를 원점에서 떨어뜨려 놓아야 transform_space 문제가 드러난다.
    bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=4, location=(0.6, 0.0, 0.0))
    cutter = bpy.context.active_object
    cutter.display_type = "WIRE"
    bpy.context.view_layer.objects.active = obj
    return cutter


def _cutter_hole_is_offset(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    # 큐브 모서리가 아닌 정점 = 구멍 테두리. 커터가 x=0.6 에 있으니 0.3~0.9 사이여야 한다.
    xs = [v.co.x for v in mesh.vertices if abs(v.co.x) < 0.99 or abs(v.co.y) < 0.99]
    evaluated.to_mesh_clear()
    return bool(xs) and all(0.25 < x < 0.95 for x in xs)


CHECKS = {
    # 평평한 기본 그리드가 실제로 울퉁불퉁해져야 한다 (정수 Scale 이면 평평하게 나온다).
    "noise_displace": ("grid", None, lambda base, r, obj: r[4] - r[3] > 1e-3),
    "scatter": ("grid", None, lambda base, r, obj: r[2] > 0 and r[1] == base[1]),
    "array": ("cube", None, lambda base, r, obj: r[0] == base[0] * 5),
    "subdivision_smooth": ("cube", None, lambda base, r, obj: r[1] == base[1] * 16),
    "shade_smooth": ("cube", None, lambda base, r, obj: r[1] == base[1]),
    "boolean_cut": ("cube", _prep_boolean, lambda base, r, obj: r[1] > base[1] and _cutter_hole_is_offset(obj)),
    "extrude_thickness": ("cube", None, lambda base, r, obj: r[1] == base[1] * 5),
    "random_delete": ("grid", None, lambda base, r, obj: 0 < r[1] < base[1]),
}


def check_template(template):
    problems = []
    primitive, prep, verify = CHECKS[template["id"]]
    obj = _reset_scene(primitive)
    base = _evaluate(obj)
    extra = prep(obj) if prep else None

    warnings = []
    spec = template["builder"]("test")
    tree, modifier = build_node_tree(spec, obj, warnings)
    problems.extend("warning: " + w for w in warnings)
    if extra is not None:
        _set_modifier_input(modifier, "Cutter Object", extra)

    if len(tree.links) != len(spec["links"]):
        problems.append("links: expected {}, got {}".format(len(spec["links"]), len(tree.links)))
    for link in tree.links:
        if not link.is_valid or not link.from_socket.enabled or not link.to_socket.enabled:
            problems.append("bad link {}.{} -> {}.{}".format(
                link.from_node.name, link.from_socket.identifier,
                link.to_node.name, link.to_socket.identifier))

    result = _evaluate(obj)
    if not verify(base, result, obj):
        problems.append("unexpected result: base={} evaluated={}".format(base[:3], result[:3]))
    return problems, result


def check_operators():
    problems = []
    _reset_scene("cube")
    addon_utils.enable("geo_node_prompt", default_set=True)
    settings = bpy.context.scene.geo_prompt
    obj = bpy.context.active_object

    settings.mode = "OFFLINE"
    settings.prompt = "표면에 노이즈로 울퉁불퉁하게 해줘"
    if bpy.ops.geo_node_prompt.generate() != {"FINISHED"}:
        problems.append("OFFLINE generate did not finish")
    modifier = obj.modifiers.get(settings.last_modifier_name)
    if modifier is None:
        problems.append("modifier not created")
    else:
        bpy.ops.geo_node_prompt.toggle_last()
        if modifier.show_viewport or modifier.show_render:
            problems.append("toggle did not turn modifier off")
        bpy.ops.geo_node_prompt.toggle_last()
        if not modifier.show_viewport:
            problems.append("toggle did not turn modifier back on")

    settings.prompt = "아무것도 매칭되지 않는 문장"
    try:
        bpy.ops.geo_node_prompt.generate()
        problems.append("unmatched OFFLINE prompt should cancel with an error")
    except RuntimeError:
        pass  # ERROR 리포트는 bpy.ops 에서 RuntimeError 로 올라온다

    # AI 모드: 인덱스 소켓 키가 JSON 문자열("0", "1")로 와도 조립되어야 한다.
    prefs = bpy.context.preferences.addons["geo_node_prompt"].preferences
    prefs.enable_ai = True
    prefs.api_key = "test-key"
    ai_spec = {
        "name": "AI Wave",
        "exposed_inputs": [{"name": "Amount", "socket_type": "NodeSocketFloat", "default": 0.5}],
        "nodes": [
            {"id": "pos", "type": "GeometryNodeInputPosition"},
            {"id": "sep", "type": "ShaderNodeSeparateXYZ"},
            {"id": "mul", "type": "ShaderNodeMath", "props": {"operation": "MULTIPLY"},
             "defaults": {"1": 2.0}},
            {"id": "comb", "type": "ShaderNodeCombineXYZ"},
            {"id": "setpos", "type": "GeometryNodeSetPosition"},
        ],
        "links": [
            {"from_node": "pos", "from_socket": "Position", "to_node": "sep", "to_socket": "Vector"},
            {"from_node": "sep", "from_socket": "X", "to_node": "mul", "to_socket": "0"},
            {"from_node": "mul", "from_socket": "0", "to_node": "comb", "to_socket": "Z"},
            {"from_node": "GROUP_INPUT", "from_socket": "Geometry", "to_node": "setpos", "to_socket": "Geometry"},
            {"from_node": "comb", "from_socket": "Vector", "to_node": "setpos", "to_socket": "Offset"},
            {"from_node": "setpos", "from_socket": "Geometry", "to_node": "GROUP_OUTPUT", "to_socket": "Geometry"},
        ],
    }
    fake_body = json.dumps({"content": [{"type": "text", "text": "```json\n" + json.dumps(ai_spec) + "\n```"}]})
    fake_response = mock.MagicMock()
    fake_response.__enter__.return_value = io.BytesIO(fake_body.encode("utf-8"))
    settings.mode = "AI"
    settings.prompt = "x 위치에 따라 기울여줘"
    with mock.patch("urllib.request.urlopen", return_value=fake_response) as urlopen:
        result = bpy.ops.geo_node_prompt.generate()
    if result != {"FINISHED"} or not urlopen.called:
        problems.append("AI generate failed: {}".format(settings.last_status))
    elif "경고" in settings.last_status:
        problems.append("AI generate produced warnings: {}".format(settings.last_status))
    else:
        tree = obj.modifiers[settings.last_modifier_name].node_group
        if len(tree.links) != len(ai_spec["links"]):
            problems.append("AI tree has {} links, expected {}".format(len(tree.links), len(ai_spec["links"])))

    addon_utils.disable("geo_node_prompt", default_set=True)
    if hasattr(bpy.types.Scene, "geo_prompt"):
        problems.append("Scene.geo_prompt still registered after disable")
    return problems


def main():
    failed = 0
    for template in TEMPLATES:
        problems, result = check_template(template)
        print("[{}] {:20s} verts={} faces={} instances={}".format(
            "OK " if not problems else "FAIL", template["id"], *result[:3]))
        for p in problems:
            print("       -", p)
        failed += bool(problems)

    problems = check_operators()
    print("[{}] operators (OFFLINE, toggle, AI mock, disable)".format("OK " if not problems else "FAIL"))
    for p in problems:
        print("       -", p)
    failed += bool(problems)

    print("FAILED" if failed else "ALL OK")
    return 1 if failed else 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    # bpy 모듈은 인터프리터 종료 시 정리 과정에서 멈추는 경우가 있어 바로 종료한다.
    os._exit(code)
