==============================================================
 Geo Node Prompt — 프롬프트로 Blender 지오메트리 노드 만들기
==============================================================

[설치]
 1. Blender 를 (설치 후) 한 번 이상 실행했다가 끕니다.
 2. GeoNodePrompt_Setup.exe 실행
    → 찾은 Blender 버전(4.0 이상) 중 설치할 버전 체크 → [설치]
    (관리자 권한 필요 없음, 사용자 폴더에 설치)
    - "설치 후 애드온 자동 활성화" 가 켜져 있으면 Blender 를 잠깐 백그라운드로
      실행해 애드온을 켜 둡니다. blender.exe 를 못 찾으면 직접 고를 수 있습니다.
    - 목록에 버전이 없으면 [다른 Blender 폴더 추가]로
      %APPDATA%\Blender Foundation\Blender\<버전> 폴더를 고르세요.
 3. ★ Blender 가 켜져 있었다면 껐다가 다시 실행
 4. 3D 뷰포트에서 N 키 → 사이드바 'Geo Prompt' 탭

 * 활성화가 안 됐으면: 편집 > 환경설정 > 애드온 → "Geo Node Prompt" 체크
 * 제거: 같은 설치 프로그램에서 버전 체크 후 [제거]
 * 명령줄: /S 지원되는 모든 버전에 자동 설치+활성화, /U 모든 버전에서 자동 제거

 설치 위치: %APPDATA%\Blender Foundation\Blender\<버전>\scripts\addons\geo_node_prompt

 * Windows SmartScreen 에 "알 수 없는 게시자" 경고가 뜨면
   [추가 정보] → [실행] (코드 서명이 없는 exe 라서 나오는 경고)
