# -*- coding: utf-8 -*-
"""레시피가 노드 트리를 짤 때 쓰는 작은 빌더 헬퍼.

templates.py 의 스펙 dict 와 달리 바로 bpy 노드를 만든다. 소켓 이름이
틀리면 즉시 GraphError 를 던지므로, 버전마다 바뀐 이름은 테스트에서 바로
드러난다. 버전별로 이름이 다른 소켓은 _SOCKET_ALIASES 에서 흡수한다.

    g = Graph("문어다리")
    count = g.input("다리 개수", "INT", 8, 1, 64)
    circle = g.node("GeometryNodeMeshCircle", Vertices=count, Radius=0.3)
    g.output(circle.out("Mesh"))
"""

import bpy


class GraphError(Exception):
    pass


_SOCKET_TYPES = {
    "FLOAT": "NodeSocketFloat",
    "INT": "NodeSocketInt",
    "BOOL": "NodeSocketBool",
    "VECTOR": "NodeSocketVector",
    "OBJECT": "NodeSocketObject",
    "GEOMETRY": "NodeSocketGeometry",
}

# 같은 소켓이 Blender 버전마다 다른 이름을 가질 때 (예: 5.0 에서 Noise 의 Fac -> Factor)
_SOCKET_ALIASES = {
    "Fac": ("Factor",),
    "Factor": ("Fac",),
}


def _find_socket(sockets, key, node, kind):
    if isinstance(key, int):
        enabled = [s for s in sockets if s.enabled]
        if key < len(enabled):
            return enabled[key]
        raise GraphError("{} '{}' 에 {}번째 {} 소켓이 없습니다".format(node.bl_idname, node.name, key, kind))
    for name in (key,) + _SOCKET_ALIASES.get(key, ()):
        for socket in sockets:
            if socket.enabled and (socket.name == name or socket.identifier == name):
                return socket
    names = [s.name for s in sockets if s.enabled]
    raise GraphError("{} 에 '{}' {} 소켓이 없습니다 (있는 것: {})".format(node.bl_idname, key, kind, names))


class Node:
    def __init__(self, graph, node):
        self.graph = graph
        self.node = node

    def out(self, key=0):
        return _find_socket(self.node.outputs, key, self.node, "출력")

    def inp(self, key):
        return _find_socket(self.node.inputs, key, self.node, "입력")

    def set(self, **inputs):
        for key, value in inputs.items():
            self.graph.feed(self.inp(key.rstrip("_").replace("_", " ")), value)
        return self


class Graph:
    """GeometryNodeTree 하나를 만든다. 입력 Geometry 와 출력 Geometry 는 항상 있다."""

    def __init__(self, name):
        self.tree = bpy.data.node_groups.new(name=name, type="GeometryNodeTree")
        iface = self.tree.interface
        iface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        iface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        self._group_in = self.tree.nodes.new("NodeGroupInput")
        self._group_out = self.tree.nodes.new("NodeGroupOutput")
        self._frame = None
        self._frames = []
        self._column = 0
        self._row = 0

    # ---- 그룹 입력/출력 ------------------------------------------------
    @property
    def geometry(self):
        return self._group_in.outputs[0]

    def input(self, name, kind, default=None, min_value=None, max_value=None):
        item = self.tree.interface.new_socket(name=name, in_out="INPUT", socket_type=_SOCKET_TYPES[kind])
        if default is not None:
            item.default_value = default
        if min_value is not None:
            item.min_value = min_value
        if max_value is not None:
            item.max_value = max_value
        return _find_socket(self._group_in.outputs, name, self._group_in, "출력")

    def output(self, socket):
        self.link(socket, self._group_out.inputs[0])

    # ---- 노드 ---------------------------------------------------------
    def frame(self, label):
        """이후에 만드는 노드를 묶을 프레임(튜토리얼의 한 단계)을 시작한다."""
        frame = self.tree.nodes.new("NodeFrame")
        frame.label = label
        frame.label_size = 16
        self._frame = frame
        self._frames.append(frame)
        self._column += 1
        self._row = 0
        return frame

    def node(self, bl_idname, label=None, props=None, **inputs):
        try:
            raw = self.tree.nodes.new(bl_idname)
        except RuntimeError as exc:
            raise GraphError("노드 타입 '{}' 을 만들 수 없습니다: {}".format(bl_idname, exc)) from exc
        raw.location = (self._column * 260 - 200, -self._row * 180)
        self._row += 1
        if label:
            raw.label = label
        if self._frame is not None:
            raw.parent = self._frame
        for attr, value in (props or {}).items():
            set_mode(raw, attr, value)
        node = Node(self, raw)
        node.set(**inputs)
        return node

    def link(self, from_socket, to_socket):
        link = self.tree.links.new(from_socket, to_socket)
        if not link.is_valid:
            raise GraphError("연결 실패: {}.{} -> {}.{}".format(
                from_socket.node.name, from_socket.name, to_socket.node.name, to_socket.name))
        return link

    def feed(self, socket, value):
        """value 가 소켓이면 연결하고, 아니면 기본값으로 넣는다."""
        if isinstance(value, Node):
            value = value.out()
        if isinstance(value, bpy.types.NodeSocket):
            self.link(value, socket)
        else:
            try:
                socket.default_value = value
            except (TypeError, ValueError, AttributeError) as exc:
                raise GraphError("{}.{} 에 값 {!r} 을 넣을 수 없습니다: {}".format(
                    socket.node.bl_idname, socket.name, value, exc)) from exc

    # ---- 자주 쓰는 조합 ------------------------------------------------
    def math(self, operation, a, b=None, c=None):
        node = self.node("ShaderNodeMath", props={"operation": operation})
        for index, value in enumerate((a, b, c)):
            if value is not None:
                self.feed(node.inp(index), value)
        return node.out()

    def vmath(self, operation, a, b=None, scale=None):
        node = self.node("ShaderNodeVectorMath", props={"operation": operation})
        self.feed(node.inp(0), a)
        if b is not None:
            self.feed(node.inp(1), b)
        if scale is not None:
            self.feed(node.inp("Scale"), scale)
        return node.out()

    def combine(self, x=0.0, y=0.0, z=0.0):
        return self.node("ShaderNodeCombineXYZ", X=x, Y=y, Z=z).out()

    def capture(self, geometry, value, domain, data_type="FLOAT"):
        """Capture Attribute (4.2+ 다중 항목 API). (geometry 출력, 값 출력) 을 돌려준다."""
        node = self.node("GeometryNodeCaptureAttribute", props={"domain": domain})
        node.node.capture_items.new(data_type, "Value")
        self.feed(node.inp("Geometry"), geometry)
        self.feed(node.inp("Value"), value)
        return node.out("Geometry"), node.out("Value")

    def finish(self):
        """프레임 크기를 맞추고 그룹 입출력 노드를 양 끝에 둔다."""
        self._group_in.location = (-520, 0)
        self._group_out.location = ((self._column + 1) * 260, 0)
        return self.tree


def set_mode(node, attr, value):
    """노드 속성(enum)을 설정한다. 5.0 처럼 속성이 메뉴 소켓으로 바뀐 경우도 처리.

    attr 는 4.x 속성 이름, value 는 (속성 값, 메뉴 소켓 이름, 메뉴 항목 이름)
    튜플이거나 그냥 값.
    """
    if isinstance(value, tuple):
        prop_value, socket_name, menu_value = value
    else:
        prop_value, socket_name, menu_value = value, None, None
    if hasattr(node, attr):
        try:
            setattr(node, attr, prop_value)
        except (TypeError, ValueError, AttributeError) as exc:
            raise GraphError("{}.{} = {!r} 설정 실패: {}".format(node.bl_idname, attr, prop_value, exc)) from exc
        return
    if socket_name is not None:
        socket = _find_socket(node.inputs, socket_name, node, "입력")
        socket.default_value = menu_value
        return
    raise GraphError("{} 에 '{}' 속성이 없습니다".format(node.bl_idname, attr))
