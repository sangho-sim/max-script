# ☕ 생두 알리미 (Green Bean Mirror)

국내 생두 쇼핑몰들의 상품을 한곳에 모아(미러링) 보여 주고, 새 생두가 입고되면 **카카오톡으로 알려 주는** 스마트폰 앱입니다.

```
greenbean-app/
├── server/   Node.js 서버 — 쇼핑몰 수집(크롤링) · 검색 API · 카카오톡 알림
└── mobile/   Expo(React Native) 앱 — iOS / Android (웹 미리보기도 가능)
```

## 🚀 간편 설치 (파일 더블클릭)

**준비물**: PC(Windows 또는 Mac), 휴대폰에 **Expo Go** 앱 (앱스토어·플레이스토어에서 무료 설치), PC와 휴대폰은 **같은 와이파이**

1. **내려받기** — GitHub 에서 이 브랜치를 열고 **Code → Download ZIP** → 압축 풀기
   (또는 `git clone -b claude/admiring-turing-h0vhsn https://github.com/sangho-sim/max-script.git`)
2. `greenbean-app` 폴더에서 더블클릭

   | Windows | Mac | 하는 일 |
   |---|---|---|
   | `생두알리미 샘플 체험.bat` | `생두알리미 샘플 체험.command` | 샘플 생두로 앱 둘러보기 (쇼핑몰 접속 없음) |
   | `생두알리미 실행.bat` | `생두알리미 실행.command` | 실제 쇼핑몰 수집 + 앱 실행 |
   | `카카오톡 알림 설정.bat` | `카카오톡 알림 설정.command` | 카카오 키를 묻고 설정 파일을 만들어 줌 |

   - 처음 실행하면 필요한 것을 **알아서 설치**합니다 (몇 분). Node.js 가 없으면 설치를 도와줍니다 (Windows 는 자동 설치 선택 가능).
   - PC 의 와이파이 IP 를 찾아 앱이 서버를 바라보게 **자동으로** 맞춥니다.
   - Windows 방화벽 창이 뜨면 **허용**을 눌러 주세요.
3. 창에 나온 **QR 코드**를 휴대폰으로 찍기 (아이폰: 기본 카메라 / 안드로이드: Expo Go 앱 안에서) → 앱이 열립니다
4. 카카오톡 알림을 받으려면 `카카오톡 알림 설정` 을 한 번 실행 → 안내대로 카카오 개발자 사이트에서 3가지 등록 → 다시 `생두알리미 실행` → 앱 **🔔 알림** 탭에서 “카카오톡으로 알림 받기”

끄려면 창을 닫으면 됩니다. 서버 기록은 `server/data/server.log` 에 남습니다.

> Mac 에서 ZIP 으로 받았다면 처음 한 번 터미널에서 `chmod +x *.command` 가 필요할 수 있어요.
> 휴대폰이 다른 네트워크(LTE 등)에 있으면 터미널에서 `npm start -- --tunnel`.
> 터미널이 편하면: `npm run demo` · `npm start` · `npm run setup:kakao` (`greenbean-app` 폴더에서)

## 기능

| 기능 | 설명 |
|---|---|
| 통합 검색 | 이름·산지·품종·가공·컵노트·회사를 한 칸에서 검색. 표기가 달라도 찾음 (`게샤`=`게이샤`, `yirgacheffe`→에티오피아, `natural`=`내추럴`) |
| 필터 | 산지 / 품종 / 가공방식 / 맛(향미 계열) / 회사 / 가격(상품가 또는 **1kg당 가격**) / 재고만 / 7일 내 입고, 정렬 6가지 |
| 키워드 | 쇼핑몰 카테고리 분류를 참고한 추천 키워드(가공방식·등급·품종·특징·유명 산지·인증·용도·맛)에서 골라 **내 키워드 칩**으로 등록, 직접 입력도 가능 |
| 썸네일 목록 | 2열 썸네일 카드, NEW·재입고·할인율 배지, 품절 표시, 썸네일 아래 **향미 색 띠** |
| 컵노트 한눈에 | 노트마다 향미 계열 색+이모지 칩 (🌸꽃향 🍋시트러스 🍓베리 🍑과일 🥭열대 🍷와인·발효 🍵차 🍯단맛 🍫초콜릿 🌰견과 🍞곡물 🌶️향신료 🌲흙·우디), 계열 비중 막대, **산미·단맛·바디 그래프** |
| 구매 이동 | 상세 화면의 **구매하기** 버튼 → 그 생두를 파는 쇼핑몰 상품 페이지 |
| 카카오톡 알림 | 신규 입고 / 재입고를 카카오톡 “나와의 채팅”으로. **알림 받을 쇼핑몰 선택**, 산지·키워드·1kg당 최대 가격 조건 |

## 수집하는 쇼핑몰

`server/src/shops.js` 에 있습니다 (현재 19곳):
알마씨엘로, 코빈즈커피, 지에스씨(GSC), 엠아이커피, 더블유빈즈, 로얄커피코리아, 블레스빈, 세웅지씨, 소펙스코리아, 커피리브레, 레햄코리아(RNC), 나무사이로, 커피스펠, 커피미업, 에이션빈, 커피플랜트, 블랙로드커피, 모모스커피, 팔콘 마이크로 코리아.

쇼핑몰 디자인(스킨)은 제각각이지만, 국내 몰은 대부분 **Cafe24 · 고도몰 · 영카트 · 위사 · 메이크샵 · 아임웹** 위에서 돌아가고 플랫폼마다 **상품 링크 주소 모양이 고정**입니다. 그래서 크롤러는 스킨이 아니라 링크 모양으로 상품을 찾고, 그 링크를 감싼 카드에서 이름·썸네일·가격·품절을 뽑습니다. Shopify 몰과 모모스커피는 공개 JSON 을 읽습니다.
새 상품은 상세 페이지도 한 번 읽어서 설명·컵노트·옵션(중량)을 보강합니다. 이미 본 상품은 14일마다만 다시 읽습니다.

### 쇼핑몰 추가하기

`server/src/shops.js` 에 한 줄 추가합니다.

```js
{
  id: 'myshop', name: '마이 생두몰', homepage: 'https://myshop.co.kr',
  source: 'html', platform: 'cafe24',          // cafe24 | godomall | youngcart | wisa | makeshop | imweb
  listUrls: ['https://myshop.co.kr/product/list.html?cate_no=42&page={page}'], maxPages: 5,
},
```

저장 없이 결과만 확인: `cd server && npm run crawl -- --dry myshop`

## 1. 서버 실행 (직접 실행할 때)

Node.js 20.12 이상.

```bash
cd server
npm install
npm test                 # 테스트
npm run demo             # 샘플 데이터로 실행 (쇼핑몰 접속 없음) → http://localhost:8787
npm start                # 실제 수집 + API + 알림
npm run crawl            # 한 번만 수집 (npm run crawl -- gsc sopex 처럼 일부만)
```

설정은 환경 변수나 `server/.env` 파일(간편 설정이 만들어 줌)에 적습니다.

| 이름 | 기본값 | 설명 |
|---|---|---|
| `PORT` | `8787` | |
| `PUBLIC_BASE_URL` | `http://localhost:8787` | 휴대폰·카카오가 접속할 서버 주소 (https 권장) |
| `CRAWL_INTERVAL_MIN` | `60` | 몇 분마다 수집할지 |
| `CRAWL_DELAY_MS` | `1500` | 같은 몰에 보내는 요청 사이 간격 |
| `SHOPS` | (전체) | `gsc,almacielo` 처럼 일부 몰만 |
| `KAKAO_REST_API_KEY` | | 카카오 앱 REST API 키 |
| `KAKAO_CLIENT_SECRET` | | 카카오 앱에서 Client Secret 을 켰다면 |
| `KAKAO_REDIRECT_URI` | `{PUBLIC_BASE_URL}/auth/kakao/callback` | |
| `ADMIN_TOKEN` | | `POST /api/admin/crawl` 로 즉시 수집할 때 쓰는 토큰 |
| `DATA_FILE` | `server/data/db.json` | 저장 파일 |

데이터는 JSON 파일 하나에 저장됩니다(생두 수천 개 규모라 DB 없이 충분).
휴대폰에서 알림 링크를 열려면 서버가 인터넷에서 보여야 하므로, 실제로 쓸 때는 클라우드(예: Fly.io, Render, 가정용 서버 + 도메인)에 올려 `PUBLIC_BASE_URL` 을 그 주소로 두세요.

## 2. 카카오톡 알림 설정

카카오 **“나에게 보내기”** API 를 씁니다. 사용자가 앱에서 카카오 로그인을 한 번 하면, 서버가 그 사용자의 카카오톡 “나와의 채팅”으로 알림을 보냅니다. (비즈니스 채널·알림톡 계약 불필요)

1. [Kakao Developers](https://developers.kakao.com) → 내 애플리케이션 → 애플리케이션 추가
2. 앱 키의 **REST API 키** → `KAKAO_REST_API_KEY`
3. 플랫폼 → **Web** 사이트 도메인에 `PUBLIC_BASE_URL` 등록 (메시지 속 링크가 이 도메인이어야 열림 — 그래서 알림 링크는 서버의 `/go/<생두>` 를 거쳐 쇼핑몰로 넘어갑니다)
4. 카카오 로그인 **활성화**, Redirect URI 에 `{PUBLIC_BASE_URL}/auth/kakao/callback` 등록
5. 동의항목에서 **카카오톡 메시지 전송(talk_message)** 을 사용으로 설정 (닉네임은 선택)
6. (1~5 대신 `카카오톡 알림 설정.bat`/`.command` 를 실행하면 키를 묻고 등록할 주소를 알려 줍니다)
7. 서버 재시작 → 앱 **알림** 탭 → **카카오톡으로 알림 받기** → 로그인·동의 → “나와의 채팅”에 연결 완료 메시지가 옵니다

알림 규칙
- 몰을 **처음** 수집할 때 이미 있던 상품은 “신규”로 치지 않습니다 (알림 폭탄 방지).
- 한 번 수집에서 여러 개가 들어오면 한 메시지로 묶어 보냅니다 (1개면 사진 카드, 여러 개면 목록 + “외 N건”).
- **알림 받을 쇼핑몰**을 고르면 그 몰에 입고될 때만 옵니다. 산지·키워드(하나라도 포함)·1kg당 최대 가격 조건과 함께 쓸 수 있습니다.
- 액세스 토큰은 자동 갱신됩니다. 리프레시 토큰(약 2개월)이 만료되면 앱에 “다시 연결” 안내가 뜹니다.

## 3. 앱 실행 (직접 실행할 때)

```bash
cd mobile
npm install
EXPO_PUBLIC_API_URL=http://<내 PC의 IP>:8787 npx expo start
```

휴대폰에 **Expo Go** 를 설치하고 QR 을 찍으면 바로 실행됩니다. (`localhost` 는 휴대폰에서 PC 를 가리키지 않으니 PC 의 IP 나 서버 주소를 쓰세요.)
스토어용 빌드는 `npx eas-cli@latest build` (Expo 계정 필요). 앱 스킴은 `greenbean://` 입니다.

화면
- **생두** — 검색창, 필터 칩(산지·품종·가공·맛·회사·가격·재고만·7일 내 입고), 내 키워드 칩, 썸네일 그리드, 정렬
- **상세** — 큰 썸네일, 컵노트 칩·향미 비중·맛 그래프, 산지/품종/가공/중량/판매처(누르면 그 조건으로 목록 필터), 구매하기 버튼
- **키워드** — 내 키워드 관리, 추천 키워드 묶음, 지금 판매 중인 품종·많이 쓰인 컵노트
- **알림** — 카카오톡 연결/테스트/해제, 신규·재입고, 알림 받을 쇼핑몰, 산지, 키워드, 1kg당 최대 가격

## API

| 요청 | 설명 |
|---|---|
| `GET /api/beans?q=&origin=&variety=&process=&flavor=&shop=&keyword=&minPrice=&maxPrice=&priceBasis=item\|kg&inStock=1&newWithinDays=&sort=new\|price_asc\|price_desc\|kg_asc\|kg_desc\|name&page=&pageSize=` | 검색 (목록 값은 쉼표로 여러 개) |
| `GET /api/beans/:id` | 생두 하나 |
| `GET /api/meta` | 필터 항목·개수, 추천 키워드, 향미 색, 쇼핑몰 상태 |
| `GET /go/:id` | 쇼핑몰 상품 페이지로 이동 |
| `GET /api/devices/:deviceId` · `PUT …/alerts` · `POST …/test` · `DELETE …/kakao` | 알림 설정 |
| `GET /auth/kakao/login?device=` | 카카오 연결 시작 |

## 알아 둘 점

- 쇼핑몰이 디자인·카테고리를 바꾸면 그 몰 수집이 멈출 수 있습니다. 서버 로그와 앱 알림 탭의 쇼핑몰 목록(“수집 오류”)에서 확인하고 `shops.js` 를 고치세요. `npm run crawl -- --dry <몰id>` 로 바로 확인할 수 있습니다.
- 산지·품종·가공·컵노트는 상품명과 상세 설명의 글자를 사전(`server/src/dictionaries/`)과 맞춰서 뽑습니다. 상세 설명이 이미지로만 되어 있으면 컵노트가 비어 있을 수 있습니다. 사전에 표현을 추가하면 다음 수집부터 반영됩니다. 맛 그래프는 컵노트로부터 추정한 값입니다.
- 크롤러는 `robots.txt` 를 지키고, 몰마다 요청 간격을 두며, 새 상품만 상세 페이지를 읽습니다. 각 쇼핑몰의 이용약관을 확인하고 개인·비상업 용도로 적당한 주기로 쓰세요.
- 네이버 스마트스토어 몰은 로그인 없이 목록을 읽기 어려워 넣지 않았습니다.
