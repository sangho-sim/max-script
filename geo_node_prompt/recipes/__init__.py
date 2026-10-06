# -*- coding: utf-8 -*-
"""레시피 목록.

- 노드 빌더(graph.py)로 짠 튜토리얼식 레시피 (문어다리, 나선, 사슬 ...)
- 예전 스펙 템플릿(templates.py)을 감싼 레시피 (노이즈, 배열, 서브디비전 ...)
- 사용자가 AI 결과를 "레시피로 저장"한 JSON (user_recipes 폴더)
"""

import json
import os

from .base import Recipe, Param, GENERATE, ATTACH, MODIFY  # noqa: F401
from .tentacles import Tentacles
from .shapes import Spiral, Chain, Rock
from .effects import Voxelize, Disintegrate, Vines, Scatter
from .. import templates as _templates


class SpecRecipe(Recipe):
    """templates.py / AI 가 만든 스펙 dict 를 레시피처럼 다룬다."""

    kind = MODIFY

    def __init__(self, recipe_id, name, aliases, spec_builder, description="", kind=MODIFY):
        self.id = recipe_id
        self.name = name
        self.aliases = tuple(aliases)
        self.description = description or name
        self.kind = kind
        self._spec_builder = spec_builder

    def spec(self):
        return self._spec_builder("")

    def create_tree(self, values=None, warnings=None):
        from ..node_builder import build_tree

        return build_tree(self.spec(), warnings if warnings is not None else [], strict=True)


# 예전 템플릿 중 레시피로 다시 만든 것(scatter)은 뺀다.
_SPEC_NAMES = {
    "noise_displace": "울퉁불퉁 노이즈",
    "array": "배열 복제",
    "subdivision_smooth": "부드럽게 (서브디비전)",
    "shade_smooth": "쉐이드 스무스",
    "boolean_cut": "구멍 뚫기 (불리언)",
    "extrude_thickness": "두께 주기",
    "random_delete": "랜덤 삭제",
}

BUILTIN = [Tentacles(), Spiral(), Chain(), Rock(), Voxelize(), Disintegrate(), Vines(), Scatter()]
BUILTIN += [
    SpecRecipe(t["id"], _SPEC_NAMES[t["id"]], t["keywords"], t["builder"], t["label"])
    for t in _templates.TEMPLATES if t["id"] in _SPEC_NAMES
]


def user_recipe_dir():
    """AI 결과를 저장하는 폴더. Blender 밖(테스트)에서는 None."""
    try:
        import bpy
    except ImportError:
        return None
    return bpy.utils.user_resource("CONFIG", path=os.path.join("geo_node_prompt", "user_recipes"), create=True)


def load_user_recipes(folder=None):
    folder = folder or user_recipe_dir()
    recipes = []
    if not folder or not os.path.isdir(folder):
        return recipes
    for filename in sorted(os.listdir(folder)):
        if not filename.endswith(".json"):
            continue
        try:
            with open(os.path.join(folder, filename), encoding="utf-8") as handle:
                data = json.load(handle)
            spec = data["spec"]
            recipes.append(SpecRecipe("user:" + filename[:-5], data["name"], data["aliases"],
                                      lambda _prompt, spec=spec: spec, "저장한 AI 레시피",
                                      kind=data.get("kind", MODIFY)))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return recipes


def save_user_recipe(name, aliases, spec, kind, folder=None):
    folder = folder or user_recipe_dir()
    safe = "".join(ch if ch.isalnum() else "_" for ch in name)[:40] or "recipe"
    path = os.path.join(folder, safe + ".json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"name": name, "aliases": list(aliases), "kind": kind, "spec": spec}, handle,
                  ensure_ascii=False, indent=1)
    return path


def all_recipes():
    return BUILTIN + load_user_recipes()


def get(recipe_id):
    for recipe in all_recipes():
        if recipe.id == recipe_id:
            return recipe
    return None
