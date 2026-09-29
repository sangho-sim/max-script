#!/bin/bash
# macOS: 더블클릭으로 실행
cd "$(dirname "$0")"
if ! command -v node >/dev/null 2>&1; then
  echo ""
  echo " Node.js 가 설치되어 있지 않습니다. 열리는 페이지에서 LTS 버전을 설치한 뒤 다시 실행해 주세요."
  open "https://nodejs.org/ko/download"
  read -n 1 -s -r -p " 아무 키나 누르면 닫힙니다"
  exit 1
fi
node scripts/launch.mjs --demo
