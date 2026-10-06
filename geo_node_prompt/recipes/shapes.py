# -*- coding: utf-8 -*-
"""새 형태를 만드는 레시피: 나선(스프링), 사슬, 바위."""

import math

from .base import Recipe, Param, GENERATE


class Spiral(Recipe):
    id = "spiral"
    name = "나선"
    kind = GENERATE
    aliases = ("나선", "스프링", "용수철", "코일", "소용돌이", "나사", "똬리", "spiral", "spring", "coil", "helix")
    description = "Curve Spiral 에 굵기를 입힌 스프링/나선."
    params = (
        Param("turns", "회전 수", "FLOAT", 6.0, 0.1, 200.0, role="count", units=("바퀴", "번", "회전")),
        Param("height", "높이", "FLOAT", 2.0, 0.0, 100.0, role="length", units=("m", "미터")),
        Param("radius", "반지름", "FLOAT", 0.5, 0.0, 50.0, role="size"),
        Param("end_radius", "끝 반지름", "FLOAT", 0.5, 0.0, 50.0),
        Param("thickness", "굵기", "FLOAT", 0.05, 0.001, 5.0, role="thickness"),
    )

    def build(self, g, P):
        g.frame("1. 나선 커브 (Curve Spiral)")
        spiral = g.node("GeometryNodeCurveSpiral", Resolution=32, Rotations=P["turns"],
                        Start_Radius=P["radius"], End_Radius=P["end_radius"], Height=P["height"]).out()
        g.frame("2. 굵기 입히기 (원형 단면으로 Curve to Mesh)")
        profile = g.node("GeometryNodeCurvePrimitiveCircle", Resolution=12, Radius=P["thickness"]).out()
        mesh = g.node("GeometryNodeCurveToMesh", Curve=spiral, Profile_Curve=profile, Fill_Caps=True).out()
        return g.node("GeometryNodeSetShadeSmooth", Geometry=mesh).out()


class Chain(Recipe):
    id = "chain"
    name = "사슬"
    kind = GENERATE
    aliases = ("사슬", "쇠사슬", "체인", "체인링크", "chain")
    description = "타원 고리를 번갈아 90도씩 돌려 X축으로 이어 붙인 사슬."
    params = (
        Param("count", "고리 수", "INT", 12, 1, 1000, role="count", units=("개", "고리", "마디")),
        Param("size", "고리 크기", "FLOAT", 0.2, 0.01, 10.0, role="size"),
        Param("thickness", "굵기", "FLOAT", 0.04, 0.002, 2.0, role="thickness"),
    )

    def build(self, g, P):
        g.frame("1. 고리 하나 (늘린 원 + 원형 단면)")
        ring = g.node("GeometryNodeCurvePrimitiveCircle", Resolution=24, Radius=P["size"]).out()
        ring = g.node("GeometryNodeTransform", Geometry=ring, Scale=(1.6, 1.0, 1.0)).out()
        profile = g.node("GeometryNodeCurvePrimitiveCircle", Resolution=10, Radius=P["thickness"]).out()
        link_mesh = g.node("GeometryNodeCurveToMesh", Curve=ring, Profile_Curve=profile).out()

        g.frame("2. 고리 위치: 안쪽 길이만큼 간격 (2 x (1.6r - 굵기))")
        pitch = g.math("MULTIPLY", g.math("SUBTRACT", g.math("MULTIPLY", P["size"], 1.6), P["thickness"]), 2.0)
        points = g.node("GeometryNodeMeshLine", props={"mode": "OFFSET"}, Count=P["count"],
                        Offset=g.combine(x=pitch)).out()

        g.frame("3. 홀수 번째 고리는 X축으로 90도 회전")
        index = g.node("GeometryNodeInputIndex").out()
        odd = g.math("FLOORED_MODULO", index, 2.0)
        rotation = g.combine(x=g.math("MULTIPLY", odd, math.pi / 2))
        chain = g.node("GeometryNodeInstanceOnPoints", Points=points, Instance=link_mesh, Rotation=rotation).out()
        chain = g.node("GeometryNodeRealizeInstances", Geometry=chain).out()
        return g.node("GeometryNodeSetShadeSmooth", Geometry=chain).out()


class Rock(Recipe):
    id = "rock"
    name = "바위"
    kind = GENERATE
    aliases = ("바위", "암석", "돌멩이", "로우폴리 바위", "바윗돌", "돌덩이", "rock", "stone", "boulder")
    description = "Ico Sphere 를 Voronoi/Noise 로 깎아 만든 로우폴리 바위."
    params = (
        Param("size", "크기", "FLOAT", 1.0, 0.01, 100.0, role="size"),
        Param("roughness", "울퉁불퉁함", "FLOAT", 0.4, 0.0, 3.0, role="wiggle"),
        Param("detail", "디테일", "INT", 3, 1, 6),
        Param("flat", "납작함", "FLOAT", 0.7, 0.1, 2.0),
        Param("seed", "시드", "INT", 0, 0, 100000, role="seed"),
    )

    def build(self, g, P):
        g.frame("1. 기본 구 (Ico Sphere)")
        sphere = g.node("GeometryNodeMeshIcoSphere", Radius=1.0, Subdivisions=P["detail"]).out()

        g.frame("2. Voronoi 로 큰 면을 깎고 Noise 로 잔 요철")
        pos = g.node("GeometryNodeInputPosition").out()
        voronoi = g.node("ShaderNodeTexVoronoi", props={"voronoi_dimensions": "4D"},
                         Vector=pos, W=P["seed"], Scale=1.6).out("Distance")
        noise = g.node("ShaderNodeTexNoise", props={"noise_dimensions": "4D"},
                       Vector=pos, W=P["seed"], Scale=2.7, Detail=4.0).out("Fac")
        bump = g.math("ADD", g.math("MULTIPLY", voronoi, -1.0), g.math("MULTIPLY", g.math("SUBTRACT", noise, 0.5), 0.6))
        normal = g.node("GeometryNodeInputNormal").out()
        offset = g.vmath("SCALE", normal, scale=g.math("MULTIPLY", bump, P["roughness"]))
        rock = g.node("GeometryNodeSetPosition", Geometry=sphere, Offset=offset).out()

        g.frame("3. 크기와 납작함, 각진 면(플랫 쉐이딩)")
        rock = g.node("GeometryNodeTransform", Geometry=rock,
                      Scale=g.vmath("SCALE", g.combine(1.2, 1.0, P["flat"]), scale=P["size"])).out()
        return g.node("GeometryNodeSetShadeSmooth", Geometry=rock, Shade_Smooth=False).out()
