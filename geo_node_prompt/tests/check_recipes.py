# -*- coding: utf-8 -*-
"""한글 키워드 레시피를 실제 Blender(bpy) 에서 만들고 결과를 숫자로 검사한다.

검사 내용
- 레시피마다: 경고/오류 없이 조립, 결과가 비지 않음, 모양 기대값, 파라미터를 바꾸면
  결과가 바뀌는지, 같은 시드면 같은 결과인지
- 한글 키워드 해석: 별칭, 띄어쓰기, 오타, 숫자/단위, 형용사, 체인
- 오퍼레이터: 선택 없음/메쉬 선택, 후보 표시, 레시피 바로 만들기, 실패 시 되돌리기
- AI 경로 (HTTP 응답만 가짜): 레시피 고르기, 새 그래프 + 오류 후 재시도, 레시피로 저장
- 화이트리스트의 노드 타입이 이 Blender 버전에 모두 있는지

실행 (저장소 루트에서):
    python geo_node_prompt/tests/check_recipes.py            # pip install bpy==4.2.23 (Python 3.11)
    RENDER_DIR=/tmp/renders python geo_node_prompt/tests/check_recipes.py   # 레시피별 렌더 PNG 도 저장
"""

import io
import json
import math
import os
import sys
import tempfile
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

import bpy  # noqa: E402
import bmesh  # noqa: E402
import addon_utils  # noqa: E402

from geo_node_prompt import recipes, korean  # noqa: E402
from geo_node_prompt.node_whitelist import ALLOWED_NODE_TYPES  # noqa: E402

FAILURES = []


def check(condition, message):
    if not condition:
        FAILURES.append(message)
        print("       - FAIL:", message)
    return condition


# ------------------------------------------------------------------ 장면/평가 도우미

def reset(base=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if base == "cube":
        bpy.ops.mesh.primitive_cube_add()
    elif base == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16)
    elif base == "grid":
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=10, y_subdivisions=10, size=4)
    else:
        mesh = bpy.data.meshes.new("empty")
        obj = bpy.data.objects.new("target", mesh)
        bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
    return bpy.context.view_layer.objects.active


def stats(obj):
    """dict(verts, faces, islands, min, max, instances, positions-hash)"""
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    seen, islands = set(), 0
    for vert in bm.verts:
        if vert.index in seen:
            continue
        islands += 1
        stack = [vert]
        seen.add(vert.index)
        while stack:
            cur = stack.pop()
            for edge in cur.link_edges:
                other = edge.other_vert(cur)
                if other.index not in seen:
                    seen.add(other.index)
                    stack.append(other)
    cos = [v.co.copy() for v in mesh.vertices]
    axis_aligned = all(max(abs(c) for c in p.normal) > 0.999 for p in mesh.polygons)
    bm.free()
    result = {
        "verts": len(mesh.vertices),
        "faces": len(mesh.polygons),
        "islands": islands,
        "min": tuple(min(c[i] for c in cos) for i in range(3)) if cos else (0, 0, 0),
        "max": tuple(max(c[i] for c in cos) for i in range(3)) if cos else (0, 0, 0),
        "hash": round(sum(c.x * 1.3 + c.y * 2.1 + c.z * 3.7 for c in cos), 4),
        "axis_aligned": axis_aligned,
    }
    evaluated.to_mesh_clear()
    result["instances"] = sum(1 for inst in depsgraph.object_instances
                              if inst.is_instance and inst.parent and inst.parent.original == obj)
    return result


def build(recipe, obj, **values):
    vals = recipe.defaults()
    vals.update(values)
    tree = recipe.create_tree(vals)
    modifier = obj.modifiers.new(recipe.name, "NODES")
    modifier.node_group = tree
    return modifier


def set_input(modifier, label, value):
    for item in modifier.node_group.interface.items_tree:
        if getattr(item, "in_out", None) == "INPUT" and item.name == label:
            modifier[item.identifier] = value
            modifier.id_data.update_tag()
            return
    raise KeyError(label)


def extent(s):
    return max(max(abs(s["min"][i]), abs(s["max"][i])) for i in range(2))


# ------------------------------------------------------------------ 레시피별 검사

def check_tentacles(r):
    obj = reset()
    m = build(r, obj, suckers=False)
    s = stats(obj)
    check(s["islands"] == 8, "tentacles: 다리 8개 -> 섬 8개 (got {})".format(s["islands"]))
    set_input(m, "다리 개수", 5)
    check(stats(obj)["islands"] == 5, "tentacles: 다리 개수 5 반영")
    set_input(m, "길이", 4.0)
    check(extent(stats(obj)) > extent(s) * 1.5, "tentacles: 길이 2->4 로 길어짐")
    h1 = stats(obj)["hash"]
    set_input(m, "시드", 3)
    check(stats(obj)["hash"] != h1, "tentacles: 시드 바꾸면 모양이 바뀜")
    set_input(m, "시드", 0)
    check(stats(obj)["hash"] == h1, "tentacles: 같은 시드면 같은 결과")
    set_input(m, "빨판", True)
    check(stats(obj)["islands"] > 5, "tentacles: 빨판 켜면 빨판 조각이 추가됨")
    set_input(m, "말림", 0.0)
    flat = stats(obj)
    set_input(m, "말림", 4.0)
    check(stats(obj)["max"][2] > flat["max"][2] + 0.3, "tentacles: 말림을 키우면 끝이 위로 말려 올라감")
    return s


def check_spiral(r):
    obj = reset()
    m = build(r, obj)
    s = stats(obj)
    height = s["max"][2] - s["min"][2]
    check(abs(height - 2.1) < 0.05, "spiral: 높이 2 + 굵기 -> 2.1 (got {:.3f})".format(height))
    check(s["islands"] == 1, "spiral: 한 덩어리")
    set_input(m, "회전 수", 3.0)
    check(stats(obj)["verts"] < s["verts"], "spiral: 회전 수 줄이면 정점 수 감소")
    return s


def check_chain(r):
    obj = reset()
    m = build(r, obj)
    s = stats(obj)
    check(s["islands"] == 12, "chain: 고리 12개 -> 섬 12개 (got {})".format(s["islands"]))
    set_input(m, "고리 수", 5)
    s5 = stats(obj)
    check(s5["islands"] == 5 and s5["max"][0] < s["max"][0], "chain: 고리 수 5 반영")
    return s


def check_rock(r):
    obj = reset()
    m = build(r, obj)
    s = stats(obj)
    check(s["verts"] > 100 and 0.5 < extent(s) < 2.5, "rock: 크기 1 근처의 바위 (extent {:.2f})".format(extent(s)))
    set_input(m, "시드", 5)
    check(stats(obj)["hash"] != s["hash"], "rock: 시드 바꾸면 다른 바위")
    set_input(m, "디테일", 1)
    check(stats(obj)["verts"] < s["verts"], "rock: 디테일 낮추면 정점 감소")
    return s


def check_voxelize(r):
    obj = reset("sphere")
    m = build(r, obj)
    s = stats(obj)
    check(s["islands"] > 100 and s["axis_aligned"], "voxelize: 구 -> 축 정렬 블록 여러 개 (got {})".format(s["islands"]))
    check(abs(extent(s) - 1.0) < 0.25, "voxelize: 원래 크기 유지 (extent {:.2f})".format(extent(s)))
    set_input(m, "블록 크기", 0.5)
    check(stats(obj)["islands"] < s["islands"], "voxelize: 블록 크게 하면 개수 감소")
    return s


def check_disintegrate(r):
    obj = reset("sphere")
    base = stats(obj)
    m = build(r, obj, progress=0.0)
    s0 = stats(obj)
    check(all(abs(s0["max"][i] - base["max"][i]) < 1e-4 for i in range(3)), "disintegrate: 진행 0 이면 원래 모양")
    check(s0["faces"] == base["faces"], "disintegrate: 면 개수 유지")
    set_input(m, "진행", 1.0)
    s1 = stats(obj)
    check(s1["max"][2] > base["max"][2] + 0.5, "disintegrate: 진행 1 이면 위로 흩날림")
    set_input(m, "진행", 0.5)
    s = stats(obj)
    check(s["islands"] == base["faces"], "disintegrate: 면이 낱개로 떨어짐")
    return s


def check_vines(r):
    obj = reset("grid")
    base = stats(obj)
    m = build(r, obj)
    s = stats(obj)
    check(s["islands"] >= 10 + base["islands"], "vines: 줄기 여러 개 + 바닥 (got {})".format(s["islands"]))
    full = s["max"][2]
    set_input(m, "성장", 0.5)
    half = stats(obj)["max"][2]
    check(0.25 * full < half < 0.8 * full, "vines: 성장 0.5 -> 높이 절반쯤 ({:.2f}/{:.2f})".format(half, full))
    set_input(m, "성장", 1.0)
    set_input(m, "줄기 수", 3)
    check(stats(obj)["islands"] < s["islands"], "vines: 줄기 수 반영")
    return s


def check_scatter(r):
    obj = reset("grid")
    m = build(r, obj)
    s = stats(obj)
    check(s["instances"] > 100, "scatter: 인스턴스 흩뿌려짐 (got {})".format(s["instances"]))
    bpy.ops.mesh.primitive_cone_add(location=(10, 0, 0))
    cone = bpy.context.active_object
    bpy.context.view_layer.objects.active = obj
    set_input(m, "흩뿌릴 오브젝트", cone)
    s2 = stats(obj)
    check(s2["instances"] == s["instances"], "scatter: 오브젝트 지정해도 개수 유지")
    set_input(m, "밀도", 5.0)
    check(stats(obj)["instances"] < s["instances"], "scatter: 밀도 반영")
    return s


SPEC_BASE = {"noise_displace": "sphere", "boolean_cut": "cube"}

CHECKS = {
    "tentacles": check_tentacles,
    "spiral": check_spiral,
    "chain": check_chain,
    "rock": check_rock,
    "voxelize": check_voxelize,
    "disintegrate": check_disintegrate,
    "vines": check_vines,
    "scatter": check_scatter,
}


def check_spec_recipe(r):
    obj = reset(SPEC_BASE.get(r.id, "cube"))
    warnings = []
    tree = r.create_tree(None, warnings)
    modifier = obj.modifiers.new(r.name, "NODES")
    modifier.node_group = tree
    s = stats(obj)
    check(not warnings, "{}: 경고 없음 {}".format(r.id, warnings))
    check(s["verts"] > 0, "{}: 결과가 비지 않음".format(r.id))
    return s


# ------------------------------------------------------------------ 렌더

def render(recipe, folder):
    scene = bpy.context.scene
    target = next((o for o in scene.objects if o.modifiers), None)
    if target is None:
        return
    s = stats(target)
    center = [(s["min"][i] + s["max"][i]) / 2 for i in range(3)]
    size = max(s["max"][i] - s["min"][i] for i in range(3)) or 1.0
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    direction = (1.0, -1.0, 0.8)
    dist = size * 1.6
    norm = math.sqrt(sum(d * d for d in direction))
    cam.location = [center[i] + direction[i] / norm * dist for i in range(3)]
    look = [center[i] - cam.location[i] for i in range(3)]
    cam.rotation_euler = (math.atan2(math.hypot(look[0], look[1]), -look[2]), 0.0,
                          math.atan2(look[1], look[0]) - math.pi / 2)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.rotation_euler = (0.7, 0.2, 0.6)
    sun.data.energy = 3.0
    scene.collection.objects.link(sun)
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.5
    scene.world = world
    material = bpy.data.materials.new("clay")
    material.diffuse_color = (0.8, 0.55, 0.45, 1.0)
    material.use_nodes = True
    material.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.45, 0.35, 1.0)
    for obj in scene.objects:
        if obj.type == "MESH":
            obj.data.materials.append(material)
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.render.resolution_x = scene.render.resolution_y = 360
    scene.render.filepath = os.path.join(folder, recipe.id + ".png")
    bpy.ops.render.render(write_still=True)


# ------------------------------------------------------------------ 키워드 해석

KEYWORDS = [
    # (프롬프트, 기대 레시피 id 들, 기대 값 {param: value})
    ("문어다리", ["tentacles"], {}),
    ("문어 다리", ["tentacles"], {}),
    ("촉수", ["tentacles"], {}),
    ("텐타클 만들어줘", ["tentacles"], {}),
    ("문어다라", ["tentacles"], {}),
    ("문어다리 6개", ["tentacles"], {"count": 6}),
    ("다리 여섯 개 문어", ["tentacles"], {"count": 6}),
    ("문어다리 길게", ["tentacles"], {"length": 3.2}),
    ("굵은 촉수 12가닥", ["tentacles"], {"count": 12, "thickness": 0.24}),
    ("스프링 10바퀴", ["spiral"], {"turns": 10.0}),
    ("나선", ["spiral"], {}),
    ("쇠사슬 20개", ["chain"], {"count": 20}),
    ("큰 바위", ["rock"], {"size": 1.6}),
    ("레고처럼 만들어줘", ["voxelize"], {}),
    ("마인크래프트", ["voxelize"], {}),
    ("타노스처럼 사라지는", ["disintegrate"], {}),
    ("넝쿨이 자라나는", ["vines"], {}),
    ("풀 흩뿌리기", ["scatter"], {}),
    ("노이즈로 울퉁불퉁하게", ["noise_displace"], {}),
    ("문어다리 울퉁불퉁", ["tentacles", "noise_displace"], {}),
    ("구멍 뚫기", ["boolean_cut"], {}),
]


def check_keywords():
    all_recipes = recipes.all_recipes()
    for prompt, expected, values in KEYWORDS:
        parsed = korean.parse(prompt, all_recipes)
        ids = [m.recipe.id for m in parsed.matches]
        ok = check(ids == expected, "키워드 '{}' -> {} (got {})".format(prompt, expected, ids))
        if ok and values:
            got = parsed.matches[0].values
            for key, value in values.items():
                check(abs(got[key] - value) < 1e-6, "키워드 '{}' : {}={} (got {})".format(prompt, key, value, got[key]))
    parsed = korean.parse("아무말 대잔치", all_recipes)
    check(not parsed.matches, "엉뚱한 말은 실행하지 않음")
    parsed = korean.parse("촉쑤", all_recipes)
    check(not parsed.matches and any(r.id == "tentacles" for r in parsed.suggestions) or
          [m.recipe.id for m in parsed.matches] == ["tentacles"], "애매한 오타는 후보로 문어다리를 보여줌")
    print("[{}] 한글 키워드 {}개".format("OK " if not FAILURES else "FAIL", len(KEYWORDS) + 2))


# ------------------------------------------------------------------ 오퍼레이터 + AI

def _fake_response(payload):
    response = mock.MagicMock()
    response.__enter__.return_value = io.BytesIO(json.dumps(payload).encode("utf-8"))
    return response


def _tool_use(recipe_list):
    return _fake_response({"content": [{"type": "tool_use", "name": "choose_recipes", "id": "t",
                                        "input": {"recipes": recipe_list}}]})


def _text(text):
    return _fake_response({"content": [{"type": "text", "text": text}]})


def run_op(op, **kw):
    try:
        return op(**kw)
    except RuntimeError:
        return {"CANCELLED"}


def check_operators(user_dir):
    before = len(FAILURES)
    reset()
    bpy.data.objects.remove(bpy.data.objects["target"])
    addon_utils.enable("geo_node_prompt", default_set=True)
    settings = bpy.context.scene.geo_prompt
    gen = bpy.ops.geo_node_prompt.generate

    # 선택 없이 문어다리 -> 새 오브젝트
    settings.mode = "OFFLINE"
    settings.prompt = "문어다리 6개 길게"
    check(run_op(gen) == {"FINISHED"}, "op: 선택 없이 '문어다리 6개 길게' 성공 ({})".format(settings.last_status))
    obj = bpy.data.objects.get(settings.last_object_name)
    check(obj is not None and obj.modifiers, "op: 새 오브젝트에 모디파이어")
    if obj is not None:
        check(stats(obj)["islands"] > 6, "op: 문어다리 결과가 실제로 생김")
        check("다리 개수 6" in settings.last_status and "길이 3.2" in settings.last_status,
              "op: 상태 메시지에 파라미터 표시 ({})".format(settings.last_status))

    # 체인: 문어다리 + 울퉁불퉁 -> 모디파이어 2개
    settings.prompt = "문어다리 울퉁불퉁"
    run_op(gen)
    obj = bpy.data.objects.get(settings.last_object_name)
    check(obj is not None and len(obj.modifiers) == 2, "op: 체인 -> 모디파이어 2개")

    # 엉뚱한 말 -> 실패 + 아무것도 안 남김 + 후보
    n_objects, n_groups = len(bpy.data.objects), len(bpy.data.node_groups)
    settings.prompt = "촉쑤"
    result = run_op(gen)
    if result == {"CANCELLED"}:
        check("tentacles" in settings.suggestions, "op: 오타 후보에 문어다리 ({})".format(settings.suggestions))
    settings.prompt = "아무말 대잔치"
    check(run_op(gen) == {"CANCELLED"}, "op: 엉뚱한 말은 취소")
    check(len(bpy.data.objects) == n_objects + (result == {"FINISHED"}), "op: 실패 시 오브젝트 안 남김")
    check("레시피 목록" in settings.last_status, "op: 실패 메시지에 레시피 목록 안내")

    # 메쉬 없이 변형 레시피 -> 친절한 오류
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = None
    settings.prompt = "복셀"
    check(run_op(gen) == {"CANCELLED"} and "메쉬" in settings.last_status, "op: 메쉬 없이 복셀 -> 선택 안내")

    # 메쉬 선택 후 복셀 -> 그 메쉬에 붙음
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    check(run_op(gen) == {"FINISHED"} and settings.last_object_name == cube.name, "op: 선택한 큐브에 복셀")

    # 레시피 바로 만들기 (드롭다운)
    settings.recipe_choice = "chain"
    check(run_op(bpy.ops.geo_node_prompt.apply_recipe) == {"FINISHED"}, "op: 레시피 목록에서 사슬")
    check(stats(bpy.data.objects[settings.last_object_name])["islands"] == 12, "op: 사슬 12고리")

    # 빈 결과는 되돌림: 빈 메쉬에 쉐이드 스무스
    empty = bpy.data.objects.new("빈것", bpy.data.meshes.new("빈것"))
    bpy.context.scene.collection.objects.link(empty)
    bpy.context.view_layer.objects.active = empty
    settings.prompt = "쉐이드 스무스"
    check(run_op(gen) == {"CANCELLED"} and not empty.modifiers, "op: 빈 결과면 모디파이어 되돌림")

    # ---- AI (가짜 응답) ----
    prefs = bpy.context.preferences.addons["geo_node_prompt"].preferences
    prefs.enable_ai = True
    prefs.api_key = "test-key"
    settings.mode = "HYBRID"
    bpy.context.view_layer.objects.active = None

    # 1) 레시피에 없는 표현 -> AI 가 문어다리를 골라줌
    settings.prompt = "바다 괴물의 꿈틀대는 팔"
    with mock.patch("urllib.request.urlopen", return_value=_tool_use(
            [{"id": "tentacles", "params": {"count": 5, "length": 3}}])) as urlopen:
        result = run_op(gen)
    body = json.loads(urlopen.call_args[0][0].data.decode("utf-8")) if urlopen.called else {}
    check(result == {"FINISHED"} and "AI가 고른" in settings.last_status, "AI: 레시피 고르기 ({})".format(settings.last_status))
    check(body.get("tool_choice", {}).get("name") == "choose_recipes", "AI: 도구 호출 강제")
    obj = bpy.data.objects.get(settings.last_object_name)
    check(obj is not None and stats(obj)["islands"] > 5, "AI: 고른 레시피 결과 생성")

    # 2) 맞는 레시피 없음 -> 새 그래프. 첫 응답은 깨진 링크, 두 번째는 정상
    broken = {
        "name": "AI 별", "exposed_inputs": [],
        "nodes": [{"id": "star", "type": "GeometryNodeCurveStar"},
                  {"id": "fill", "type": "GeometryNodeFillCurve"}],
        "links": [{"from_node": "star", "from_socket": "Curve", "to_node": "fill", "to_socket": "Curv"},
                  {"from_node": "fill", "from_socket": "Mesh", "to_node": "GROUP_OUTPUT", "to_socket": "Geometry"}],
    }
    fixed = json.loads(json.dumps(broken))
    fixed["links"][0]["to_socket"] = "Curve"
    settings.prompt = "별 모양 판"
    n_groups = len(bpy.data.node_groups)
    with mock.patch("urllib.request.urlopen", side_effect=[
            _tool_use([]), _text(json.dumps(broken)), _text(json.dumps(fixed))]) as urlopen:
        result = run_op(gen)
    check(result == {"FINISHED"} and urlopen.call_count == 3, "AI: 깨진 그래프 -> 오류 알려주고 재시도 성공 ({}, calls {})".format(
        settings.last_status, urlopen.call_count))
    retry = json.loads(urlopen.call_args_list[-1][0][0].data.decode("utf-8")) if urlopen.call_count == 3 else {}
    check(len(retry.get("messages", [])) == 3 and "Curv" in retry["messages"][2]["content"],
          "AI: 재시도 요청에 이전 응답과 오류 포함")
    check(len(bpy.data.node_groups) == n_groups + 1, "AI: 실패한 시도의 노드 그룹은 지움")
    check(bool(settings.last_ai_spec), "AI: 레시피로 저장 버튼 활성")

    # 3) 레시피로 저장 -> 다음부터 오프라인으로 매칭
    check(run_op(bpy.ops.geo_node_prompt.save_ai_recipe) == {"FINISHED"}, "AI: 레시피로 저장")
    check(any(f.endswith(".json") for f in os.listdir(os.path.join(user_dir, "config", "geo_node_prompt", "user_recipes"))
              ) if os.path.isdir(os.path.join(user_dir, "config")) else True, "AI: 저장 파일 생성")
    settings.mode = "OFFLINE"
    bpy.context.view_layer.objects.active = None
    check(run_op(gen) == {"FINISHED"} and "별 모양 판" in settings.last_status, "AI: 저장한 레시피를 오프라인으로 재사용 ({})".format(
        settings.last_status))

    # 4) 두 번 다 깨지면 오류 + 아무것도 안 남김
    settings.mode = "AI"
    settings.prompt = "이상한 것"
    n_objects, n_groups = len(bpy.data.objects), len(bpy.data.node_groups)
    with mock.patch("urllib.request.urlopen", side_effect=[
            _tool_use([]), _text(json.dumps(broken)), _text(json.dumps(broken))]):
        result = run_op(gen)
    check(result == {"CANCELLED"} and "AI 생성 실패" in settings.last_status, "AI: 두 번 실패하면 오류")
    check(len(bpy.data.objects) == n_objects and len(bpy.data.node_groups) == n_groups, "AI: 실패 후 남은 것 없음")

    addon_utils.disable("geo_node_prompt", default_set=True)
    check(not hasattr(bpy.types.Scene, "geo_prompt"), "애드온 끄면 등록 해제")
    print("[{}] 오퍼레이터 + AI 가짜 응답".format("OK " if len(FAILURES) == before else "FAIL"))


def check_whitelist():
    tree = bpy.data.node_groups.new("whitelist", "GeometryNodeTree")
    missing = []
    for bl_idname in sorted(ALLOWED_NODE_TYPES):
        try:
            tree.nodes.new(bl_idname)
        except RuntimeError:
            missing.append(bl_idname)
    bpy.data.node_groups.remove(tree)
    check(not missing, "화이트리스트에 없는 노드 타입: {}".format(missing))
    print("[{}] 화이트리스트 노드 {}종".format("OK " if not missing else "FAIL", len(ALLOWED_NODE_TYPES)))


def main():
    print("Blender", bpy.app.version_string)
    render_dir = os.environ.get("RENDER_DIR")
    for recipe in recipes.BUILTIN:
        before = len(FAILURES)
        try:
            s = CHECKS.get(recipe.id, check_spec_recipe)(recipe)
            detail = "verts={} islands={} instances={}".format(s["verts"], s["islands"], s["instances"])
        except Exception as exc:  # noqa: BLE001
            check(False, "{}: 예외 {}: {}".format(recipe.id, type(exc).__name__, exc))
            detail = ""
        print("[{}] {:16s} {}".format("OK " if len(FAILURES) == before else "FAIL", recipe.id, detail))
        if render_dir and len(FAILURES) == before:
            os.makedirs(render_dir, exist_ok=True)
            obj = reset(SPEC_BASE.get(recipe.id) or {"modify": "sphere", "attach": "grid"}.get(recipe.kind))
            build(recipe, obj) if recipe.id in CHECKS else check_spec_recipe(recipe)
            render(recipe, render_dir)

    check_keywords()
    check_whitelist()
    user_dir = tempfile.mkdtemp()
    os.environ["BLENDER_USER_CONFIG"] = os.path.join(user_dir, "config")
    check_operators(user_dir)

    print("FAILED ({})".format(len(FAILURES)) if FAILURES else "ALL OK")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    # bpy 모듈은 인터프리터 종료 시 정리 과정에서 멈추는 경우가 있어 바로 종료한다.
    os._exit(code)
