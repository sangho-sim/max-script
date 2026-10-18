# 인수인계: 3ds Max 자동 로드 에러 조사 및 Retopo Annotate 제거

작성일: 2026-10-18 · 브랜치: `claude/friendly-bohr-bu7fc0` · 코드 변경 없음

## 1. 현재 상태 한눈에 보기

| 항목 | 상태 |
| --- | --- |
| 에러 원인 | **확정 못 함.** 에러창 제목의 스크립트 경로가 잘려서 어떤 스크립트인지 모름 |
| 이 저장소의 스크립트가 원인인가 | 가능성 낮음 (아래 근거). 단정은 못 함 |
| Retopo Annotate 제거 | **실행됐는지 모름.** 사용자 PC에서 직접 실행해야 함 |
| 저장소 코드 수정 | 없음. 이 파일(`HANDOFF.md`)만 추가 |

## 2. 사용자가 겪는 문제

3ds Max를 켤 때 아래 에러창이 뜸.

```
MAXScript Auto-load Script Error - C:\Program Files\Autodesk\3ds M...
-- Runtime error: .NET runtime exception: Invalid directory on URL.
```

제목 줄이 `3ds M...`에서 잘려서 스크립트 파일명을 알 수 없음.

## 3. 조사 결과

### 이 저장소 스크립트가 원인일 가능성이 낮은 근거

- **설치 위치가 다름.** 설치 프로그램(`dist/RetopoAnnotate_Setup.exe`)의 문자열을 확인한 결과, 설치 경로는 아래뿐임. 에러창의 `C:\Program Files\Autodesk\3ds Max ...`와 다름.
  - `%APPDATA%\Autodesk\ApplicationPlugins\RetopoAnnotate.bundle`
  - `%LOCALAPPDATA%\Autodesk\3dsMax\20xx - 64bit\...\scripts\startup`
- **.NET 호출이 모두 `try ... catch` 안에 있음.** `max/RetopoAnnotate.ms`의 `dotNet.loadAssembly`(2736행, 4107행)와 `CSharpCodeProvider`(4156~4160행 부근)가 해당함. 로드 시 .NET 예외가 밖으로 나와 "Auto-load Script Error"를 띄우기 어려움.
- 다만 사용자가 `RetopoAnnotate.ms`를 Program Files 쪽에 직접 복사해 둔 경우는 확인하지 못함.

### 에러 메시지의 의미 (기억에 의존, 검증 안 함)

`Invalid directory on URL`은 `dotNet.loadAssembly`나 `Assembly.LoadFrom`에 잘못된 경로가 넘어갔을 때 흔히 나오는 .NET 메시지임. 의심할 원인은 아래와 같음.
- DLL 경로가 틀렸거나 비어 있음 (파일 대신 폴더만 넘김 등)
- 경로에 `#` 같은 특수문자가 있거나 UNC 경로임
- 오래된 플러그인을 Max 2025 이상(.NET 8)에서 로드함

## 4. 제거 요청 경과

- 사용자가 "MAXScript에서 Retopo Annotate를 제거해 달라"고 요청함.
- 이 세션은 클라우드 리눅스 컨테이너라 사용자 PC의 Windows/3ds Max에 접근할 수 없음. 원격 제어 도구도 연결돼 있지 않음. 그래서 **직접 제거하지 못했고** 사용자에게 방법을 안내함.

### 제거 방법 (사용자 PC에서, 3ds Max 종료 후)

1. 설치 프로그램으로 제거 (권장)
   - `RetopoAnnotate_Setup.exe`의 [제거] 버튼, 또는 `RetopoAnnotate_Setup.exe /U` (창 없이 자동 제거)
   - 제거 후 Max를 처음 켜면 일회용 `RetopoAnnotate_uninstall.ms`가 "Retopo" 메뉴를 지우고 스스로 삭제됨.
2. 수동 삭제
   - `%APPDATA%\Autodesk\ApplicationPlugins\RetopoAnnotate.bundle` 폴더 삭제
   - `%LOCALAPPDATA%\Autodesk\3dsMax\20xx - 64bit\...\usermacros\RetopoAnnotate-*.mcr` 삭제
   - 같은 버전 폴더의 `scripts\startup\`에 RetopoAnnotate 관련 파일이 있으면 삭제
   - "Retopo" 메뉴가 남으면 리스너(F11)에서 아래 실행:
     ```maxscript
     try (local m = menuMan.findMenu "Retopo"; if m != undefined do (menuMan.unRegisterMenu m; menuMan.updateMenuBar())) catch ()
     ```

주의: 위 경로와 제거 스크립트 내용은 설치 프로그램 바이너리의 문자열에서 읽은 것임. `...\scripts\startup` 사이의 언어 폴더(예: `ENU`) 이름은 확인하지 못함.

## 5. 다음에 할 일

1. 사용자에게 **에러창의 스크립트 전체 경로(파일명)** 를 받는다. 제목 줄이 잘렸으니 창을 넓히게 하거나 아래 폴더를 직접 보게 한다.
   - `C:\Program Files\Autodesk\3ds Max 20xx\scripts\startup\`
   - `C:\Program Files\Autodesk\3ds Max 20xx\stdplugs\stdscripts\`
2. 그 파일이 이 저장소의 것인지 판단한다.
   - **다른 플러그인 것이면:** 그 플러그인 업데이트/재설치, 급하면 파일을 다른 폴더로 옮겨 둔다.
   - **이 저장소 것이면:** `max/RetopoAnnotate.ms`를 고친다. 먼저 `RA_ScriptDir`(17행)와 `getThisScriptFilename()`이 Program Files 경로에서 어떤 값을 주는지 확인한다.
3. 제거를 실행한 뒤에도 에러가 계속 뜨는지 사용자에게 확인한다. 계속 뜨면 Retopo Annotate와 무관하다는 뜻이다.

## 6. 저장소 구조 (참고)

- `max/RetopoAnnotate.ms` — 3ds Max 스크립트 (매크로 정의 4678행~, 메뉴 등록 4762행~, 첫 실행 처리 4793행~)
- `blender/retopo_annotate.py` — Blender 애드온
- `dotnet/RAKeys.cs`, `dotnet/RAQuad.cs` — `RAKeys.dll`로 빌드되는 키 입력 도우미와 스캔 엔진
- `installer/` — 원래 설치 프로그램(1.5)과 리소스 교체 도구(`Repack.cs`)
- `dist/` — 빌드 결과 (`RetopoAnnotate_Setup.exe`, `RAKeys.dll`, 사용법 txt)
- `build.sh` — 빌드 스크립트 (mono와 Mono.Cecil.dll 필요)
