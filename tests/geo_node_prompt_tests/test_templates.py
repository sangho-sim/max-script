# -*- coding: utf-8 -*-
import pytest

from geo_node_prompt.ai_backend import validate_spec
from geo_node_prompt.node_whitelist import ALLOWED_NODE_TYPES, ALLOWED_SOCKET_TYPES
from geo_node_prompt.templates import TEMPLATES, match_template

TEMPLATE_IDS = [t["id"] for t in TEMPLATES]


def _template(template_id):
    return next(t for t in TEMPLATES if t["id"] == template_id)


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_template_spec_passes_validation(template_id):
    spec = _template(template_id)["builder"]("")
    validate_spec(spec)


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_template_uses_whitelisted_types(template_id):
    spec = _template(template_id)["builder"]("")
    for node in spec["nodes"]:
        assert node["type"] in ALLOWED_NODE_TYPES
    for exposed in spec["exposed_inputs"]:
        assert exposed["socket_type"] in ALLOWED_SOCKET_TYPES


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_template_group_io_sockets_exist(template_id):
    spec = _template(template_id)["builder"]("")
    group_inputs = {"Geometry"} | {e["name"] for e in spec["exposed_inputs"]}
    for link in spec["links"]:
        if link["from_node"] == "GROUP_INPUT":
            assert link["from_socket"] in group_inputs
        if link["to_node"] == "GROUP_OUTPUT":
            assert link["to_socket"] == "Geometry"


@pytest.mark.parametrize("template_id", TEMPLATE_IDS)
def test_template_node_ids_unique(template_id):
    spec = _template(template_id)["builder"]("")
    ids = [n["id"] for n in spec["nodes"]]
    assert len(ids) == len(set(ids))


def test_template_ids_unique():
    assert len(TEMPLATE_IDS) == len(set(TEMPLATE_IDS))


@pytest.mark.parametrize("prompt, expected", [
    ("표면에 노이즈로 울퉁불퉁하게 해줘", "noise_displace"),
    ("풀을 스캐터해서 뿌려줘", "scatter"),
    ("이 오브젝트를 일렬로 배열해줘", "array"),
    ("subdivision으로 둥글게 만들어줘", "subdivision_smooth"),
    ("Shade Smooth 적용", "shade_smooth"),
    ("다른 오브젝트로 구멍을 뚫어줘 (boolean)", "boolean_cut"),
    ("두께를 주고 싶어", "extrude_thickness"),
    ("부서진 느낌으로 랜덤 삭제", "random_delete"),
    ("MAKE IT BUMPY", "noise_displace"),
])
def test_match_template(prompt, expected):
    template = match_template(prompt)
    assert template is not None
    assert template["id"] == expected


@pytest.mark.parametrize("prompt", ["", "안녕하세요", "render a teapot"])
def test_match_template_no_match(prompt):
    assert match_template(prompt) is None


def test_match_template_highest_score_wins():
    # "noise"(1) vs "scatter"+"instance"+"스캐터"(3)
    assert match_template("noise 말고 스캐터 scatter instance")["id"] == "scatter"


def test_match_template_tie_prefers_first():
    # noise_displace 와 scatter 가 각각 1점 -> 리스트 앞쪽 우선
    assert match_template("noise scatter")["id"] == "noise_displace"
