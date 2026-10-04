# -*- coding: utf-8 -*-
"""프롬프트 문자열 -> 노드 스펙(dict) 변환을 담당하는 오프라인 규칙 템플릿.

bpy 에 의존하지 않는다 (순수 데이터 생성 + 문자열 매칭). node_builder.py 가
이 모듈이 돌려주는 스펙 dict 를 받아 실제 Blender 노드 트리로 조립한다.

스펙(dict) 형식
----------------
{
    "name": str,                     # 생성될 노드 그룹 / 모디파이어 이름
    "exposed_inputs": [               # Geometry 외에 모디파이어에 노출할 입력들
        {"name": str, "socket_type": str, "default": Any,
         "min": Any(optional), "max": Any(optional)},
        ...
    ],
    "nodes": [
        {"id": str, "type": str, "location": (x, y) optional,
         "props": {attr_name: value} optional,
         "defaults": {socket(str|int): value} optional},
        ...
    ],
    "links": [
        {"from_node": "GROUP_INPUT" | id, "from_socket": str|int,
         "to_node": "GROUP_OUTPUT" | id, "to_socket": str|int},
        ...
    ],
}

"GROUP_INPUT" 의 첫 출력 소켓은 항상 "Geometry" 이고, exposed_inputs 에
적은 이름이 그 뒤를 잇는 출력 소켓 이름이 된다. "GROUP_OUTPUT" 의 입력
소켓은 "Geometry" 하나뿐이다.
"""


def _noise_displace_spec(prompt):
    return {
        "name": "노이즈 디스플레이스",
        "exposed_inputs": [
            {"name": "Strength", "socket_type": "NodeSocketFloat",
             "default": 0.2, "min": 0.0, "max": 5.0},
            # 정수 배율이면 기본 큐브/그리드 정점이 노이즈 격자점에 딱 맞아 평평해진다.
            {"name": "Scale", "socket_type": "NodeSocketFloat",
             "default": 4.3, "min": 0.0, "max": 100.0},
        ],
        "nodes": [
            {"id": "normal", "type": "GeometryNodeInputNormal", "location": (-200, 200)},
            {"id": "noise", "type": "ShaderNodeTexNoise", "location": (-200, 0)},
            {"id": "mul", "type": "ShaderNodeMath", "location": (0, 0),
             "props": {"operation": "MULTIPLY"}},
            {"id": "scale_vec", "type": "ShaderNodeVectorMath", "location": (200, 100),
             "props": {"operation": "SCALE"}},
            {"id": "setpos", "type": "GeometryNodeSetPosition", "location": (400, 200)},
        ],
        "links": [
            {"from_node": "GROUP_INPUT", "from_socket": "Scale", "to_node": "noise", "to_socket": "Scale"},
            {"from_node": "noise", "from_socket": "Fac", "to_node": "mul", "to_socket": 0},
            {"from_node": "GROUP_INPUT", "from_socket": "Strength", "to_node": "mul", "to_socket": 1},
            {"from_node": "normal", "from_socket": "Normal", "to_node": "scale_vec", "to_socket": "Vector"},
            {"from_node": "mul", "from_socket": "Value", "to_node": "scale_vec", "to_socket": "Scale"},
            {"from_node": "GROUP_INPUT", "from_socket": "Geometry", "to_node": "setpos", "to_socket": "Geometry"},
            {"from_node": "scale_vec", "from_socket": "Vector", "to_node": "setpos", "to_socket": "Offset"},
            {"from_node": "setpos", "from_socket": "Geometry", "to_node": "GROUP_OUTPUT", "to_socket": "Geometry"},
        ],
    }


def _scatter_instances_spec(prompt):
    return {
        "name": "포인트 스캐터",
        "exposed_inputs": [
            {"name": "Density", "socket_type": "NodeSocketFloat",
             "default": 50.0, "min": 0.0, "max": 100000.0},
            {"name": "Seed", "socket_type": "NodeSocketInt",
             "default": 0, "min": 0, "max": 100000},
            {"name": "Min Scale", "socket_type": "NodeSocketFloat",
             "default": 0.8, "min": 0.0, "max": 10.0},
            {"name": "Max Scale", "socket_type": "NodeSocketFloat",
             "default": 1.3, "min": 0.0, "max": 10.0},
        ],
        "nodes": [
            {"id": "distribute", "type": "GeometryNodeDistributePointsOnFaces", "location": (-200, 200),
             "props": {"distribute_method": "RANDOM"}},
            {"id": "rot_rand", "type": "FunctionNodeRandomValue", "location": (0, 300),
             "props": {"data_type": "FLOAT_VECTOR"},
             "defaults": {"Min": (0.0, 0.0, 0.0), "Max": (0.0, 0.0, 6.2832)}},
            {"id": "scale_rand", "type": "FunctionNodeRandomValue", "location": (0, 50),
             "props": {"data_type": "FLOAT"}},
            {"id": "combine_scale", "type": "ShaderNodeCombineXYZ", "location": (200, 50)},
            {"id": "instance_src", "type": "GeometryNodeMeshIcoSphere", "location": (0, -150),
             "defaults": {"Radius": 0.05, "Subdivisions": 1}},
            {"id": "instance", "type": "GeometryNodeInstanceOnPoints", "location": (400, 150)},
            {"id": "join", "type": "GeometryNodeJoinGeometry", "location": (600, 0)},
        ],
        "links": [
            {"from_node": "GROUP_INPUT", "from_socket": "Geometry", "to_node": "distribute", "to_socket": "Mesh"},
            {"from_node": "GROUP_INPUT", "from_socket": "Density", "to_node": "distribute", "to_socket": "Density"},
            {"from_node": "GROUP_INPUT", "from_socket": "Seed", "to_node": "distribute", "to_socket": "Seed"},
            {"from_node": "GROUP_INPUT", "from_socket": "Min Scale", "to_node": "scale_rand", "to_socket": 2},
            {"from_node": "GROUP_INPUT", "from_socket": "Max Scale", "to_node": "scale_rand", "to_socket": 3},
            {"from_node": "scale_rand", "from_socket": "Value", "to_node": "combine_scale", "to_socket": "X"},
            {"from_node": "scale_rand", "from_socket": "Value", "to_node": "combine_scale", "to_socket": "Y"},
            {"from_node": "scale_rand", "from_socket": "Value", "to_node": "combine_scale", "to_socket": "Z"},
            {"from_node": "distribute", "from_socket": "Points", "to_node": "instance", "to_socket": "Points"},
            {"from_node": "instance_src", "from_socket": "Mesh", "to_node": "instance", "to_socket": "Instance"},
            {"from_node": "rot_rand", "from_socket": "Value", "to_node": "instance", "to_socket": "Rotation"},
            {"from_node": "combine_scale", "from_socket": "Vector", "to_node": "instance", "to_socket": "Scale"},
            {"from_node": "GROUP_INPUT", "from_socket": "Geometry", "to_node": "join", "to_socket": "Geometry"},
            {"from_node": "instance", "from_socket": "Instances", "to_node": "join", "to_socket": "Geometry"},
            {"from_node": "join", "from_socket": "Geometry", "to_node": "GROUP_OUTPUT", "to_socket": "Geometry"},
        ],
    }


def _array_along_axis_spec(prompt):
    return {
        "name": "축 방향 배열",
        "exposed_inputs": [
            {"name": "Count", "socket_type": "NodeSocketInt",
             "default": 5, "min": 1, "max": 1000},
            {"name": "Offset", "socket_type": "NodeSocketVector",
             "default": (1.0, 0.0, 0.0)},
        ],
        "nodes": [
            {"id": "line", "type": "GeometryNodeMeshLine", "location": (-200, 100),
             "props": {"mode": "OFFSET"}},
            {"id": "instance", "type": "GeometryNodeInstanceOnPoints", "location": (0, 0)},
            {"id": "realize", "type": "GeometryNodeRealizeInstances", "location": (200, 0)},
        ],
        "links": [
            {"from_node": "GROUP_INPUT", "from_socket": "Count", "to_node": "line", "to_socket": "Count"},
            {"from_node": "GROUP_INPUT", "from_socket": "Offset", "to_node": "line", "to_socket": "Offset"},
            {"from_node": "line", "from_socket": "Mesh", "to_node": "instance", "to_socket": "Points"},
            {"from_node": "GROUP_INPUT", "from_socket": "Geometry", "to_node": "instance", "to_socket": "Instance"},
            {"from_node": "instance", "from_socket": "Instances", "to_node": "realize", "to_socket": "Geometry"},
            {"from_node": "realize", "from_socket": "Geometry", "to_node": "GROUP_OUTPUT", "to_socket": "Geometry"},
        ],
    }


def _subdivision_smooth_spec(prompt):
    return {
        "name": "서브디비전 스무스",
        "exposed_inputs": [
            {"name": "Level", "socket_type": "NodeSocketInt",
             "default": 2, "min": 0, "max": 6},
        ],
        "nodes": [
            {"id": "subsurf", "type": "GeometryNodeSubdivisionSurface", "location": (0, 0)},
        ],
        "links": [
            {"from_node": "GROUP_INPUT", "from_socket": "Geometry", "to_node": "subsurf", "to_socket": "Mesh"},
            {"from_node": "GROUP_INPUT", "from_socket": "Level", "to_node": "subsurf", "to_socket": "Level"},
            {"from_node": "subsurf", "from_socket": "Mesh", "to_node": "GROUP_OUTPUT", "to_socket": "Geometry"},
        ],
    }


def _shade_smooth_spec(prompt):
    return {
        "name": "쉐이드 스무스",
        "exposed_inputs": [
            {"name": "Smooth", "socket_type": "NodeSocketBool", "default": True},
        ],
        "nodes": [
            {"id": "smooth", "type": "GeometryNodeSetShadeSmooth", "location": (0, 0)},
        ],
        "links": [
            {"from_node": "GROUP_INPUT", "from_socket": "Geometry", "to_node": "smooth", "to_socket": "Geometry"},
            {"from_node": "GROUP_INPUT", "from_socket": "Smooth", "to_node": "smooth", "to_socket": "Shade Smooth"},
            {"from_node": "smooth", "from_socket": "Geometry", "to_node": "GROUP_OUTPUT", "to_socket": "Geometry"},
        ],
    }


def _boolean_cut_spec(prompt):
    return {
        "name": "불리언 컷",
        "exposed_inputs": [
            {"name": "Cutter Object", "socket_type": "NodeSocketObject", "default": None},
        ],
        "nodes": [
            {"id": "objinfo", "type": "GeometryNodeObjectInfo", "location": (-200, -100),
             "props": {"transform_space": "RELATIVE"}},
            {"id": "boolean", "type": "GeometryNodeMeshBoolean", "location": (0, 0),
             "props": {"operation": "DIFFERENCE"}},
        ],
        "links": [
            {"from_node": "GROUP_INPUT", "from_socket": "Cutter Object", "to_node": "objinfo", "to_socket": "Object"},
            {"from_node": "GROUP_INPUT", "from_socket": "Geometry", "to_node": "boolean", "to_socket": "Mesh 1"},
            {"from_node": "objinfo", "from_socket": "Geometry", "to_node": "boolean", "to_socket": "Mesh 2"},
            {"from_node": "boolean", "from_socket": "Mesh", "to_node": "GROUP_OUTPUT", "to_socket": "Geometry"},
        ],
    }


def _extrude_thickness_spec(prompt):
    return {
        "name": "익스트루드 두께",
        "exposed_inputs": [
            {"name": "Thickness", "socket_type": "NodeSocketFloat",
             "default": 0.05, "min": -10.0, "max": 10.0},
        ],
        "nodes": [
            {"id": "extrude", "type": "GeometryNodeExtrudeMesh", "location": (0, 0),
             "props": {"mode": "FACES"}},
        ],
        "links": [
            {"from_node": "GROUP_INPUT", "from_socket": "Geometry", "to_node": "extrude", "to_socket": "Mesh"},
            {"from_node": "GROUP_INPUT", "from_socket": "Thickness", "to_node": "extrude", "to_socket": "Offset Scale"},
            {"from_node": "extrude", "from_socket": "Mesh", "to_node": "GROUP_OUTPUT", "to_socket": "Geometry"},
        ],
    }


def _random_delete_spec(prompt):
    return {
        "name": "랜덤 삭제",
        "exposed_inputs": [
            {"name": "Ratio", "socket_type": "NodeSocketFloat",
             "default": 0.3, "min": 0.0, "max": 1.0},
            {"name": "Seed", "socket_type": "NodeSocketInt",
             "default": 0, "min": 0, "max": 100000},
        ],
        "nodes": [
            {"id": "rand", "type": "FunctionNodeRandomValue", "location": (-200, 0),
             "props": {"data_type": "FLOAT"}},
            {"id": "compare", "type": "FunctionNodeCompare", "location": (0, 0),
             "props": {"data_type": "FLOAT", "operation": "LESS_THAN"}},
            {"id": "delete", "type": "GeometryNodeDeleteGeometry", "location": (200, 0),
             "props": {"domain": "FACE"}},
        ],
        "links": [
            {"from_node": "GROUP_INPUT", "from_socket": "Seed", "to_node": "rand", "to_socket": "Seed"},
            {"from_node": "rand", "from_socket": "Value", "to_node": "compare", "to_socket": "A"},
            {"from_node": "GROUP_INPUT", "from_socket": "Ratio", "to_node": "compare", "to_socket": "B"},
            {"from_node": "GROUP_INPUT", "from_socket": "Geometry", "to_node": "delete", "to_socket": "Geometry"},
            {"from_node": "compare", "from_socket": "Result", "to_node": "delete", "to_socket": "Selection"},
            {"from_node": "delete", "from_socket": "Geometry", "to_node": "GROUP_OUTPUT", "to_socket": "Geometry"},
        ],
    }


# id, 사람이 읽을 라벨, 매칭 키워드(한/영 혼용), 스펙 빌더 함수
TEMPLATES = [
    {
        "id": "noise_displace",
        "label": "노이즈 디스플레이스 (울퉁불퉁하게)",
        "keywords": ["노이즈", "울퉁불퉁", "요철", "범피", "bumpy", "noise", "displace", "organic"],
        "builder": _noise_displace_spec,
    },
    {
        "id": "scatter",
        "label": "포인트 스캐터 / 인스턴스 흩뿌리기",
        "keywords": ["스캐터", "흩뿌", "뿌려", "풀", "자갈", "scatter", "instance", "인스턴스"],
        "builder": _scatter_instances_spec,
    },
    {
        "id": "array",
        "label": "축 방향 배열/복제",
        "keywords": ["배열", "복제", "줄줄이", "array", "duplicate", "반복 배치"],
        "builder": _array_along_axis_spec,
    },
    {
        "id": "subdivision_smooth",
        "label": "서브디비전으로 둥글게",
        "keywords": ["서브디비전", "둥글게", "부드럽게", "매끄럽게", "subdivision", "subdivide"],
        "builder": _subdivision_smooth_spec,
    },
    {
        "id": "shade_smooth",
        "label": "쉐이드 스무스",
        "keywords": ["쉐이드 스무스", "쉐이딩", "매끈해 보이게", "shade smooth", "shading"],
        "builder": _shade_smooth_spec,
    },
    {
        "id": "boolean_cut",
        "label": "불리언으로 구멍/컷",
        "keywords": ["불리언", "구멍", "뚫", "도려", "컷", "boolean", "cut", "hole"],
        "builder": _boolean_cut_spec,
    },
    {
        "id": "extrude_thickness",
        "label": "익스트루드로 두께 주기",
        "keywords": ["두께", "돌출", "익스트루드", "extrude", "thickness", "shell", "solidify"],
        "builder": _extrude_thickness_spec,
    },
    {
        "id": "random_delete",
        "label": "랜덤하게 일부 삭제",
        "keywords": ["랜덤 삭제", "부서진", "깨진", "랜덤하게 없애", "random delete", "broken", "fragment"],
        "builder": _random_delete_spec,
    },
]


def match_template(prompt):
    """prompt 문자열과 가장 잘 맞는 템플릿을 찾는다.

    점수(일치한 키워드 개수)가 가장 높은 템플릿을 돌려주고, 하나도 맞지
    않으면 None 을 돌려준다. 동점일 때는 TEMPLATES 리스트에서 먼저 나온
    쪽을 우선한다.
    """
    lowered = prompt.lower()
    best = None
    best_score = 0
    for template in TEMPLATES:
        score = sum(1 for kw in template["keywords"] if kw.lower() in lowered)
        if score > best_score:
            best_score = score
            best = template
    return best
