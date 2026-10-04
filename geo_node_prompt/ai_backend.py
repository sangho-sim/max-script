# -*- coding: utf-8 -*-
"""Anthropic(Claude) API 로 자연어 프롬프트 -> 노드 스펙(JSON) 변환.

bpy 에 의존하지 않는다 (표준 라이브러리 urllib/json 만 사용). 네트워크
호출이 실패하거나 응답이 스펙 형식에 맞지 않으면 ValueError 를 던진다.
"""

import json
import urllib.request
import urllib.error

from .node_whitelist import ALLOWED_NODE_TYPES, ALLOWED_SOCKET_TYPES

API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

SYSTEM_PROMPT = """너는 Blender Geometry Nodes 노드 트리를 설계하는 도우미다.
사용자의 한국어/영어 프롬프트를 아래 JSON 스키마 하나로만 답해야 한다.
설명, 코드 블록 표시(```), 그 외의 텍스트는 절대 포함하지 마라. JSON만 출력하라.

스키마:
{
  "name": "<노드 그룹 이름, 짧게>",
  "exposed_inputs": [
    {"name": "<표시 이름>", "socket_type": "<소켓 타입>", "default": <값>,
     "min": <값 optional>, "max": <값 optional>}
  ],
  "nodes": [
    {"id": "<고유 id>", "type": "<노드 bl_idname>",
     "location": [x, y],
     "props": {"<속성명>": <값>},
     "defaults": {"<소켓 이름 또는 인덱스>": <값>}}
  ],
  "links": [
    {"from_node": "<id 또는 GROUP_INPUT>", "from_socket": "<소켓 이름>",
     "to_node": "<id 또는 GROUP_OUTPUT>", "to_socket": "<소켓 이름>"}
  ]
}

규칙:
- "GROUP_INPUT" 의 첫 출력 소켓은 항상 "Geometry" 이고, exposed_inputs 에 적은
  이름들이 선언한 순서대로 그 뒤를 잇는 출력 소켓이 된다.
- "GROUP_OUTPUT" 은 입력 소켓 "Geometry" 하나만 받는다. 최종 결과를 반드시
  여기로 연결해야 한다.
- node.type(bl_idname)은 반드시 다음 목록 중에서만 골라라: __ALLOWED_TYPES__
- socket_type 은 다음 중에서만 골라라: __ALLOWED_SOCKETS__
- 소켓 이름이 모호한(Math, VectorMath 등) 노드는 "to_socket"/"from_socket"에
  이름 대신 0부터 시작하는 정수 인덱스를 써도 된다.
- 존재하지 않는 노드/소켓 이름을 쓰지 말고, 반드시 실행 가능한 그래프를 만들어라.
"""

SYSTEM_PROMPT = SYSTEM_PROMPT.replace(
    "__ALLOWED_TYPES__", ", ".join(sorted(ALLOWED_NODE_TYPES))
).replace(
    "__ALLOWED_SOCKETS__", ", ".join(sorted(ALLOWED_SOCKET_TYPES))
)


def _strip_code_fence(text):
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def validate_spec(spec):
    """스펙 dict 의 최소한의 구조적 안전성을 검사한다.

    문제가 있으면 설명과 함께 ValueError 를 던지고, 문제 없으면 그냥
    돌아온다 (반환값 없음).
    """
    if not isinstance(spec, dict):
        raise ValueError("스펙이 JSON 객체가 아닙니다.")

    nodes = spec.get("nodes")
    links = spec.get("links")
    if not isinstance(nodes, list) or not nodes:
        raise ValueError("'nodes' 리스트가 비어 있거나 없습니다.")
    if not isinstance(links, list) or not links:
        raise ValueError("'links' 리스트가 비어 있거나 없습니다.")

    node_ids = set()
    for node in nodes:
        if not isinstance(node, dict) or "id" not in node or "type" not in node:
            raise ValueError("노드에 'id' 또는 'type'이 없습니다.")
        if node["type"] not in ALLOWED_NODE_TYPES:
            raise ValueError("허용되지 않은 노드 타입: {}".format(node["type"]))
        if node["id"] in node_ids or node["id"] in ("GROUP_INPUT", "GROUP_OUTPUT"):
            raise ValueError("중복되거나 예약된 노드 id: {}".format(node["id"]))
        node_ids.add(node["id"])

    valid_ids = node_ids | {"GROUP_INPUT", "GROUP_OUTPUT"}
    for link in links:
        if not isinstance(link, dict):
            raise ValueError("링크가 JSON 객체가 아닙니다.")
        for key in ("from_node", "from_socket", "to_node", "to_socket"):
            if key not in link:
                raise ValueError("링크에 '{}' 항목이 없습니다.".format(key))
        if link["from_node"] not in valid_ids:
            raise ValueError("알 수 없는 from_node: {}".format(link["from_node"]))
        if link["to_node"] not in valid_ids:
            raise ValueError("알 수 없는 to_node: {}".format(link["to_node"]))

    for exposed in spec.get("exposed_inputs", []) or []:
        if not isinstance(exposed, dict) or "name" not in exposed:
            raise ValueError("exposed_inputs 항목에 'name'이 없습니다.")
        if exposed.get("socket_type") not in ALLOWED_SOCKET_TYPES:
            raise ValueError("허용되지 않은 socket_type: {}".format(exposed.get("socket_type")))

    has_group_output_link = any(link["to_node"] == "GROUP_OUTPUT" for link in links)
    if not has_group_output_link:
        raise ValueError("GROUP_OUTPUT 으로 연결되는 링크가 없습니다.")


def generate_spec_via_ai(prompt, api_key, model, max_tokens=2000, timeout=30):
    """Claude API 를 호출해 프롬프트로부터 노드 스펙 dict 를 생성한다.

    실패(네트워크 오류, JSON 파싱 실패, 스펙 검증 실패) 시 ValueError 를
    던진다.
    """
    if not api_key:
        raise ValueError("API 키가 설정되어 있지 않습니다.")

    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    request = urllib.request.Request(
        API_URL,
        data=body,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError("Claude API 오류 ({}): {}".format(exc.code, detail)) from exc
    except urllib.error.URLError as exc:
        raise ValueError("네트워크 오류: {}".format(exc.reason)) from exc

    try:
        payload = json.loads(raw)
        text = payload["content"][0]["text"]
    except (KeyError, IndexError, ValueError) as exc:
        raise ValueError("API 응답을 해석할 수 없습니다: {}".format(raw[:500])) from exc

    text = _strip_code_fence(text)
    try:
        spec = json.loads(text)
    except ValueError as exc:
        raise ValueError("AI 응답이 JSON 형식이 아닙니다: {}".format(text[:500])) from exc

    validate_spec(spec)
    return spec
