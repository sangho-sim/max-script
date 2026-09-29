// DEMO_DATA=1 일 때 넣는 샘플 생두. 실제 쇼핑몰 상품이 아니라 화면 확인용이며, 가상의 '데모 생두몰' 소속이다.
export const DEMO_SHOP = { id: 'demo', name: '데모 생두몰', homepage: 'https://example.com' };

const RAW = [
  ['에티오피아 예가체프 G1 워시드 코케 1kg', 16500, '컵노트: 자스민, 레몬, 베르가못, 홍차'],
  ['에티오피아 구지 함벨라 G1 내추럴 1kg', 18900, '컵노트: 블루베리, 딸기, 다크초콜릿, 와인'],
  ['케냐 니에리 AA 워시드 SL28 SL34 1kg', 21000, 'Cup Notes: 블랙커런트, 자몽, 토마토, 긴 여운의 밝은 산미'],
  ['콜롬비아 우일라 수프리모 워시드 1kg', 12500, '컵노트: 캐러멜, 밀크초콜릿, 사과, 부드러운 바디'],
  ['콜롬비아 엘 파라이소 핑크 버번 더블 무산소 500g', 29000, '테이스팅 노트: 리치, 복숭아, 장미, 요거트'],
  ['브라질 세하도 NY2 17/18 내추럴 옐로우 버번 1kg', 9800, '컵노트: 땅콩, 코코아, 흑설탕, 묵직한 바디'],
  ['과테말라 안티구아 SHB 워시드 버번 카투라 1kg', 13500, '컵노트: 다크초콜릿, 시나몬, 오렌지, 스모키'],
  ['코스타리카 타라주 SHB 레드 허니 카투아이 1kg', 15800, '컵노트: 꿀, 살구, 브라운슈가, 쥬시한 산미'],
  ['파나마 보케테 게이샤 워시드 마이크로랏 200g', 42000, '컵노트: 자스민, 복숭아, 베르가못, 꿀, 티 라이크'],
  ['인도네시아 수마트라 만델링 G1 세미워시드 1kg', 12000, '컵노트: 흙내음, 삼나무, 다크초콜릿, 허브, 묵직한 바디'],
  ['과테말라 우에우에테낭고 디카페인 스위스워터 1kg', 17500, '컵노트: 밀크초콜릿, 아몬드, 캐러멜'],
  ['르완다 후예 레드 버번 내추럴 1kg', 16800, '컵노트: 라즈베리, 히비스커스, 자두, 와인'],
  ['엘살바도르 산타아나 파카마라 워시드 COE 1kg', 26000, '컵노트: 포도, 자몽, 메이플 시럽, 실키한 바디'],
  ['예멘 모카 마타리 내추럴 500g', 38000, '컵노트: 건포도, 와인, 카다멈, 다크초콜릿'],
  ['페루 카하마르카 유기농 공정무역 워시드 1kg', 11900, '컵노트: 헤이즐넛, 밀크초콜릿, 오렌지'],
  ['하와이 코나 엑스트라 팬시 500g', 55000, '컵노트: 마카다미아, 버터, 꿀, 부드러운 산미'],
  ['탄자니아 킬리만자로 AA 워시드 1kg', 14200, '컵노트: 블랙베리, 레몬, 흑설탕'],
  ['베트남 로부스타 스크린 18 5kg', 32000, '컵노트: 곡물, 다크초콜릿, 담배'],
];

export function demoRawProducts() {
  return RAW.map(([name, price, notes], i) => ({
    productId: String(1000 + i),
    url: `https://example.com/demo/${1000 + i}`,
    name,
    imageUrl: null,
    price,
    listPrice: i % 4 === 0 ? Math.round(price * 1.15 / 100) * 100 : null,
    soldOut: i === 13,
    description: null,
    detailText: notes,
    detailFetchedAt: new Date().toISOString(),
  }));
}

export function loadDemoData(store, now = new Date()) {
  const raws = demoRawProducts();
  // 절반은 '며칠 전' 입고, 나머지는 '방금' 입고로 보이게 두 번에 나눠 넣는다
  store.applyCrawl(DEMO_SHOP, raws.slice(0, 12), { ok: false, now: new Date(now - 5 * 86400_000) });
  store.applyCrawl(DEMO_SHOP, raws.slice(12), { ok: false, now });
  store.save();
  return raws.length;
}
