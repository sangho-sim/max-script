# -*- coding: utf-8 -*-
"""Blender 밖에서 geo_node_prompt 를 import/실행하기 위한 최소 bpy 스텁.

애드온이 실제로 쓰는 API 만 흉내 낸다: bpy.types 의 베이스 클래스들,
bpy.props, bpy.utils.register_class, bpy.data.node_groups/objects,
GeometryNodeTree 의 interface/nodes/links, 오브젝트 모디파이어.

그룹 입력/출력 노드의 소켓은 트리 interface 에 선언된 이름만 허용해
(실제 Blender 와 같게) 스펙의 GROUP_INPUT/GROUP_OUTPUT 소켓 이름 오류를
잡아낸다. 그 외 노드의 소켓 이름은 Blender 버전마다 달라 검증하지 않는다.
"""

import types as _pytypes


# ---------------------------------------------------------------- bpy.props
def _prop(*args, **kwargs):
    return ("_stub_property", kwargs)


props = _pytypes.SimpleNamespace(
    StringProperty=_prop,
    EnumProperty=_prop,
    BoolProperty=_prop,
    IntProperty=_prop,
    FloatProperty=_prop,
    PointerProperty=_prop,
)


# ---------------------------------------------------------------- bpy.types
class _Registrable:
    pass


class Operator(_Registrable):
    def __init__(self):
        self.reports = []

    def report(self, level, message):
        self.reports.append((set(level), message))


class Panel(_Registrable):
    pass


class PropertyGroup(_Registrable):
    pass


class AddonPreferences(_Registrable):
    pass


class Scene:
    pass


types = _pytypes.SimpleNamespace(
    Operator=Operator,
    Panel=Panel,
    PropertyGroup=PropertyGroup,
    AddonPreferences=AddonPreferences,
    Scene=Scene,
)


# ---------------------------------------------------------------- bpy.utils
registered_classes = []


def _register_class(cls):
    if cls in registered_classes:
        raise ValueError("이미 등록된 클래스: {}".format(cls.__name__))
    registered_classes.append(cls)


def _unregister_class(cls):
    if cls not in registered_classes:
        raise RuntimeError("등록되지 않은 클래스: {}".format(cls.__name__))
    registered_classes.remove(cls)


utils = _pytypes.SimpleNamespace(
    register_class=_register_class,
    unregister_class=_unregister_class,
)


# ---------------------------------------------------------------- node tree
class Socket:
    def __init__(self, node, name):
        self.node = node
        self.name = name
        self.default_value = None


class Sockets:
    """이름(str) 또는 인덱스(int)로 접근하는 소켓 컬렉션.

    strict 가 아니면 처음 보는 이름/인덱스의 소켓을 그 자리에서 만든다.
    """

    def __init__(self, node, names_fn=None):
        self._node = node
        self._names_fn = names_fn
        self._items = []

    @property
    def strict(self):
        return self._names_fn is not None

    def _sync(self):
        if self._names_fn is None:
            return
        names = self._names_fn()
        by_name = {s.name: s for s in self._items}
        self._items = [by_name.get(n) or Socket(self._node, n) for n in names]

    def __getitem__(self, key):
        self._sync()
        if isinstance(key, int):
            if key < 0:
                raise IndexError(key)
            while not self.strict and len(self._items) <= key:
                self._items.append(Socket(self._node, "Socket_{}".format(len(self._items))))
            return self._items[key]
        for socket in self._items:
            if socket.name == key:
                return socket
        if self.strict:
            raise KeyError("bpy_prop_collection[key]: key \"{}\" not found".format(key))
        socket = Socket(self._node, key)
        self._items.append(socket)
        return socket

    def __len__(self):
        self._sync()
        return len(self._items)


class Node:
    def __init__(self, tree, bl_idname):
        self.id_data = tree
        self.bl_idname = bl_idname
        self.location = (0.0, 0.0)
        if bl_idname == "NodeGroupInput":
            self.inputs = Sockets(self, names_fn=lambda: [])
            self.outputs = Sockets(self, names_fn=lambda: tree.interface.names("INPUT"))
        elif bl_idname == "NodeGroupOutput":
            self.inputs = Sockets(self, names_fn=lambda: tree.interface.names("OUTPUT"))
            self.outputs = Sockets(self, names_fn=lambda: [])
        else:
            self.inputs = Sockets(self)
            self.outputs = Sockets(self)


class Nodes(list):
    def __init__(self, tree):
        super().__init__()
        self._tree = tree

    def new(self, bl_idname):
        # bpy 스텁이 sys.modules 에 들어간 뒤에 패키지를 import 해야 하므로 지연 import
        from geo_node_prompt.node_whitelist import ALLOWED_NODE_TYPES

        if bl_idname not in ALLOWED_NODE_TYPES:
            raise RuntimeError("Node type {} undefined".format(bl_idname))
        node = Node(self._tree, bl_idname)
        self.append(node)
        return node


class Link:
    def __init__(self, from_socket, to_socket):
        self.from_socket = from_socket
        self.to_socket = to_socket
        self.from_node = from_socket.node
        self.to_node = to_socket.node


class Links(list):
    def new(self, from_socket, to_socket):
        link = Link(from_socket, to_socket)
        self.append(link)
        return link


class InterfaceSocket:
    def __init__(self, name, in_out, socket_type):
        self.name = name
        self.in_out = in_out
        self.socket_type = socket_type
        self.default_value = None
        self.min_value = None
        self.max_value = None


class Interface:
    SOCKET_TYPES = {
        "NodeSocketFloat", "NodeSocketInt", "NodeSocketBool", "NodeSocketVector",
        "NodeSocketColor", "NodeSocketObject", "NodeSocketString", "NodeSocketGeometry",
    }

    def __init__(self):
        self.items_tree = []

    def new_socket(self, name, in_out="INPUT", socket_type="NodeSocketFloat"):
        if in_out not in {"INPUT", "OUTPUT"}:
            raise TypeError("in_out 은 INPUT/OUTPUT 이어야 합니다: {}".format(in_out))
        if socket_type not in self.SOCKET_TYPES:
            raise TypeError("알 수 없는 socket_type: {}".format(socket_type))
        item = InterfaceSocket(name, in_out, socket_type)
        self.items_tree.append(item)
        return item

    def names(self, in_out):
        return [item.name for item in self.items_tree if item.in_out == in_out]


class GeometryNodeTree:
    def __init__(self, name):
        self.name = name
        self.bl_idname = "GeometryNodeTree"
        self.interface = Interface()
        self.nodes = Nodes(self)
        self.links = Links()


# ---------------------------------------------------------------- objects
class Modifier:
    def __init__(self, name, type):
        self.name = name
        self.type = type
        self.node_group = None
        self.show_viewport = True
        self.show_render = True


class Modifiers(list):
    def new(self, name, type):
        modifier = Modifier(name, type)
        self.append(modifier)
        return modifier

    def get(self, name, default=None):
        for modifier in self:
            if modifier.name == name:
                return modifier
        return default


class Object:
    def __init__(self, name, type="MESH"):
        self.name = name
        self.type = type
        self.modifiers = Modifiers()


class _NamedCollection(list):
    def get(self, name, default=None):
        for item in self:
            if item.name == name:
                return item
        return default


class _NodeGroups(_NamedCollection):
    def new(self, name, type):
        if type != "GeometryNodeTree":
            raise TypeError("스텁은 GeometryNodeTree 만 지원합니다: {}".format(type))
        tree = GeometryNodeTree(name)
        self.append(tree)
        return tree


data = _pytypes.SimpleNamespace(node_groups=_NodeGroups(), objects=_NamedCollection())


def reset():
    """테스트 사이에 전역 상태(등록 클래스, bpy.data)를 비운다."""
    registered_classes.clear()
    data.node_groups.clear()
    data.objects.clear()
    if hasattr(Scene, "geo_prompt"):
        del Scene.geo_prompt
