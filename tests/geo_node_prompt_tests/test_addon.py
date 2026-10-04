# -*- coding: utf-8 -*-
"""애드온 등록/해제와 오퍼레이터 흐름(오프라인/AI 분기)."""

import types

import pytest

import bpy_stub
import geo_node_prompt
from geo_node_prompt import operators


def test_bl_info():
    info = geo_node_prompt.bl_info
    assert info["name"] == "Geo Node Prompt"
    assert info["blender"] >= (4, 0, 0)


def test_register_unregister_roundtrip():
    geo_node_prompt.register()
    assert bpy_stub.registered_classes
    assert hasattr(bpy_stub.Scene, "geo_prompt")
    geo_node_prompt.unregister()
    assert bpy_stub.registered_classes == []
    assert not hasattr(bpy_stub.Scene, "geo_prompt")


def _context(prompt, mode="HYBRID", enable_ai=False, api_key=""):
    settings = types.SimpleNamespace(
        prompt=prompt, mode=mode, last_status="", last_modifier_name="", last_object_name=""
    )
    obj = bpy_stub.Object("Cube")
    bpy_stub.data.objects.append(obj)
    prefs = types.SimpleNamespace(enable_ai=enable_ai, api_key=api_key, model="m", max_tokens=100)
    addons = {"geo_node_prompt": types.SimpleNamespace(preferences=prefs)}
    return types.SimpleNamespace(
        scene=types.SimpleNamespace(geo_prompt=settings),
        active_object=obj,
        preferences=types.SimpleNamespace(addons=addons),
    )


def _run(context):
    op = operators.GEONODEPROMPT_OT_generate()
    return op, op.execute(context)


def test_poll_requires_mesh():
    ctx = _context("x")
    assert operators.GEONODEPROMPT_OT_generate.poll(ctx)
    ctx.active_object.type = "CURVE"
    assert not operators.GEONODEPROMPT_OT_generate.poll(ctx)
    ctx.active_object = None
    assert not operators.GEONODEPROMPT_OT_generate.poll(ctx)


def test_generate_offline_template():
    ctx = _context("울퉁불퉁하게", mode="OFFLINE")
    op, result = _run(ctx)
    assert result == {"FINISHED"}
    assert len(ctx.active_object.modifiers) == 1
    settings = ctx.scene.geo_prompt
    assert settings.last_modifier_name == ctx.active_object.modifiers[0].name
    assert settings.last_object_name == "Cube"
    assert "규칙 템플릿" in settings.last_status


def test_generate_empty_prompt():
    _, result = _run(_context("   "))
    assert result == {"CANCELLED"}


def test_generate_offline_no_match():
    ctx = _context("render a teapot", mode="OFFLINE")
    _, result = _run(ctx)
    assert result == {"CANCELLED"}
    assert len(ctx.active_object.modifiers) == 0


@pytest.mark.parametrize("mode", ["HYBRID", "AI"])
def test_generate_ai_disabled(mode, monkeypatch):
    monkeypatch.setattr(operators, "generate_spec_via_ai", pytest.fail)
    op, result = _run(_context("render a teapot", mode=mode, enable_ai=False))
    assert result == {"CANCELLED"}
    assert "AI 사용 허용" in op.reports[0][1]


def test_generate_ai_missing_key(monkeypatch):
    monkeypatch.setattr(operators, "generate_spec_via_ai", pytest.fail)
    op, result = _run(_context("teapot", mode="AI", enable_ai=True, api_key=""))
    assert result == {"CANCELLED"}
    assert "API 키" in op.reports[0][1]


def test_generate_ai_mode_skips_templates(monkeypatch):
    from geo_node_prompt.templates import TEMPLATES

    calls = []

    def fake_ai(prompt, api_key, model, max_tokens):
        calls.append((prompt, api_key, model, max_tokens))
        return TEMPLATES[3]["builder"](prompt)

    monkeypatch.setattr(operators, "generate_spec_via_ai", fake_ai)
    ctx = _context("울퉁불퉁하게", mode="AI", enable_ai=True, api_key="k")
    _, result = _run(ctx)
    assert result == {"FINISHED"}
    assert calls == [("울퉁불퉁하게", "k", "m", 100)]
    assert "AI" in ctx.scene.geo_prompt.last_status


def test_generate_ai_failure_reported(monkeypatch):
    def fake_ai(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(operators, "generate_spec_via_ai", fake_ai)
    op, result = _run(_context("teapot", mode="HYBRID", enable_ai=True, api_key="k"))
    assert result == {"CANCELLED"}
    assert "boom" in op.reports[0][1]


def test_toggle_last():
    ctx = _context("울퉁불퉁하게", mode="OFFLINE")
    _run(ctx)
    modifier = ctx.active_object.modifiers[0]
    toggle = operators.GEONODEPROMPT_OT_toggle_last()

    assert toggle.execute(ctx) == {"FINISHED"}
    assert modifier.show_viewport is False and modifier.show_render is False
    assert toggle.execute(ctx) == {"FINISHED"}
    assert modifier.show_viewport is True and modifier.show_render is True


def test_toggle_last_missing_object():
    ctx = _context("x")
    ctx.scene.geo_prompt.last_object_name = "Gone"
    assert operators.GEONODEPROMPT_OT_toggle_last().execute(ctx) == {"CANCELLED"}
