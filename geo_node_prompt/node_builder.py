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


def _socket_key(key):
    """JSON 은 dict 키를 항상 문자열로 만들므로 "0" 같은 키는 인덱스로 바꾼다."""
    if isinstance(key, str) and key.isdigit():
        return int(key)
    return key


_ALIASES = {"Fac": "Factor", "Factor": "Fac"}


def _find_socket(sockets, key):
    """이름(또는 인덱스)으로 소켓 찾기. 이름은 활성 소켓 우선, 버전별 별칭 허용."""
    if isinstance(key, int):
        return sockets[key]
    for name in (key, _ALIASES.get(key)):
        if name is None:
            continue
        for socket in sockets:
            if socket.enabled and (socket.name == name or socket.identifier == name):
                return socket
    return sockets[key]


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


def build_tree(spec, warnings=None, strict=False):
    """spec 으로부터 새 GeometryNodeTree 를 만든다.

    문제가 있는 개별 노드/링크는 건너뛰고 warnings 리스트(주어졌다면)에
    메시지를 추가한다. strict=True 이면 노드 생성 실패나 링크 실패를
    경고 대신 NodeBuildError 로 올린다 (AI 결과 검증용).
    """
    if warnings is None:
        warnings = []

    def problem(message):
        if strict:
            bpy.data.node_groups.remove(tree)
            raise NodeBuildError(message)
        warnings.append(message)

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
            problem("입력 '{}' 추가 실패: {}".format(exposed.get("name"), exc))

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
            problem("노드 '{}'({}) 생성 실패: {}".format(node_id, node_spec["type"], exc))
            continue
        if "location" in node_spec:
            node.location = node_spec["location"]
        for attr, value in (node_spec.get("props") or {}).items():
            try:
                setattr(node, attr, value)
            except Exception as exc:  # noqa: BLE001
                problem("노드 '{}' 속성 '{}' 설정 실패: {}".format(node_id, attr, exc))
        for socket_key, value in (node_spec.get("defaults") or {}).items():
            try:
                node.inputs[_socket_key(socket_key)].default_value = value
            except Exception as exc:  # noqa: BLE001
                problem("노드 '{}' 입력 '{}' 기본값 설정 실패: {}".format(node_id, socket_key, exc))
        node_map[node_id] = node

    for link_spec in spec.get("links", []):
        from_node = node_map.get(link_spec["from_node"])
        to_node = node_map.get(link_spec["to_node"])
        if from_node is None or to_node is None:
            problem("링크의 노드를 찾을 수 없습니다: {}".format(link_spec))
            continue
        try:
            from_socket = _find_socket(from_node.outputs, _socket_key(link_spec["from_socket"]))
            to_socket = _find_socket(to_node.inputs, _socket_key(link_spec["to_socket"]))
            link = tree.links.new(from_socket, to_socket)
            if not link.is_valid:
                raise ValueError("유효하지 않은 연결")
        except Exception as exc:  # noqa: BLE001
            problem("링크 생성 실패 {}: {}".format(link_spec, exc))

    if not group_output.inputs[0].is_linked:
        problem("GROUP_OUTPUT 의 Geometry 에 연결된 것이 없습니다.")

    return tree


def attach_modifier(tree, obj):
    modifier = obj.modifiers.new(name=tree.name[:63], type="NODES")
    modifier.node_group = tree
    return modifier


def build_node_tree(spec, obj, warnings=None):
    """spec 으로부터 새 GeometryNodeTree 를 만들고 obj 에 모디파이어로 붙인다.

    Returns: (node_tree, modifier)
    """
    tree = build_tree(spec, warnings)
    return tree, attach_modifier(tree, obj)
