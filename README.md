# Retopo Annotate

3ds Max / Blender 주석 기반 리토폴로지 툴 (설치 프로그램에서 꺼낸 소스).

- `max/RetopoAnnotate.ms` — 3ds Max 스크립트
- `blender/retopo_annotate.py` — Blender 애드온
- `dotnet/RAKeys.cs` — 키 입력 도우미, `dotnet/RAQuad.cs` — 스캔 → 합친 메쉬 엔진 (둘 다 `RAKeys.dll` 로 빌드)
- `installer/` — 원래 설치 프로그램(1.5)과 리소스 교체 도구, 사용법(README.txt)
- `tools/RAQuadTest.cs` — OBJ 로 엔진을 돌려 보는 테스트 프로그램
- `dist/` — 빌드 결과 (`RetopoAnnotate_Setup.exe`)

빌드: `./build.sh <Mono.Cecil.dll>` (mono 필요)

## 스캔 → 합친 메쉬 엔진 (RAQuad)

1. 모든 입력 삼각형까지 거리장을 좁은 띠로 계산하고 바깥에서 채워 겹친/열린 오브젝트를 하나의 껍질로 합침
2. 서피스 넷으로 바탕 메쉬
3. Instant Meshes 방식 4-RoSy 방향장 + 위치장 (계층, 병렬), 날카로운 모서리·가이드 선은 방향/격자선 고정
4. 격자 추출 → 구멍 채우기 → 삼각형 짝 → 홀수 면을 쿼드 띠로 이어 전부 쿼드
5. 닫힌 표면(틈 메움)으로 투영하며 이완, 뾰족한 꼭짓점 고정
