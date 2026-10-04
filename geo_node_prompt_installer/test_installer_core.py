# -*- coding: utf-8 -*-
"""installer_core 테스트: python -m pytest geo_node_prompt_installer"""
import os

import installer_core as core


def _make(tmp_path, *names):
    root = tmp_path / "Blender Foundation" / "Blender"
    for n in names:
        (root / n).mkdir(parents=True)
    return str(tmp_path)


def test_find_versions_sorted_and_filtered(tmp_path):
    appdata = _make(tmp_path, "3.6", "4.2", "4.10", "notes")
    assert [n for _, n, _ in core.find_blender_versions(appdata)] == ["4.10", "4.2", "3.6"]


def test_find_versions_missing_root(tmp_path):
    assert core.find_blender_versions(str(tmp_path)) == []


def test_install_reinstall_uninstall(tmp_path):
    appdata = _make(tmp_path, "4.2")
    _, _, vdir = core.find_blender_versions(appdata)[0]
    dest = core.install(vdir)
    assert dest == os.path.join(vdir, "scripts", "addons", "geo_node_prompt")
    assert core.is_installed(vdir)
    assert not os.path.exists(os.path.join(dest, "tests"))
    stale = os.path.join(dest, "old_module.py")
    open(stale, "w").close()
    core.install(vdir)  # 다시 설치하면 이전 파일은 지워짐
    assert not os.path.exists(stale)
    assert core.uninstall(vdir)
    assert not core.is_installed(vdir)
    assert not core.uninstall(vdir)


def test_find_blender_exe(tmp_path):
    exe = tmp_path / "PF" / "Blender Foundation" / "Blender 4.2" / "blender.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    env = {"ProgramFiles": str(tmp_path / "PF")}
    assert core.find_blender_exe("4.2", env) == str(exe)
    assert core.find_blender_exe("4.5", env) is None
