# -*- coding: utf-8 -*-
import io
import json
import urllib.error

import pytest

from geo_node_prompt import ai_backend
from geo_node_prompt.ai_backend import _strip_code_fence, generate_spec_via_ai, validate_spec
from geo_node_prompt.templates import TEMPLATES

VALID_SPEC = TEMPLATES[0]["builder"]("")


def _spec(**overrides):
    spec = json.loads(json.dumps(VALID_SPEC))
    spec.update(overrides)
    return spec


# ---------------------------------------------------------------- validate_spec
@pytest.mark.parametrize("bad", [None, [], "spec", 3])
def test_validate_rejects_non_dict(bad):
    with pytest.raises(ValueError):
        validate_spec(bad)


@pytest.mark.parametrize("key", ["nodes", "links"])
@pytest.mark.parametrize("value", [None, [], "x"])
def test_validate_rejects_missing_or_empty_lists(key, value):
    with pytest.raises(ValueError):
        validate_spec(_spec(**{key: value}))


def test_validate_rejects_node_without_id():
    with pytest.raises(ValueError):
        validate_spec(_spec(nodes=[{"type": "GeometryNodeSetPosition"}]))


@pytest.mark.parametrize("node_id", ["GROUP_INPUT", "GROUP_OUTPUT"])
def test_validate_rejects_reserved_node_id(node_id):
    spec = _spec()
    spec["nodes"][0]["id"] = node_id
    with pytest.raises(ValueError, match=node_id):
        validate_spec(spec)


def test_validate_rejects_duplicate_node_id():
    spec = _spec()
    spec["nodes"][1]["id"] = spec["nodes"][0]["id"]
    with pytest.raises(ValueError, match=spec["nodes"][0]["id"]):
        validate_spec(spec)


@pytest.mark.parametrize("key", ["nodes", "links", "exposed_inputs"])
def test_validate_rejects_non_dict_entries(key):
    spec = _spec()
    spec[key] = spec[key] + ["oops"]
    with pytest.raises(ValueError):
        validate_spec(spec)


def test_validate_rejects_exposed_input_without_name():
    spec = _spec(exposed_inputs=[{"socket_type": "NodeSocketFloat"}])
    with pytest.raises(ValueError, match="name"):
        validate_spec(spec)


def test_validate_rejects_disallowed_node_type():
    spec = _spec()
    spec["nodes"][0]["type"] = "GeometryNodeEvilScript"
    with pytest.raises(ValueError, match="GeometryNodeEvilScript"):
        validate_spec(spec)


def test_validate_rejects_link_missing_key():
    spec = _spec()
    del spec["links"][0]["to_socket"]
    with pytest.raises(ValueError, match="to_socket"):
        validate_spec(spec)


@pytest.mark.parametrize("end", ["from_node", "to_node"])
def test_validate_rejects_unknown_link_node(end):
    spec = _spec()
    spec["links"][0][end] = "ghost"
    with pytest.raises(ValueError, match="ghost"):
        validate_spec(spec)


def test_validate_rejects_disallowed_socket_type():
    spec = _spec(exposed_inputs=[{"name": "X", "socket_type": "NodeSocketShader"}])
    with pytest.raises(ValueError):
        validate_spec(spec)


def test_validate_requires_group_output_link():
    spec = _spec()
    spec["links"] = [l for l in spec["links"] if l["to_node"] != "GROUP_OUTPUT"]
    with pytest.raises(ValueError, match="GROUP_OUTPUT"):
        validate_spec(spec)


def test_validate_allows_missing_exposed_inputs():
    spec = _spec()
    spec.pop("exposed_inputs")
    validate_spec(spec)


# ---------------------------------------------------------------- _strip_code_fence
@pytest.mark.parametrize("text", [
    '{"a": 1}',
    '```json\n{"a": 1}\n```',
    '```\n{"a": 1}\n```',
    '  \n```json\n{"a": 1}\n```  \n',
])
def test_strip_code_fence(text):
    assert json.loads(_strip_code_fence(text)) == {"a": 1}


def test_system_prompt_placeholders_filled():
    assert "__ALLOWED_TYPES__" not in ai_backend.SYSTEM_PROMPT
    assert "__ALLOWED_SOCKETS__" not in ai_backend.SYSTEM_PROMPT
    assert "GeometryNodeSetPosition" in ai_backend.SYSTEM_PROMPT
    assert "NodeSocketFloat" in ai_backend.SYSTEM_PROMPT


# ---------------------------------------------------------------- generate_spec_via_ai
class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _api_payload(text):
    return json.dumps({"content": [{"type": "text", "text": text}]}).encode("utf-8")


@pytest.fixture
def fake_urlopen(monkeypatch):
    calls = []
    state = {"response": None, "error": None}

    def _urlopen(request, timeout=None):
        calls.append((request, timeout))
        if state["error"] is not None:
            raise state["error"]
        return _FakeResponse(state["response"])

    monkeypatch.setattr(ai_backend.urllib.request, "urlopen", _urlopen)
    state["calls"] = calls
    return state


def test_generate_requires_api_key(fake_urlopen):
    with pytest.raises(ValueError, match="API"):
        generate_spec_via_ai("prompt", "", "model")
    assert fake_urlopen["calls"] == []


def test_generate_success_builds_request(fake_urlopen):
    fake_urlopen["response"] = _api_payload(json.dumps(VALID_SPEC))
    spec = generate_spec_via_ai("울퉁불퉁", "sk-test", "claude-x", max_tokens=1234, timeout=7)
    assert spec["name"] == VALID_SPEC["name"]

    request, timeout = fake_urlopen["calls"][0]
    assert timeout == 7
    assert request.full_url == ai_backend.API_URL
    assert request.get_method() == "POST"
    headers = {k.lower(): v for k, v in request.header_items()}
    assert headers["x-api-key"] == "sk-test"
    assert headers["anthropic-version"] == ai_backend.ANTHROPIC_VERSION
    body = json.loads(request.data.decode("utf-8"))
    assert body["model"] == "claude-x"
    assert body["max_tokens"] == 1234
    assert body["system"] == ai_backend.SYSTEM_PROMPT
    assert body["messages"] == [{"role": "user", "content": "울퉁불퉁"}]


def test_generate_accepts_fenced_json(fake_urlopen):
    fake_urlopen["response"] = _api_payload("```json\n" + json.dumps(VALID_SPEC) + "\n```")
    assert generate_spec_via_ai("p", "k", "m")["nodes"]


def test_generate_http_error(fake_urlopen):
    fake_urlopen["error"] = urllib.error.HTTPError(
        ai_backend.API_URL, 401, "Unauthorized", {}, io.BytesIO(b'{"error":"bad key"}')
    )
    with pytest.raises(ValueError, match="401"):
        generate_spec_via_ai("p", "k", "m")


def test_generate_network_error(fake_urlopen):
    fake_urlopen["error"] = urllib.error.URLError("no route")
    with pytest.raises(ValueError, match="no route"):
        generate_spec_via_ai("p", "k", "m")


def test_generate_unexpected_payload(fake_urlopen):
    fake_urlopen["response"] = b'{"content": []}'
    with pytest.raises(ValueError):
        generate_spec_via_ai("p", "k", "m")


def test_generate_non_json_text(fake_urlopen):
    fake_urlopen["response"] = _api_payload("노드를 이렇게 만드세요...")
    with pytest.raises(ValueError, match="JSON"):
        generate_spec_via_ai("p", "k", "m")


def test_generate_rejects_invalid_spec(fake_urlopen):
    bad = _spec()
    bad["nodes"][0]["type"] = "GeometryNodeEvilScript"
    fake_urlopen["response"] = _api_payload(json.dumps(bad))
    with pytest.raises(ValueError, match="GeometryNodeEvilScript"):
        generate_spec_via_ai("p", "k", "m")
