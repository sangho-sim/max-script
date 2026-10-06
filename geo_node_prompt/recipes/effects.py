# -*- coding: utf-8 -*-
"""선택한 메쉬에 거는 효과 레시피: 복셀화, 분해, 덩굴 성장, 흩뿌리기."""

from .base import Recipe, Param, MODIFY, ATTACH


class Voxelize(Recipe):
    id = "voxelize"
    name = "복셀화"
    kind = MODIFY
    aliases = ("복셀", "복셀화", "레고", "블록화", "블록", "픽셀화", "마인크래프트", "큐브화",
               "voxel", "voxelize", "lego", "minecraft")
    description = "메쉬를 볼륨으로 바꾼 뒤 격자 점마다 큐브를 놓아 블록(레고) 모양으로 만든다."
    params = (
        Param("block", "블록 크기", "FLOAT", 0.2, 0.01, 10.0, role="size"),
        Param("gap", "틈", "FLOAT", 0.05, 0.0, 0.9),
    )

    def build(self, g, P):
        g.frame("1. 메쉬 -> 볼륨 (속이 찬 형태로)")
        volume = g.node("GeometryNodeMeshToVolume",
                        props={"resolution_mode": ("VOXEL_SIZE", "Resolution Mode", "Size")},
                        Mesh=g.geometry, Voxel_Size=g.math("MULTIPLY", P["block"], 0.5)).out()

        g.frame("2. 볼륨 안에 격자 점 (Distribute Points in Volume: Grid)")
        spacing = g.combine(P["block"], P["block"], P["block"])
        points = g.node("GeometryNodeDistributePointsInVolume",
                        props={"mode": ("DENSITY_GRID", "Mode", "Grid")},
                        Volume=volume, Spacing=spacing, Threshold=0.1).out()

        g.frame("3. 점마다 큐브 (틈만큼 작게)")
        side = g.math("MULTIPLY", P["block"], g.math("SUBTRACT", 1.0, P["gap"]))
        cube = g.node("GeometryNodeMeshCube", Size=g.combine(side, side, side)).out()
        blocks = g.node("GeometryNodeInstanceOnPoints", Points=points, Instance=cube).out()
        return g.node("GeometryNodeRealizeInstances", Geometry=blocks).out()


class Disintegrate(Recipe):
    id = "disintegrate"
    name = "분해 효과"
    kind = MODIFY
    aliases = ("분해", "분해 효과", "흩어지는", "흩날리는", "흩날리", "부서지는", "디졸브", "산산조각",
               "사라지는", "타노스", "가루", "disintegrate", "dissolve", "shatter")
    description = "아래에서 위로 면이 하나씩 떨어져 작아지며 날아가는 분해 효과. '진행'을 0->1 로 애니메이션."
    params = (
        Param("progress", "진행", "FLOAT", 0.5, 0.0, 1.0),
        Param("distance", "날아가는 거리", "FLOAT", 1.5, 0.0, 100.0, role="length"),
        Param("spread", "퍼짐", "FLOAT", 0.3, 0.01, 2.0, role="wiggle"),
        Param("seed", "시드", "INT", 0, 0, 100000, role="seed"),
    )

    def build(self, g, P):
        g.frame("1. 면을 낱개로 떼어냄 (Split Edges)")
        mesh = g.node("GeometryNodeSplitEdges", Mesh=g.geometry).out()

        g.frame("2. 면마다 진행값: 높이 + 노이즈로 순서 정하기")
        bbox = g.node("GeometryNodeBoundBox", Geometry=g.geometry)
        pos = g.node("GeometryNodeInputPosition").out()
        z = g.node("ShaderNodeSeparateXYZ", Vector=pos).out("Z")
        zmin = g.node("ShaderNodeSeparateXYZ", Vector=bbox.out("Min")).out("Z")
        zmax = g.node("ShaderNodeSeparateXYZ", Vector=bbox.out("Max")).out("Z")
        height01 = g.node("ShaderNodeMapRange", Value=z, From_Min=zmin, From_Max=zmax).out("Result")
        jitter = g.node("FunctionNodeRandomValue", props={"data_type": "FLOAT"},
                        Min=0.0, Max=1.0, Seed=P["seed"]).out("Value")
        order = g.math("ADD", g.math("MULTIPLY", height01, 0.8), g.math("MULTIPLY", jitter, 0.2))
        # progress 0 이면 모두 0, 1 이면 모두 1 이 되도록 sweep 범위를 넓힌다
        sweep = g.math("MULTIPLY", P["progress"], g.math("ADD", 1.0, P["spread"]))
        local = g.math("DIVIDE", g.math("SUBTRACT", sweep, order), P["spread"])
        local = g.node("ShaderNodeClamp", Value=local, Min=0.0, Max=1.0).out()
        mesh, amount = g.capture(mesh, local, "FACE")

        g.frame("3. 진행된 면은 작아지고 위로 흩날림")
        mesh = g.node("GeometryNodeScaleElements", props={"domain": "FACE"}, Geometry=mesh,
                      Scale=g.math("SUBTRACT", 1.0, amount)).out()
        noise = g.node("ShaderNodeTexNoise", props={"noise_dimensions": "4D"},
                       Vector=g.node("GeometryNodeInputPosition").out(), W=P["seed"], Scale=1.5).out("Color")
        drift = g.vmath("ADD", g.vmath("SUBTRACT", noise, (0.5, 0.5, 0.5)), (0.0, 0.0, 0.6))
        offset = g.vmath("SCALE", drift, scale=g.math("MULTIPLY", g.math("POWER", amount, 1.5), P["distance"]))
        return g.node("GeometryNodeSetPosition", Geometry=mesh, Offset=offset).out()


class Vines(Recipe):
    id = "vines"
    name = "덩굴 성장"
    kind = ATTACH
    aliases = ("덩굴", "넝쿨", "덩굴 성장", "자라나는", "성장", "뿌리", "줄기", "이끼줄기", "vine", "vines", "growth", "grow")
    description = "선택한 메쉬 표면에서 구불구불한 줄기가 자라난다. '성장'을 0->1 로 애니메이션."
    params = (
        Param("count", "줄기 수", "INT", 12, 1, 2000, role="count", units=("개", "가닥", "줄기", "줄")),
        Param("length", "길이", "FLOAT", 1.5, 0.01, 100.0, role="length", units=("m", "미터")),
        Param("growth", "성장", "FLOAT", 1.0, 0.0, 1.0),
        Param("wiggle", "구불거림", "FLOAT", 0.6, 0.0, 10.0, role="wiggle"),
        Param("thickness", "굵기", "FLOAT", 0.03, 0.001, 2.0, role="thickness"),
        Param("seed", "시드", "INT", 0, 0, 100000, role="seed"),
    )

    def build(self, g, P):
        g.frame("1. 표면에 정확히 N개의 시작점 (면적으로 밀도 계산)")
        area = g.node("GeometryNodeInputMeshFaceArea").out()
        total = g.node("GeometryNodeAttributeStatistic", props={"data_type": "FLOAT", "domain": "FACE"},
                       Geometry=g.geometry, Attribute=area).out("Sum")
        density = g.math("DIVIDE", P["count"], g.math("MAXIMUM", total, 0.0001))
        dist = g.node("GeometryNodeDistributePointsOnFaces", Mesh=g.geometry, Density=density, Seed=P["seed"])
        along_normal = g.node("FunctionNodeAlignEulerToVector", props={"axis": "Z"},
                              Vector=dist.out("Normal")).out()

        g.frame("2. 줄기 하나 = 법선 방향 직선 커브")
        line = g.node("GeometryNodeCurvePrimitiveLine", End=g.combine(z=P["length"])).out()
        line = g.node("GeometryNodeResampleCurve", Curve=line, Count=48).out()
        stems = g.node("GeometryNodeInstanceOnPoints", Points=dist.out("Points"), Instance=line,
                       Rotation=along_normal).out()
        stems = g.node("GeometryNodeRealizeInstances", Geometry=stems).out()

        g.frame("3. 노이즈로 구불구불 (뿌리는 고정)")
        factor = g.node("GeometryNodeSplineParameter").out("Factor")
        noise = g.node("ShaderNodeTexNoise", props={"noise_dimensions": "4D"},
                       Vector=g.node("GeometryNodeInputPosition").out(), W=P["seed"], Scale=1.2, Detail=2.0)
        offset = g.vmath("SCALE", g.vmath("SUBTRACT", noise.out("Color"), (0.5, 0.5, 0.5)),
                         scale=g.math("MULTIPLY", g.math("MULTIPLY", factor, P["wiggle"]), P["length"]))
        stems = g.node("GeometryNodeSetPosition", Geometry=stems, Offset=offset).out()

        g.frame("4. 성장: Trim Curve 로 끝을 잘라냄 (0 -> 1 애니메이션)")
        stems = g.node("GeometryNodeTrimCurve", props={"mode": "FACTOR"}, Curve=stems, End=P["growth"]).out()

        g.frame("5. 끝으로 갈수록 가늘게 + 굵기 입히기")
        factor2 = g.node("GeometryNodeSplineParameter").out("Factor")
        taper = g.node("ShaderNodeMapRange", Value=factor2, To_Min=1.0, To_Max=0.15).out("Result")
        stems = g.node("GeometryNodeSetCurveRadius", Curve=stems,
                       Radius=g.math("MULTIPLY", taper, P["thickness"])).out()
        profile = g.node("GeometryNodeCurvePrimitiveCircle", Resolution=8, Radius=1.0).out()
        mesh = g.node("GeometryNodeCurveToMesh", Curve=stems, Profile_Curve=profile, Fill_Caps=True).out()
        mesh = g.node("GeometryNodeSetShadeSmooth", Geometry=mesh).out()

        joined = g.node("GeometryNodeJoinGeometry")
        g.link(mesh, joined.inp("Geometry"))
        g.link(g.geometry, joined.inp("Geometry"))
        return joined.out()


class Scatter(Recipe):
    id = "scatter"
    name = "흩뿌리기"
    kind = ATTACH
    aliases = ("흩뿌리기", "흩뿌려", "흩뿌", "뿌려", "스캐터", "풀", "자갈", "잔디", "나무 심기", "돌 흩뿌리기",
               "scatter", "instance", "인스턴스")
    description = "선택한 메쉬 표면에 오브젝트(없으면 작은 구)를 무작위 크기·회전으로 흩뿌린다."
    params = (
        Param("density", "밀도", "FLOAT", 50.0, 0.0, 100000.0, role="count", units=("개",)),
        Param("min_scale", "최소 크기", "FLOAT", 0.8, 0.0, 10.0),
        Param("max_scale", "최대 크기", "FLOAT", 1.3, 0.0, 10.0, role="size"),
        Param("instance", "흩뿌릴 오브젝트", "OBJECT", None),
        Param("seed", "시드", "INT", 0, 0, 100000, role="seed"),
    )

    def build(self, g, P):
        g.frame("1. 표면에 점 뿌리기 (법선 방향 회전 포함)")
        dist = g.node("GeometryNodeDistributePointsOnFaces", props={"distribute_method": "RANDOM"},
                      Mesh=g.geometry, Density=P["density"], Seed=P["seed"])

        g.frame("2. 흩뿌릴 모양: 오브젝트가 비어 있으면 작은 구")
        info = g.node("GeometryNodeObjectInfo", props={"transform_space": "ORIGINAL"},
                      Object=P["instance"], As_Instance=False)
        has_object = g.node("FunctionNodeCompare", props={"data_type": "INT", "operation": "GREATER_THAN"},
                            A=g.node("GeometryNodeAttributeDomainSize", Geometry=info.out("Geometry"))
                            .out("Point Count"), B=0).out("Result")
        ball = g.node("GeometryNodeMeshIcoSphere", Radius=0.05, Subdivisions=1).out()
        shape = g.node("GeometryNodeSwitch", props={"input_type": "GEOMETRY"}, Switch=has_object,
                       False_=ball, True_=info.out("Geometry")).out()

        g.frame("3. 무작위 크기와 Z축 회전")
        scale = g.node("FunctionNodeRandomValue", props={"data_type": "FLOAT"},
                       Min=P["min_scale"], Max=P["max_scale"], Seed=P["seed"]).out("Value")
        inst = g.node("GeometryNodeInstanceOnPoints", Points=dist.out("Points"), Instance=shape,
                      Rotation=dist.out("Rotation"), Scale=g.combine(scale, scale, scale)).out()
        spin = g.node("FunctionNodeRandomValue", props={"data_type": "FLOAT_VECTOR"},
                      Min=(0.0, 0.0, 0.0), Max=(0.0, 0.0, 6.2832), Seed=g.math("ADD", P["seed"], 7.0)).out("Value")
        inst = g.node("GeometryNodeRotateInstances", Instances=inst, Rotation=spin).out()

        joined = g.node("GeometryNodeJoinGeometry")
        g.link(inst, joined.inp("Geometry"))
        g.link(g.geometry, joined.inp("Geometry"))
        return joined.out()
