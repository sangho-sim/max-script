# -*- coding: utf-8 -*-
"""문어다리(촉수): 커브 한 가닥을 말고 가늘게 만든 뒤 원형으로 복제, 노이즈로 꿈틀거리게."""

from .base import Recipe, Param, GENERATE


class Tentacles(Recipe):
    id = "tentacles"
    name = "문어다리"
    kind = GENERATE
    aliases = ("문어다리", "문어 다리", "촉수", "텐타클", "오징어다리", "오징어 다리", "문어", "오징어",
               "tentacle", "tentacles", "octopus")
    description = "원형으로 퍼진 문어 다리(촉수). 끝으로 갈수록 가늘고 말려 있으며 꿈틀거린다."
    params = (
        Param("count", "다리 개수", "INT", 8, 1, 64, role="count", units=("개", "가닥", "다리")),
        Param("length", "길이", "FLOAT", 2.0, 0.1, 50.0, role="length", units=("m", "미터")),
        Param("thickness", "굵기", "FLOAT", 0.15, 0.005, 5.0, role="thickness"),
        Param("wiggle", "꿈틀거림", "FLOAT", 0.7, 0.0, 10.0, role="wiggle"),
        Param("curl", "말림", "FLOAT", 2.4, 0.0, 12.0, role="curl"),
        Param("suckers", "빨판", "BOOL", True),
        Param("seed", "시드", "INT", 0, 0, 100000, role="seed"),
    )

    def build(self, g, P):
        g.frame("1. 다리 한 가닥 뼈대 (직선 커브를 잘게 나눔)")
        end = g.combine(x=P["length"])
        line = g.node("GeometryNodeCurvePrimitiveLine", End=end)
        curve = g.node("GeometryNodeResampleCurve", Curve=line, Count=64).out()

        g.frame("2. 끝부분만 위로 돌돌 말리게 (다리 62% 지점을 중심으로 회전)")
        factor = g.node("GeometryNodeSplineParameter").out("Factor")
        tip = g.math("DIVIDE", g.math("MAXIMUM", g.math("SUBTRACT", factor, 0.62), 0.0), 0.38)
        angle = g.math("MULTIPLY", g.math("POWER", tip, 1.3), g.math("MULTIPLY", P["curl"], -1.0))
        pivot = g.combine(x=g.math("MULTIPLY", P["length"], 0.62))
        pos = g.node("GeometryNodeInputPosition").out()
        rotate = g.node("ShaderNodeVectorRotate", props={"rotation_type": "Y_AXIS"},
                        Vector=pos, Center=pivot, Angle=angle)
        curve = g.node("GeometryNodeSetPosition", Geometry=curve, Position=rotate).out()

        g.frame("3. 뿌리는 굵고 끝은 가늘게 (Set Curve Radius)")
        taper = g.node("ShaderNodeMapRange", Value=factor, To_Min=1.0, To_Max=0.08).out("Result")
        curve = g.node("GeometryNodeSetCurveRadius", Curve=curve,
                       Radius=g.math("MULTIPLY", taper, P["thickness"])).out()

        g.frame("4. 원형으로 다리 복제 (바깥 방향으로 정렬)")
        ring_radius = g.math("MULTIPLY", P["thickness"], 1.5)
        circle = g.node("GeometryNodeMeshCircle", Vertices=P["count"], Radius=ring_radius).out()
        outward = g.node("FunctionNodeAlignEulerToVector", props={"axis": "X"},
                         Vector=g.node("GeometryNodeInputPosition").out()).out()
        legs = g.node("GeometryNodeInstanceOnPoints", Points=circle, Instance=curve, Rotation=outward).out()
        legs = g.node("GeometryNodeRealizeInstances", Geometry=legs).out()

        g.frame("5. 노이즈로 꿈틀거림 (끝으로 갈수록 크게)")
        factor2 = g.node("GeometryNodeSplineParameter").out("Factor")
        noise = g.node("ShaderNodeTexNoise", props={"noise_dimensions": "4D"},
                       Vector=g.node("GeometryNodeInputPosition").out(), W=P["seed"], Scale=0.9, Detail=1.0)
        centered = g.vmath("SUBTRACT", noise.out("Color"), (0.5, 0.5, 0.5))
        amount = g.math("MULTIPLY", g.math("MULTIPLY", factor2, P["wiggle"]), P["length"])
        offset = g.vmath("SCALE", centered, scale=amount)
        legs = g.node("GeometryNodeSetPosition", Geometry=legs, Offset=offset).out()

        g.frame("6. 굵기 입히기 (Curve to Mesh)")
        profile = g.node("GeometryNodeCurvePrimitiveCircle", Resolution=16, Radius=1.0).out()
        mesh = g.node("GeometryNodeCurveToMesh", Curve=legs, Profile_Curve=profile, Fill_Caps=True).out()

        g.frame("7. 빨판 (다리 아랫면에 작은 구를 줄지어)")
        # 점으로 바꾸면 Spline Parameter 를 못 쓰므로 커브에서 미리 저장(Capture)해 둔다
        legs_c, tip = g.capture(legs, g.node("GeometryNodeSplineParameter").out("Factor"), "POINT")
        points = g.node("GeometryNodeCurveToPoints", props={"mode": "COUNT"}, Curve=legs_c, Count=22)
        radius = g.node("GeometryNodeInputRadius").out()
        # 끝부분 빨판은 빼서 자연스럽게
        keep = g.node("FunctionNodeCompare", props={"data_type": "FLOAT", "operation": "LESS_THAN"},
                      A=tip, B=0.85).out("Result")
        down = g.vmath("SCALE", (0.0, 0.0, -1.0), scale=g.math("MULTIPLY", radius, 0.8))
        pts = g.node("GeometryNodeSetPosition", Geometry=points.out("Points"), Offset=down).out()
        cup = g.node("GeometryNodeMeshUVSphere", Segments=10, Rings=6, Radius=1.0).out()
        size = g.math("MULTIPLY", radius, 0.45)
        cups = g.node("GeometryNodeInstanceOnPoints", Points=pts, Selection=keep, Instance=cup,
                      Scale=g.combine(size, size, g.math("MULTIPLY", size, 0.5))).out()
        cups = g.node("GeometryNodeRealizeInstances", Geometry=cups).out()
        # True 는 파이썬 예약어라 True_ 로 넘긴다 (끝의 _ 는 무시됨)
        cups = g.node("GeometryNodeSwitch", props={"input_type": "GEOMETRY"}, Switch=P["suckers"], True_=cups)
        joined = g.node("GeometryNodeJoinGeometry")
        g.link(cups.out(), joined.inp("Geometry"))
        g.link(mesh, joined.inp("Geometry"))

        g.frame("8. 매끈하게")
        return g.node("GeometryNodeSetShadeSmooth", Geometry=joined).out()
