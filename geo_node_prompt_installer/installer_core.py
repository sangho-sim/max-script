# -*- coding: utf-8 -*-
"""Geo Node Prompt 설치 로직 (GUI 없음 — 테스트와 명령줄 설치에서 같이 씀).

Blender 사용자 애드온 폴더:
    %APPDATA%\\Blender Foundation\\Blender\\<버전>\\scripts\\addons\\geo_node_prompt
"""
import os
import re
import shutil
import subprocess
import sys

ADDON_NAME = "geo_node_prompt"
MIN_VERSION = (4, 0)  # bl_info["blender"] 와 맞춤

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)$")
# 설치에 필요 없는 것들 (개발용 테스트, 캐시)
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", "tests")

# Blender 안에서 실행할 코드: 애드온 켜고 환경설정 저장
_ENABLE_EXPR = (
    "import bpy, addon_utils;"
    "bpy.ops.preferences.addon_enable(module='%s');"
    "bpy.ops.wm.save_userpref();"
    "print('GEO_NODE_PROMPT_ENABLED' if addon_utils.check('%s')[1] else 'GEO_NODE_PROMPT_FAILED')"
) % (ADDON_NAME, ADDON_NAME)


def addon_source():
    """설치할 애드온 폴더. exe 안에서는 PyInstaller 가 풀어 둔 임시 폴더."""
    base = getattr(sys, "_MEIPASS", None)
    if base is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, ADDON_NAME)


def blender_config_root(appdata=None):
    appdata = appdata or os.environ.get("APPDATA", "")
    return os.path.join(appdata, "Blender Foundation", "Blender")


def parse_version(name):
    m = _VERSION_RE.match(name)
    return (int(m.group(1)), int(m.group(2))) if m else None


def find_blender_versions(appdata=None):
    """설치된(한 번이라도 실행된) Blender 버전 폴더 목록, 최신 버전부터.

    반환: [(버전 튜플, "4.2", 버전 폴더 경로), ...]
    """
    root = blender_config_root(appdata)
    found = []
    if os.path.isdir(root):
        for name in os.listdir(root):
            ver = parse_version(name)
            path = os.path.join(root, name)
            if ver and os.path.isdir(path):
                found.append((ver, name, path))
    found.sort(reverse=True)
    return found


def addon_dir(version_dir):
    return os.path.join(version_dir, "scripts", "addons", ADDON_NAME)


def is_installed(version_dir):
    return os.path.isfile(os.path.join(addon_dir(version_dir), "__init__.py"))


def install(version_dir, source=None):
    """애드온을 복사 (기존 설치는 지우고 새로 씀). 설치된 경로를 반환."""
    source = source or addon_source()
    if not os.path.isfile(os.path.join(source, "__init__.py")):
        raise FileNotFoundError("애드온 파일을 찾을 수 없습니다: " + source)
    dest = addon_dir(version_dir)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copytree(source, dest, ignore=_IGNORE)
    return dest


def uninstall(version_dir):
    """애드온 폴더 삭제. 지웠으면 True."""
    dest = addon_dir(version_dir)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
        return True
    return False


def find_blender_exe(version_name, env=None):
    """해당 버전의 blender.exe 를 일반적인 설치 위치에서 찾음. 없으면 None."""
    env = env if env is not None else os.environ
    candidates = []
    for var in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
        base = env.get(var)
        if base:
            candidates.append(os.path.join(base, "Blender Foundation",
                                           "Blender " + version_name, "blender.exe"))
    local = env.get("LOCALAPPDATA")
    if local:  # winget / 사용자 단위 설치
        candidates.append(os.path.join(local, "Programs", "Blender Foundation",
                                       "Blender " + version_name, "blender.exe"))
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def enable(blender_exe, timeout=180):
    """Blender 를 백그라운드로 잠깐 실행해 애드온을 켜고 환경설정을 저장.

    반환: (성공 여부, 출력 마지막 부분)
    """
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(
            [blender_exe, "--background", "--python-expr", _ENABLE_EXPR],
            capture_output=True, text=True, errors="replace",
            timeout=timeout, creationflags=flags,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    out = (proc.stdout or "") + (proc.stderr or "")
    return "GEO_NODE_PROMPT_ENABLED" in out, out[-2000:]
