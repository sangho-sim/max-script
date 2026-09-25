#!/bin/bash
# RAKeys.dll(키 도우미 + RAQuad 스캔 엔진)과 설치 프로그램을 다시 만듦. 필요: mono (mcs), Mono.Cecil.dll
#   ./build.sh [Mono.Cecil.dll 경로]
set -e
cd "$(dirname "$0")"
CECIL=${1:-${CECIL:-Mono.Cecil.dll}}
mkdir -p dist obj
mcs -target:library -optimize+ -sdk:4.5 -nowarn:219 -out:dist/RAKeys.dll dotnet/RAKeys.cs dotnet/RAQuad.cs
mcs -r:"$CECIL" -out:obj/Repack.exe installer/Repack.cs
MONO_PATH=$(dirname "$CECIL") mono obj/Repack.exe installer/base/RetopoAnnotate_Setup_1.5.exe dist/RetopoAnnotate_Setup.exe \
	RetopoAnnotate.ms=max/RetopoAnnotate.ms retopo_annotate.py=blender/retopo_annotate.py \
	RAKeys.dll=dist/RAKeys.dll README.txt=installer/README.txt
cp installer/README.txt "dist/RetopoAnnotate_사용법.txt"
echo "dist/RetopoAnnotate_Setup.exe 완료"
