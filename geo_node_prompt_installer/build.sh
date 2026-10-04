#!/bin/bash
# GeoNodePrompt_Setup.exe 만들기 (.NET Framework 4.5 exe, Windows 에 기본으로 들어 있어 따로 설치 필요 없음)
#   Linux/macOS: mono 의 mcs 필요     Windows: Git Bash 에서 실행 (Framework 의 csc.exe 사용)
#   ./geo_node_prompt_installer/build.sh
set -e
cd "$(dirname "$0")/.."
mkdir -p obj dist
# 애드온 폴더를 zip 으로 (개발용 tests, 캐시 제외) → exe 리소스로 넣음
PY=python3; "$PY" -c "" 2>/dev/null || PY=python  # Windows 의 python3 는 스토어 바로가기일 수 있음
"$PY" - <<'PY'
import os, zipfile
with zipfile.ZipFile("obj/geo_node_prompt.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk("geo_node_prompt"):
        dirs[:] = sorted(d for d in dirs if d not in ("tests", "__pycache__"))
        for f in sorted(files):
            if not f.endswith(".pyc"):
                p = os.path.join(root, f)
                z.write(p, p.replace(os.sep, "/"))
PY
SRC=geo_node_prompt_installer/GeoNodePromptSetup.cs
REFS="-r:System.Windows.Forms.dll -r:System.Drawing.dll -r:System.IO.Compression.dll"
if command -v mcs >/dev/null; then
	mcs -target:winexe -optimize+ -codepage:utf8 $REFS \
		-resource:obj/geo_node_prompt.zip,geo_node_prompt.zip -out:dist/GeoNodePrompt_Setup.exe $SRC
else
	CSC=/c/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe
	"$CSC" -nologo -target:winexe -optimize+ -codepage:65001 $REFS \
		-resource:obj/geo_node_prompt.zip,geo_node_prompt.zip -out:dist/GeoNodePrompt_Setup.exe $SRC
fi
cp geo_node_prompt_installer/README.txt "dist/GeoNodePrompt_사용법.txt"
echo "dist/GeoNodePrompt_Setup.exe 완료"
