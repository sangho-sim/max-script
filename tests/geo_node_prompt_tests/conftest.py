# -*- coding: utf-8 -*-
"""geo_node_prompt 를 import 하기 전에 bpy 스텁을 sys.modules 에 끼워 넣는다."""

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))

for path in (REPO_ROOT, HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

import bpy_stub  # noqa: E402

sys.modules.setdefault("bpy", bpy_stub)


@pytest.fixture(autouse=True)
def _reset_bpy():
    bpy_stub.reset()
    yield
    bpy_stub.reset()
