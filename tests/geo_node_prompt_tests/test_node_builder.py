# -*- coding: utf-8 -*-
import pytest

import bpy_stub
from geo_node_prompt.node_builder import build_node_tree
from geo_node_prompt.templates import TEMPLATES


def _node_by_type(tree, bl_idname):
    return next(n for n in tree.nodes if n.bl_idname == bl_idname)


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t["id"])
def test_build_every_template_without_warnings(template):
    spec = template["builder"]("")
    obj = bpy_stub.Object("Cube")
    warnings = []

    tree, modifier = build_node_tree(spec, obj, warnings)

    assert warnings == []
    assert tree in bpy_stub.data.node_groups
    assert modifier in obj.modifiers
    assert modifier.type == "NODES"
    assert modifier.node_group is tree
    # 그룹 입/출력 2개 + 스펙 노드
    assert len(tree.nodes) == len(spec["nodes"]) + 2
    assert len(tree.links) == len(spec["links"])
    inputs = tree.interface.names("INPUT")
    assert inputs == ["Geometry"] + [e["name"] for e in spec["exposed_inputs"]]
    assert tree.interface.names("OUTPUT") == ["Geometry"]
    group_output = _node_by_type(tree, "NodeGroupOutput")
    assert any(link.to_node is group_output for link in tree.links)


def test_exposed_input_bounds_applied():
    spec = next(t for t in TEMPLATES if t["id"] == "noise_displace")["builder"]("")
    tree, _ = build_node_tree(spec, bpy_stub.Object("Cube"))
    strength = next(i for i in tree.interface.items_tree if i.name == "Strength")
    assert strength.default_value == 0.2
    assert strength.min_value == 0.0
    assert strength.max_value == 5.0


def test_props_and_defaults_applied():
    spec = next(t for t in TEMPLATES if t["id"] == "scatter")["builder"]("")
    tree, _ = build_node_tree(spec, bpy_stub.Object("Cube"))
    ico = _node_by_type(tree, "GeometryNodeMeshIcoSphere")
    assert ico.inputs["Radius"].default_value == 0.05
    distribute = _node_by_type(tree, "GeometryNodeDistributePointsOnFaces")
    assert distribute.distribute_method == "RANDOM"


def test_bad_node_and_links_become_warnings():
    spec = {
        "name": "Broken",
        "exposed_inputs": [{"name": "Bad", "socket_type": "NodeSocketShader"}],
        "nodes": [
            {"id": "ghost", "type": "GeometryNodeDoesNotExist"},
            {"id": "setpos", "type": "GeometryNodeSetPosition"},
        ],
        "links": [
            {"from_node": "GROUP_INPUT", "from_socket": "Geometry", "to_node": "setpos", "to_socket": "Geometry"},
            {"from_node": "ghost", "from_socket": "Mesh", "to_node": "setpos", "to_socket": "Geometry"},
            {"from_node": "GROUP_INPUT", "from_socket": "Nope", "to_node": "setpos", "to_socket": "Offset"},
            {"from_node": "setpos", "from_socket": "Geometry", "to_node": "GROUP_OUTPUT", "to_socket": "Geometry"},
        ],
    }
    warnings = []
    tree, modifier = build_node_tree(spec, bpy_stub.Object("Cube"), warnings)

    assert len(warnings) == 4
    assert any("Bad" in w for w in warnings)
    assert any("ghost" in w and "GeometryNodeDoesNotExist" in w for w in warnings)
    assert len(tree.links) == 2
    assert modifier.node_group is tree


def test_default_name_and_modifier_name_truncated():
    spec = next(t for t in TEMPLATES if t["id"] == "shade_smooth")["builder"]("")
    spec["name"] = ""
    tree, modifier = build_node_tree(spec, bpy_stub.Object("Cube"))
    assert tree.name == "GeoPrompt"

    spec["name"] = "x" * 100
    _, modifier = build_node_tree(spec, bpy_stub.Object("Cube"))
    assert len(modifier.name) == 63


def test_digit_string_socket_keys_are_indices():
    # JSON 으로 왕복한 스펙은 defaults 키가 "1" 같은 문자열이 된다.
    spec = {
        "name": "Digits",
        "exposed_inputs": [],
        "nodes": [{"id": "math", "type": "ShaderNodeMath", "defaults": {"1": 2.5}}],
        "links": [
            {"from_node": "GROUP_INPUT", "from_socket": "Geometry", "to_node": "GROUP_OUTPUT", "to_socket": "0"},
            {"from_node": "math", "from_socket": "0", "to_node": "math", "to_socket": "0"},
        ],
    }
    warnings = []
    tree, _ = build_node_tree(spec, bpy_stub.Object("Cube"), warnings)
    assert warnings == []
    math = _node_by_type(tree, "ShaderNodeMath")
    assert math.inputs[1].default_value == 2.5
    group_output = _node_by_type(tree, "NodeGroupOutput")
    assert tree.links[0].to_socket is group_output.inputs["Geometry"]
