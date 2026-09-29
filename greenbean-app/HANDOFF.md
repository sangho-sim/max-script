# 생두 알리미 — 인수인계 (2026-09-29)

새 세션에서 이 파일부터 읽고 시작하세요. 코드 설명은 `README.md`, 이 파일은 **지금 어디까지 왔고 무엇이 남았는지**입니다.

## 새 세션 시작할 때 붙여 넣을 말

```
sangho-sim/max-script 저장소의 claude/admiring-turing-h0vhsn 브랜치를 체크아웃하고
greenbean-app/HANDOFF.md 를 읽은 뒤, "남은 일" 에서 이어서 작업해 줘.
```

> 이 앱은 아직 기본 브랜치에 병합되지 않았습니다. 반드시 위 브랜치에서 작업하세요.

## 한 줄 요약

국내 생두 쇼핑몰 19곳의 상품을 모아 검색·필터하고(스마트폰 앱), 새 생두가 들어오면 카카오톡 “나와의 채팅”으로 알려 주는 앱. 서버(Node.js) + 앱(Expo) 구성.

- 저장소: `sangho-sim/max-script` (원래는 3ds Max 스크립트 저장소 — 앱은 `greenbean-app/` 폴더에만 있음)
- 브랜치: `claude/admiring-turing-h0vhsn`
- PR: https://github.com/sangho-sim/max-script/pull/2 (draft, 기본 브랜치 `claude/retopology-mesh-performance-nct6ec` 대상, 충돌 없음, CI 없음, 리뷰 코멘트 없음)
- 커밋: `140f956` 앱 본체, `305476c` 간편 설치

## 사용자에 대해

- 한국어로 대화. 개발자가 아닐 가능성이 높음 → 명령어보다 **더블클릭·단계별 안내**를 선호.
- Windows 사용자로 추정 (저장소에 .exe·3ds Max 파일). Mac 도 지원해 둠.
- 요청 이력
  1. 한국에서 살 수 있는 생두 정보를 미러링하는 앱: 이름·산지·품종·키워드·가격·회사별 검색, 쇼핑몰 참고한 검색 키워드 설정, 썸네일, 컵노트를 직관적으로, 누르면 구매 페이지, 신규 입고 시 카톡 알림
  2. **원하는 쇼핑몰에서만 알림** 받게 (→ 알림 탭의 쇼핑몰 선택, 구현 완료)
  3. 사용법 안내 → 간편 설치 요청 (→ .bat/.command 더블클릭 실행기, 구현 완료)
  4. `https://t1.daumcdn.net/osa/notice/26/1wV1gSwjRc/NOTICE.html` 에 카톡 알림 코드가 있는지 질문 → 이전 세션은 네트워크 차단으로 **열어 보지 못함**. 주소 모양상 카카오의 오픈소스 라이선스 고지 페이지로 추정(코드 없음). 사용자가 “직접 컴퓨터 조작해서 받아 달라”고 했으나 그 세션엔 컴퓨터 조작 기능이 없었음.

## 구조

```
greenbean-app/
├── 생두알리미 실행.bat / .command         실제 수집 + 앱
├── 생두알리미 샘플 체험.bat / .command    샘플 데이터 (쇼핑몰 접속 없음)
├── 카카오톡 알림 설정.bat / .command      카카오 키 입력 → server/.env
├── scripts/launch.mjs       간편 실행기: 첫 실행 시 npm install, 내부 IP 찾기, 서버+Expo 동시 실행
├── scripts/setup-kakao.mjs  카카오 설정 도우미
├── server/
│   ├── src/shops.js           몰 목록(19곳)과 목록 페이지 URL  ← 몰 추가/수정은 여기
│   ├── src/crawler/           platforms.js(플랫폼별 상품 링크 규칙) · parse.js(목록/상세 파싱) · crawl.js · fetch.js(robots.txt, EUC-KR)
│   ├── src/dictionaries/      origins(산지) · attributes(품종/가공/태그) · flavors(컵노트 13계열)
│   ├── src/normalize.js       상품명/설명 → 산지·품종·가공·노트·kg당 가격
│   ├── src/search.js          검색·필터·패싯 (별칭: 게샤=게이샤 등)
│   ├── src/store.js           JSON 파일 저장, 신규/재입고/판매종료 판정
│   ├── src/kakao.js           카카오 OAuth + “나에게 보내기” + 메시지 템플릿
│   ├── src/notifier.js        사용자별 알림 조건(쇼핑몰·산지·키워드·kg당 가격) 적용
│   └── src/server.js          Express API, /go/:id 리다이렉트, 카카오 로그인 콜백
└── mobile/                    Expo SDK 57, expo-router (src/app/)
    ├── src/app/(tabs)/index.tsx     생두 목록·검색·필터
    ├── src/app/(tabs)/keywords.tsx  내 키워드
    ├── src/app/(tabs)/alerts.tsx    카카오 연결·알림 조건(쇼핑몰 선택 포함)
    └── src/app/bean/[id].tsx        상세·구매 이동
```

## 확인 방법

```bash
cd greenbean-app
npm test                          # 서버 29개 + 실행기 2개 (모두 통과 상태)
cd mobile && npx tsc --noEmit     # 타입 검사 (통과 상태)
cd .. && npm run demo             # 샘플 모드로 서버+앱 실행
cd server && npm run crawl -- --dry gsc   # 몰 하나 수집 결과만 출력 (저장 안 함)
```

## 확인된 것 / 안 된 것

| 항목 | 상태 |
|---|---|
| 서버 테스트(파싱·정규화·검색·알림·카카오 토큰 갱신·API) | ✅ 31개 통과 |
| 앱 화면(목록·필터·상세·키워드·알림) | ✅ 웹 빌드 + Playwright 스크린샷으로 확인 |
| 알림 탭에서 쇼핑몰 선택 → 서버 저장 | ✅ 확인 |
| 간편 실행기 (Linux 에서 끝까지) | ✅ 자동 설치 → 서버 → Expo QR 까지 확인 |
| **실제 쇼핑몰 수집** | ❌ 이전 세션 네트워크에서 몰 사이트가 403 으로 막혀 **한 번도 못 돌림**. 몰 목록 URL·플랫폼은 공개 정보로 구성 |
| Windows .bat / Mac .command 더블클릭 | ❌ 실제 기기에서 미확인 |
| 카카오톡 실제 발송 | ❌ 실제 카카오 앱 키로 미확인 (가짜 API 로 테스트만) |
| 카카오가 `http://192.168.x.x` 같은 내부 주소를 Redirect URI/도메인으로 받아 주는지 | ❓ 미확인. 안 되면 ngrok/Cloudflare Tunnel 의 https 주소 사용 |

## 남은 일 (우선순위 순)

1. **실제 수집 검증** — 쇼핑몰 사이트에 접속 가능한 환경에서 `npm run crawl -- --dry <몰id>` 를 몰마다 돌려 보고, 0개이거나 이름/가격이 이상한 몰은 `server/src/shops.js`(목록 URL) 또는 `server/src/crawler/parse.js`(파싱) 수정. 수정할 때 `server/test/fixtures/` 에 실제 HTML 일부를 넣고 테스트 추가.
2. **사용자 PC 에서 실행 확인** — 사용자가 `.bat` 실행 중 오류 화면을 보내면 대응. 특히 한글 경로/파일명, `chcp 65001`, 방화벽, Expo Go 버전.
3. **카카오 실제 연동** — 사용자와 함께 카카오 개발자 앱 등록 → `카카오톡 알림 설정` → 테스트 알림.
4. 사용자 질문(NOTICE.html) — 페이지 내용을 받거나 열어 보고 답하기. 카톡 알림 코드는 이미 `server/src/kakao.js` 에 있음.
5. (제안만 해 둔 것) PC 없이 24시간 알림: 서버 클라우드 배포(Render/Fly.io 등) 설정. Expo Go 없이 설치하는 안드로이드 APK(EAS, Expo 계정 필요). 앱 안에서 서버 주소 바꾸는 설정 화면.

## 이전 세션에서 겪은 환경 문제 (클라우드 세션일 때)

- 네트워크 정책이 쇼핑몰 사이트, `t1.daumcdn.net`, `docs.expo.dev`, `api.expo.dev` 등을 막았음. 필요하면 사용자에게 환경 설정(세션 제목 줄의 클라우드 환경 메뉴 → Edit → Network access)에서 허용 도메인 추가를 요청.
- `npx expo install` 은 api.expo.dev 가 막혀 실패 → `EXPO_OFFLINE=1 npx expo install <패키지>` 로 해결.
- 웹 빌드 확인: `EXPO_OFFLINE=1 CI=1 npx expo export --platform web`, Playwright 는 `/opt/pw-browsers/chromium-1194/chrome-linux/chrome` 사용.
- `mobile/AGENTS.md` 규칙: 패키지는 `npx expo install` 로, 끝내기 전에 `npx tsc --noEmit`.

## 참고

- 몰 목록 URL 은 공개 저장소 [sheutsum/green-coffee-radar](https://github.com/sheutsum/green-coffee-radar) 를 참고함 (라이선스가 없어 코드는 가져오지 않았음).
- 커밋 메시지·PR 에 모델 이름을 넣지 않기.
