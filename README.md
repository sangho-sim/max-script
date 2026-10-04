# Retopo Annotate

3ds Max / Blender 주석 기반 리토폴로지 툴 (설치 프로그램에서 꺼낸 소스).

- `max/RetopoAnnotate.ms` — 3ds Max 스크립트
- `blender/retopo_annotate.py` — Blender 애드온
- `blender/korean_input.py` — Blender 한글 입력 도우미 애드온 (아래 설명)
- `installer/` — 원래 설치 프로그램(1.5) 소스

## 한글 입력 도우미 (Korean IME Helper)

블렌더 자체 텍스트 입력창은 플랫폼에 따라 한글 자모 조합(IME)이 제대로 되지 않는
경우가 있다. `blender/korean_input.py`는 OS IME를 거치지 않고 표준 두벌식 키보드
배열을 직접 받아 완성형 한글을 조합하는 애드온이다.

- 설치: 블렌더 환경설정 > 애드온 > 설치에서 `blender/korean_input.py` 선택
- 사용: 3D 뷰 사이드바(N) > `한글입력` 탭
  - **한글 입력창 열기** — 두벌식으로 입력 후 Enter 시 클립보드로 복사 (아무 텍스트 필드에나 붙여넣기 가능)
  - **선택 오브젝트 이름 변경** — 입력한 한글로 활성 오브젝트 이름을 바로 변경
  - **3D 텍스트 만들기** — 입력한 한글로 Text 오브젝트를 만들고, 시스템에서 한글 폰트(나눔고딕/맑은 고딕/Noto Sans KR 등)를 자동으로 찾아 적용
- 입력 중 Tab으로 한글/영문 전환, Back Space로 한 키 지우기, Esc로 취소
