# -*- coding: utf-8 -*-
"""스펙(dict) -> 실제 Blender GeometryNodeTree 조립 + 모디파이어 부착.

templates.py / ai_backend.py 가 만들어내는 스펙 dict 형식은 templates.py
모듈 docstring 을 참고.
"""

import bpy


class NodeBuildError(Exception):
    pass


def _new_interface_socket(tree, name, in_out, socket_type):
    """Blender 4.0+ 의 node_tree.interface API 로 소켓을 하나 추가한다."""
    return tree.interface.new_socket(name=name, in_out=in_out, socket_type=socket_type)


def _apply_exposed_input_bounds(item, spec):
    if "default" in spec and spec["default"] is not None:
        try:
            item.default_value = spec["default"]
        except (TypeError, ValueError, AttributeError):
            pass
    if "min" in spec:
        try:
            item.min_value = spec["min"]
        except AttributeError:
            pass
    if "max" in spec:
        try:
            item.max_value = spec["max"]
        except AttributeError:
            pass


def build_node_tree(spec, obj, warnings=None):
    """spec 으로부터 새 GeometryNodeTree 를 만들고 obj 에 모디파이어로 붙인다.

    Returns: (node_tree, modifier)
    문제가 있는 개별 노드/링크는 건너뛰고 warnings 리스트(주어졌다면)에
    메시지를 추가한다. 치명적인 문제(필수 구조 누락)는 NodeBuildError.
    """
    if warnings is None:
        warnings = []

    name = spec.get("name") or "GeoPrompt"
    tree = bpy.data.node_groups.new(name=name, type="GeometryNodeTree")

    _new_interface_socket(tree, "Geometry", "INPUT", "NodeSocketGeometry")
    _new_interface_socket(tree, "Geometry", "OUTPUT", "NodeSocketGeometry")

    for exposed in spec.get("exposed_inputs", []) or []:
        try:
            item = _new_interface_socket(
                tree, exposed["name"], "INPUT", exposed["socket_type"]
            )
            _apply_exposed_input_bounds(item, exposed)
        except Exception as exc:  # noqa: BLE001 - 사용자 스펙은 신뢰할 수 없음
            warnings.append("입력 '{}' 추가 실패: {}".format(exposed.get("name"), exc))

    group_input = tree.nodes.new("NodeGroupInput")
    group_input.location = (-600, 0)
    group_output = tree.nodes.new("NodeGroupOutput")
    group_output.location = (600, 0)

    node_map = {"GROUP_INPUT": group_input, "GROUP_OUTPUT": group_output}

    for node_spec in spec.get("nodes", []):
        node_id = node_spec["id"]
        try:
            node = tree.nodes.new(node_spec["type"])
        except Exception as exc:  # noqa: BLE001
            warnings.append("노드 '{}'({}) 생성 실패: {}".format(node_id, node_spec["type"], exc))
            continue
        if "location" in node_spec:
            node.location = node_spec["location"]
        for attr, value in (node_spec.get("props") or {}).items():
            try:
                setattr(node, attr, value)
            except Exception as exc:  # noqa: BLE001
                warnings.append("노드 '{}' 속성 '{}' 설정 실패: {}".format(node_id, attr, exc))
        for socket_key, value in (node_spec.get("defaults") or {}).items():
            try:
                node.inputs[socket_key].default_value = value
            except Exception as exc:  # noqa: BLE001
                warnings.append("노드 '{}' 입력 '{}' 기본값 설정 실패: {}".format(node_id, socket_key, exc))
        node_map[node_id] = node

    for link_spec in spec.get("links", []):
        from_node = node_map.get(link_spec["from_node"])
        to_node = node_map.get(link_spec["to_node"])
        if from_node is None or to_node is None:
            warnings.append("링크의 노드를 찾을 수 없습니다: {}".format(link_spec))
            continue
        try:
            from_socket = from_node.outputs[link_spec["from_socket"]]
            to_socket = to_node.inputs[link_spec["to_socket"]]
            tree.links.new(from_socket, to_socket)
        except Exception as exc:  # noqa: BLE001
            warnings.append("링크 생성 실패 {}: {}".format(link_spec, exc))

    modifier = obj.modifiers.new(name=name[:63], type="NODES")
    modifier.node_group = tree

    return tree, modifier
