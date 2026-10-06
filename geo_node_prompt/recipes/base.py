# -*- coding: utf-8 -*-
"""레시피 공통 정의.

레시피 = 한글 키워드(별칭) + 노출 파라미터 + 노드 트리를 짜는 build 함수.
bpy 는 create_tree() 안에서만 쓰므로, 키워드 매칭 쪽은 Blender 없이도
import 해서 테스트할 수 있다.
"""

# 레시피 종류
GENERATE = "generate"  # 새 형태를 만든다 (선택 오브젝트 없어도 됨, 새 오브젝트에 붙임)
ATTACH = "attach"      # 선택한 메쉬 표면 위에 만든다 (없으면 바닥 평면을 새로 만든다)
MODIFY = "modify"      # 선택한 메쉬를 변형한다 (메쉬가 꼭 있어야 함)


class Param:
    """모디파이어 패널에 노출되는 입력 하나.

    role 은 한글 형용사 해석용 ("길게" -> length 역할 파라미터 x1.6).
    units 는 숫자 뒤에 붙는 단위 ("8개" -> units 에 "개" 가 있는 파라미터).
    """

    def __init__(self, key, label, kind, default, min_value=None, max_value=None,
                 role=None, units=()):
        self.key = key
        self.label = label
        self.kind = kind
        self.default = default
        self.min_value = min_value
        self.max_value = max_value
        self.role = role
        self.units = tuple(units)

    def clamp(self, value):
        if self.kind == "INT":
            value = int(round(value))
        elif self.kind == "FLOAT":
            value = float(value)
        if self.min_value is not None:
            value = max(self.min_value, value)
        if self.max_value is not None:
            value = min(self.max_value, value)
        return value


class Recipe:
    id = ""
    name = ""
    kind = MODIFY
    aliases = ()
    description = ""
    params = ()

    def param(self, key):
        for p in self.params:
            if p.key == key:
                return p
        return None

    def defaults(self):
        return {p.key: p.default for p in self.params}

    def build(self, g, P):  # pragma: no cover - 하위 클래스가 구현
        """g: graph.Graph, P: {param key: 그룹 입력 소켓}. 최종 지오메트리 소켓을 돌려준다."""
        raise NotImplementedError

    def create_tree(self, values=None, warnings=None):
        from ..graph import Graph

        values = dict(self.defaults(), **(values or {}))
        g = Graph(self.name)
        sockets = {}
        for p in self.params:
            sockets[p.key] = g.input(p.label, p.kind, p.clamp(values[p.key]) if p.kind in ("INT", "FLOAT")
                                     else values[p.key], p.min_value, p.max_value)
        g.output(self.build(g, sockets))
        return g.finish()

    def summary(self, values):
        parts = []
        for p in self.params:
            if p.kind in ("INT", "FLOAT") and p.key in values:
                v = values[p.key]
                parts.append("{} {}".format(p.label, v if p.kind == "INT" else round(v, 2)))
        return " · ".join(parts)
