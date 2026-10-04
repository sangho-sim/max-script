# -*- coding: utf-8 -*-
"""Geo Node Prompt 설치 프로그램 (GeoNodePrompt_Setup.exe 의 진입점).

    GeoNodePrompt_Setup.exe        창을 띄워 Blender 버전을 골라 설치/제거
    GeoNodePrompt_Setup.exe /S     지원되는 모든 Blender 버전에 자동 설치 + 활성화
    GeoNodePrompt_Setup.exe /U     모든 버전에서 자동 제거
"""
import os
import sys
import threading

import installer_core as core

TITLE = "Geo Node Prompt 설치"


def _supported(ver):
    return ver >= core.MIN_VERSION


def run_silent(uninstall=False):
    code = 0
    for ver, name, path in core.find_blender_versions():
        if uninstall:
            if core.uninstall(path):
                print("제거:", name)
            continue
        if not _supported(ver):
            continue
        print("설치:", core.install(path))
        exe = core.find_blender_exe(name)
        if exe:
            ok, _ = core.enable(exe)
            print("  활성화", "완료" if ok else "실패 (Blender 환경설정에서 직접 체크)")
            code = code or (0 if ok else 2)
    return code


class App:
    def __init__(self, root):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.root = root
        root.title(TITLE)
        root.resizable(False, False)
        frm = ttk.Frame(root, padding=14)
        frm.grid()

        ttk.Label(frm, text="Geo Node Prompt — 프롬프트로 지오메트리 노드 만들기",
                  font=("", 11, "bold")).grid(sticky="w")
        ttk.Label(frm, text="설치할 Blender 버전을 고르세요 (Blender %d.%d 이상)" % core.MIN_VERSION
                  ).grid(sticky="w", pady=(8, 4))

        self.box = ttk.Frame(frm)
        self.box.grid(sticky="w", padx=8)
        self.vars = []  # (BooleanVar, 버전 이름, 버전 폴더)
        self._fill_versions()

        ttk.Button(frm, text="다른 Blender 폴더 추가...", command=self._add_folder
                   ).grid(sticky="w", pady=(6, 0))

        self.enable_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="설치 후 애드온 자동 활성화 (Blender 를 잠깐 백그라운드로 실행)",
                        variable=self.enable_var).grid(sticky="w", pady=(10, 0))

        self.status = tk.StringVar(value="")
        ttk.Label(frm, textvariable=self.status, wraplength=440, justify="left"
                  ).grid(sticky="w", pady=(10, 0))

        btns = ttk.Frame(frm)
        btns.grid(sticky="e", pady=(12, 0))
        self.btn_install = ttk.Button(btns, text="설치", command=self._install)
        self.btn_uninstall = ttk.Button(btns, text="제거", command=self._uninstall)
        self.btn_install.grid(row=0, column=0, padx=4)
        self.btn_uninstall.grid(row=0, column=1, padx=4)
        ttk.Button(btns, text="닫기", command=root.destroy).grid(row=0, column=2, padx=4)

        if not self.vars:
            self.status.set("설치된 Blender 를 찾지 못했습니다.\n"
                            "Blender 를 한 번 실행했다가 끈 뒤 다시 실행하거나, "
                            "[다른 Blender 폴더 추가]로 직접 고르세요.")

    def _fill_versions(self):
        from tkinter import ttk

        first = True
        for ver, name, path in core.find_blender_versions():
            ok = _supported(ver)
            label = "Blender " + name
            if core.is_installed(path):
                label += "  (설치됨)"
            if not ok:
                label += "  (지원 안 됨)"
            var = self.tk.BooleanVar(value=ok and first)
            first = first and not ok
            ttk.Checkbutton(self.box, text=label, variable=var,
                            state="normal" if ok else "disabled").grid(sticky="w")
            self.vars.append((var, name, path))

    def _add_folder(self):
        from tkinter import filedialog, messagebox, ttk

        path = filedialog.askdirectory(
            title="Blender 버전 폴더 선택 (예: ...\\Blender Foundation\\Blender\\4.2)",
            initialdir=core.blender_config_root())
        if not path:
            return
        path = os.path.normpath(path)
        name = os.path.basename(path)
        if core.parse_version(name) is None:
            messagebox.showwarning(TITLE, "버전 이름(예: 4.2)으로 된 폴더를 골라 주세요.")
            return
        var = self.tk.BooleanVar(value=True)
        ttk.Checkbutton(self.box, text="Blender %s  (%s)" % (name, path), variable=var).grid(sticky="w")
        self.vars.append((var, name, path))
        self.status.set("")

    def _selected(self):
        return [(name, path) for var, name, path in self.vars if var.get()]

    def _busy(self, busy):
        state = "disabled" if busy else "normal"
        self.btn_install.config(state=state)
        self.btn_uninstall.config(state=state)

    def _install(self):
        from tkinter import filedialog, messagebox

        targets = self._selected()
        if not targets:
            messagebox.showinfo(TITLE, "설치할 Blender 버전을 하나 이상 체크하세요.")
            return
        jobs = []
        for name, path in targets:
            exe = None
            if self.enable_var.get():
                exe = core.find_blender_exe(name)
                if exe is None and messagebox.askyesno(
                        TITLE, "Blender %s 의 blender.exe 를 찾지 못했습니다.\n"
                               "직접 찾아서 자동 활성화할까요?\n"
                               "(아니요 = 파일만 복사, 활성화는 Blender 에서 직접)" % name):
                    exe = filedialog.askopenfilename(
                        title="Blender %s 의 blender.exe 선택" % name,
                        filetypes=[("blender.exe", "blender.exe"), ("실행 파일", "*.exe")]) or None
            jobs.append((name, path, exe))
        self._busy(True)
        self.status.set("설치 중...")
        threading.Thread(target=self._install_worker, args=(jobs,), daemon=True).start()

    def _install_worker(self, jobs):
        lines, manual = [], False
        for name, path, exe in jobs:
            try:
                core.install(path)
            except Exception as exc:  # 권한·파일 잠김 등
                lines.append("Blender %s: 설치 실패 — %s" % (name, exc))
                continue
            if exe:
                self.root.after(0, self.status.set, "Blender %s 에서 애드온 활성화 중..." % name)
                ok, _ = core.enable(exe)
                lines.append("Blender %s: 설치 + 활성화 %s" % (name, "완료" if ok else "실패"))
                manual = manual or not ok
            else:
                lines.append("Blender %s: 설치 완료" % name)
                manual = True
        msg = "\n".join(lines)
        if manual:
            msg += ("\n\n활성화가 안 된 버전은 Blender 에서 편집 > 환경설정 > 애드온 → "
                    "\"Geo Node Prompt\" 를 체크하세요.")
        msg += "\n\n★ Blender 가 켜져 있었다면 껐다가 다시 실행하세요.\n" \
               "사용: 3D 뷰포트에서 N 키 → 사이드바 'Geo Prompt' 탭"
        self.root.after(0, self._done, msg)

    def _uninstall(self):
        from tkinter import messagebox

        targets = self._selected()
        if not targets:
            messagebox.showinfo(TITLE, "제거할 Blender 버전을 체크하세요.")
            return
        lines = []
        for name, path in targets:
            try:
                removed = core.uninstall(path)
                lines.append("Blender %s: %s" % (name, "제거 완료" if removed else "설치되어 있지 않음"))
            except Exception as exc:
                lines.append("Blender %s: 제거 실패 — %s (Blender 를 끄고 다시 시도)" % (name, exc))
        self._done("\n".join(lines))

    def _done(self, msg):
        from tkinter import messagebox

        self._busy(False)
        self.status.set("")
        messagebox.showinfo(TITLE, msg)


def main(argv):
    flags = {a.upper() for a in argv[1:]}
    if "/U" in flags:
        return run_silent(uninstall=True)
    if "/S" in flags:
        return run_silent()
    import tkinter as tk

    root = tk.Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
