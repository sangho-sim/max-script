# -*- coding: utf-8 -*-
"""AI가 생성한 JSON 스펙에서 허용되는 노드 타입 목록.

node_builder.py 와 ai_backend.py 가 공유한다. bpy 에 의존하지 않으므로
Blender 밖에서도(단위 테스트) import 할 수 있다.
"""

ALLOWED_NODE_TYPES = {
    # 메쉬 생성/변형
    "GeometryNodeMeshBoolean",
    "GeometryNodeSubdivisionSurface",
    "GeometryNodeSubdivideMesh",
    "GeometryNodeExtrudeMesh",
    "GeometryNodeDeleteGeometry",
    "GeometryNodeSetShadeSmooth",
    "GeometryNodeSetPosition",
    "GeometryNodeTransform",
    "GeometryNodeMergeByDistance",
    "GeometryNodeJoinGeometry",
    # 포인트/인스턴스
    "GeometryNodeDistributePointsOnFaces",
    "GeometryNodeInstanceOnPoints",
    "GeometryNodeRotateInstances",
    "GeometryNodeScaleInstances",
    "GeometryNodeTranslateInstances",
    "GeometryNodeRealizeInstances",
    "GeometryNodeDuplicateElements",
    "GeometryNodeMeshLine",
    # 1차 도형
    "GeometryNodeMeshCube",
    "GeometryNodeMeshUVSphere",
    "GeometryNodeMeshIcoSphere",
    "GeometryNodeMeshCylinder",
    "GeometryNodeMeshCone",
    "GeometryNodeMeshGrid",
    # 입력/유틸리티
    "GeometryNodeObjectInfo",
    "GeometryNodeInputPosition",
    "GeometryNodeInputNormal",
    "GeometryNodeInputIndex",
    "GeometryNodeSwitch",
    "FunctionNodeRandomValue",
    "FunctionNodeCompare",
    "ShaderNodeMath",
    "ShaderNodeVectorMath",
    "ShaderNodeSeparateXYZ",
    "ShaderNodeCombineXYZ",
    "ShaderNodeTexNoise",
    # 그룹 I/O (항상 존재, 화이트리스트엔 참고용으로만 포함)
    "NodeGroupInput",
    "NodeGroupOutput",
}

# AI JSON 스펙에서 exposed_inputs 에 쓸 수 있는 소켓 타입
ALLOWED_SOCKET_TYPES = {
    "NodeSocketFloat",
    "NodeSocketInt",
    "NodeSocketBool",
    "NodeSocketVector",
    "NodeSocketColor",
    "NodeSocketObject",
    "NodeSocketString",
    "NodeSocketGeometry",
}
