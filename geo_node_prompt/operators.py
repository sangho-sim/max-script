# -*- coding: utf-8 -*-
"""프롬프트 생성 오퍼레이터, 레시피 바로 만들기, AI 결과 저장, 마지막 생성 모디파이어 on/off 토글."""

import json
import os

import bpy
import bmesh

from . import korean
from . import recipes
from .recipes import GENERATE, ATTACH, MODIFY
from .ai_backend import choose_recipes_via_ai, generate_spec_via_ai
from .node_builder import build_tree, attach_modifier, NodeBuildError
from .graph import GraphError
from .preferences import get_preferences


class ApplyError(Exception):
    pass


# ---------------------------------------------------------------- 대상 오브젝트

def _active_mesh(context):
    obj = context.active_object
    if obj is not None and obj.type == "MESH":
        return obj
    return None


def _new_object(context, name, with_plane):
    mesh = bpy.data.meshes.new(name)
    if with_plane:
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=10, y_segments=10, size=2.0)
        bm.to_mesh(mesh)
        bm.free()
    obj = bpy.data.objects.new(name, mesh)
    (context.collection or context.scene.collection).objects.link(obj)
    obj.location = context.scene.cursor.location
    for other in context.view_layer.objects:
        other.select_set(False)
    obj.select_set(True)
    context.view_layer.objects.active = obj
    return obj


def _evaluated_size(context, obj):
    """(정점 수, 인스턴스 수)"""
    context.view_layer.update()
    depsgraph = context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    verts = len(mesh.vertices) if mesh is not None else 0
    evaluated.to_mesh_clear()
    instances = sum(1 for inst in depsgraph.object_instances
                    if inst.is_instance and inst.parent and inst.parent.original == obj)
    return verts, instances


def _target_for(context, kind, name):
    """레시피 종류에 맞는 대상 오브젝트. (오브젝트, 새로 만들었는지)"""
    active = _active_mesh(context)
    if kind == GENERATE:
        return _new_object(context, name, with_plane=False), True
    if kind == ATTACH:
        if active is not None:
            return active, False
        return _new_object(context, name + " 바닥", with_plane=True), True
    if active is None:
        raise ApplyError("'{}' 은(는) 선택한 메쉬를 바꾸는 레시피예요. 메쉬 오브젝트를 먼저 선택하세요.".format(name))
    return active, False


def _rollback(obj, created, modifiers, trees):
    for modifier in modifiers:
        if obj is not None and not created and modifier.name in obj.modifiers:
            obj.modifiers.remove(modifier)
    for tree in trees:
        if tree.name in bpy.data.node_groups:
            bpy.data.node_groups.remove(tree)
    if created and obj is not None:
        mesh = obj.data
        bpy.data.objects.remove(obj)
        if mesh is not None and mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def apply_matches(context, matches):
    """레시피(들)을 실행해 모디파이어로 붙인다. 실패하면 되돌리고 ApplyError.

    Returns: (오브젝트, 마지막 모디파이어)
    """
    first = matches[0].recipe
    obj, created = _target_for(context, first.kind, first.name)
    modifiers, trees = [], []
    try:
        for match in matches:
            tree = match.recipe.create_tree(match.values)
            trees.append(tree)
            modifiers.append(attach_modifier(tree, obj))
        verts, instances = _evaluated_size(context, obj)
        if verts == 0 and instances == 0:
            raise ApplyError("결과가 비어 있어요. 선택한 오브젝트나 값을 확인해 주세요.")
    except (GraphError, NodeBuildError, ApplyError) as exc:
        _rollback(obj, created, modifiers, trees)
        raise ApplyError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - 예상 못한 오류도 사용자에게 보여주고 되돌린다
        _rollback(obj, created, modifiers, trees)
        raise ApplyError("노드 생성 실패: {}".format(exc)) from exc
    return obj, modifiers[-1]


def spec_uses_input(spec):
    return any(link.get("from_node") == "GROUP_INPUT" and link.get("from_socket") in ("Geometry", 0, "0")
               for link in spec.get("links", []))


def apply_spec(context, spec):
    """AI 가 만든 스펙을 엄격 모드로 조립. 실패하면 되돌리고 ApplyError.

    입력 Geometry 를 쓰지 않는 스펙(새 형태)은 선택과 상관없이 새 오브젝트에 붙인다.
    """
    active = _active_mesh(context) if spec_uses_input(spec) else None
    obj, created = (active, False) if active is not None else (_new_object(context, spec.get("name") or "AI", False), True)
    trees, modifiers = [], []
    try:
        tree = build_tree(spec, strict=True)
        trees.append(tree)
        modifiers.append(attach_modifier(tree, obj))
        verts, instances = _evaluated_size(context, obj)
        if verts == 0 and instances == 0:
            raise ApplyError("결과 지오메트리가 비어 있습니다.")
    except (NodeBuildError, ApplyError) as exc:
        _rollback(obj, created, modifiers, trees)
        raise ApplyError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        _rollback(obj, created, modifiers, trees)
        raise ApplyError("노드 생성 실패: {}".format(exc)) from exc
    return obj, modifiers[-1], (MODIFY if spec_uses_input(spec) else GENERATE)


def _log_unmatched(prompt):
    try:
        folder = bpy.utils.user_resource("CONFIG", path="geo_node_prompt", create=True)
        with open(os.path.join(folder, "unmatched.txt"), "a", encoding="utf-8") as handle:
            handle.write(prompt.replace("\n", " ") + "\n")
    except OSError:
        pass


def _finish(op, settings, obj, modifier, status):
    settings.last_modifier_name = modifier.name
    settings.last_object_name = obj.name
    settings.suggestions = ""
    settings.last_status = status
    op.report({"INFO"}, status)
    return {"FINISHED"}


def _describe(matches, notes):
    parts = []
    for match in matches:
        summary = match.recipe.summary(match.values)
        parts.append("{}{}".format(match.recipe.name, " (" + summary + ")" if summary else ""))
    text = " + ".join(parts)
    if notes:
        text += " · " + ", ".join(notes)
    return text


# ---------------------------------------------------------------- 오퍼레이터

class GEONODEPROMPT_OT_generate(bpy.types.Operator):
    bl_idname = "geo_node_prompt.generate"
    bl_label = "지오메트리 노드 생성"
    bl_description = "입력한 키워드/프롬프트로 지오메트리 노드를 만듭니다. 문어다리, 나선처럼 새 형태를 만드는 레시피는 새 오브젝트를 만듭니다"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        settings = context.scene.geo_prompt
        prompt = settings.prompt.strip()
        settings.suggestions = ""
        settings.last_ai_spec = ""

        if not prompt:
            self.report({"ERROR"}, "키워드를 입력하세요. 예: 문어다리, 나선, 사슬, 바위")
            return {"CANCELLED"}

        mode = settings.mode
        parsed = None
        if mode in {"OFFLINE", "HYBRID"}:
            parsed = korean.parse(prompt, recipes.all_recipes())
            if parsed.matches:
                try:
                    obj, modifier = apply_matches(context, parsed.matches)
                except ApplyError as exc:
                    return self._fail(settings, str(exc))
                return _finish(self, settings, obj, modifier,
                               "레시피: " + _describe(parsed.matches, parsed.notes))

        prefs = get_preferences(context)
        ai_ready = prefs.enable_ai and prefs.api_key
        if mode in {"HYBRID", "AI"} and ai_ready:
            return self._run_ai(context, settings, prefs, prompt)

        if mode == "AI":
            msg = ("AI 모드를 쓰려면 환경설정에서 'AI 사용 허용'을 켜고 API 키를 입력하세요."
                   if not prefs.enable_ai else "환경설정에 Anthropic API 키가 입력되어 있지 않습니다.")
            return self._fail(settings, msg)

        _log_unmatched(prompt)
        suggestions = parsed.suggestions if parsed else []
        settings.suggestions = ",".join(r.id for r in suggestions)
        msg = "'{}' 에 맞는 레시피가 없어요.".format(prompt)
        msg += " 아래 후보를 누르거나" if suggestions else ""
        msg += " 레시피 목록에서 골라 보세요."
        if mode == "HYBRID" and not prefs.enable_ai:
            msg += " (환경설정에서 AI를 켜면 새로 만들어 볼 수도 있어요)"
        return self._fail(settings, msg)

    def _fail(self, settings, message):
        settings.last_status = message
        self.report({"ERROR"}, message)
        return {"CANCELLED"}

    def _run_ai(self, context, settings, prefs, prompt):
        # 1차: AI 가 기존 레시피 중에서 고르게 한다
        catalog = recipes.all_recipes()
        try:
            picks = choose_recipes_via_ai(prompt, catalog, prefs.api_key, prefs.model)
        except ValueError as exc:
            # 고르기 단계가 실패해도 새 그래프 만들기로 넘어간다 (네트워크 문제면 거기서 다시 드러남)
            print("[geo_node_prompt] AI 레시피 선택 실패:", exc)
            picks = []
        if picks:
            matches = []
            for recipe_id, values in picks:
                recipe = recipes.get(recipe_id)
                if recipe is None:
                    continue
                merged = recipe.defaults()
                for key, value in (values or {}).items():
                    param = recipe.param(key)
                    if param is not None and param.kind in ("INT", "FLOAT"):
                        try:
                            merged[key] = param.clamp(float(value))
                        except (TypeError, ValueError):
                            pass
                matches.append(korean.Match(recipe, merged, recipe.name, (0, 0)))
            base = [m for m in matches if m.recipe.kind in (GENERATE, ATTACH)][:1]
            matches = base + [m for m in matches if m.recipe.kind == MODIFY]
            if matches:
                try:
                    obj, modifier = apply_matches(context, matches)
                except ApplyError as exc:
                    return self._fail(settings, str(exc))
                return _finish(self, settings, obj, modifier, "AI가 고른 레시피: " + _describe(matches, []))

        # 2차: 맞는 레시피가 없으면 노드 그래프를 새로 짜게 하고, 실패하면 오류를 알려 한 번 더
        feedback = None
        last_error = ""
        for _attempt in range(2):
            try:
                spec, raw_text = generate_spec_via_ai(prompt, prefs.api_key, prefs.model, prefs.max_tokens,
                                                      feedback=feedback, return_text=True)
                obj, modifier, kind = apply_spec(context, spec)
            except ApplyError as exc:
                last_error = str(exc)
                feedback = (raw_text, last_error)
                continue
            except ValueError as exc:
                # 스펙 검증 실패면 AI 응답 원문과 오류를 돌려줘서 고치게 한다 (네트워크 오류면 원문 없음)
                last_error = str(exc)
                text = getattr(exc, "response_text", None)
                feedback = (text, last_error) if text else None
                continue
            settings.last_ai_spec = json.dumps({"spec": spec, "kind": kind}, ensure_ascii=False)
            settings.last_ai_prompt = prompt
            return _finish(self, settings, obj, modifier, "AI(Claude)가 새로 만든 노드 · '레시피로 저장'으로 다음부터 바로 쓸 수 있어요")
        return self._fail(settings, "AI 생성 실패: {}".format(last_error))


class GEONODEPROMPT_OT_apply_recipe(bpy.types.Operator):
    bl_idname = "geo_node_prompt.apply_recipe"
    bl_label = "레시피 만들기"
    bl_description = "고른 레시피를 기본값으로 바로 만듭니다"
    bl_options = {"REGISTER", "UNDO"}

    recipe_id: bpy.props.StringProperty()

    def execute(self, context):
        settings = context.scene.geo_prompt
        recipe = recipes.get(self.recipe_id or settings.recipe_choice)
        if recipe is None:
            self.report({"ERROR"}, "레시피를 찾을 수 없습니다.")
            return {"CANCELLED"}
        match = korean.Match(recipe, recipe.defaults(), recipe.name, (0, 0))
        try:
            obj, modifier = apply_matches(context, [match])
        except ApplyError as exc:
            settings.last_status = str(exc)
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        return _finish(self, settings, obj, modifier, "레시피: " + _describe([match], []))


class GEONODEPROMPT_OT_save_ai_recipe(bpy.types.Operator):
    bl_idname = "geo_node_prompt.save_ai_recipe"
    bl_label = "레시피로 저장"
    bl_description = "방금 AI가 만든 노드를 이 키워드의 레시피로 저장해서, 다음부터는 AI 없이 바로 만듭니다"

    def execute(self, context):
        settings = context.scene.geo_prompt
        if not settings.last_ai_spec:
            self.report({"ERROR"}, "저장할 AI 결과가 없습니다.")
            return {"CANCELLED"}
        data = json.loads(settings.last_ai_spec)
        name = settings.last_ai_prompt.strip()
        path = recipes.save_user_recipe(name, [name], data["spec"], data.get("kind", MODIFY))
        settings.last_ai_spec = ""
        self.report({"INFO"}, "'{}' 레시피로 저장했어요 ({})".format(name, path))
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
    GEONODEPROMPT_OT_apply_recipe,
    GEONODEPROMPT_OT_save_ai_recipe,
    GEONODEPROMPT_OT_toggle_last,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
