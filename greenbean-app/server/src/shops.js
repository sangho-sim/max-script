// 미러링할 국내 생두 쇼핑몰 목록.
// source: 'html' 은 목록 페이지를 긁고(platform 규칙 사용), 'shopify' / 'momos' 는 몰이 공개한 JSON 을 읽는다.
// listUrls 의 {page} 는 페이지 번호로 바뀐다. 몰이 카테고리를 바꾸면 여기만 고치면 된다.
// 몰을 추가하려면 같은 모양으로 한 줄 넣으면 된다 (README '쇼핑몰 추가하기' 참고).

export const SHOPS = [
  {
    id: 'almacielo', name: '알마씨엘로', homepage: 'https://www.almacielo.com',
    source: 'html', platform: 'wisa',
    listUrls: ['https://www.almacielo.com/shop/big_section.php?cno1=1070&page={page}'], maxPages: 10,
  },
  {
    id: 'cobeans', name: '코빈즈커피', homepage: 'https://www.cobeans.com',
    source: 'html', platform: 'wisa',
    listUrls: ['https://www.cobeans.com/shop/big_section.php?cno1=1037&sort=1&page={page}'], maxPages: 5,
  },
  {
    id: 'gsc', name: '지에스씨(GSC)', homepage: 'https://www.gsc.coffee',
    source: 'html', platform: 'godomall',
    listUrls: ['https://www.gsc.coffee/goods/goods_list.php?cateCd=014&page={page}'], maxPages: 10,
  },
  {
    id: 'micoffee', name: '엠아이커피', homepage: 'https://www.micoffee.co.kr',
    source: 'html', platform: 'godomall',
    listUrls: ['001', '002', '003', '004', '024'].map((c) => `https://www.micoffee.co.kr/goods/goods_list.php?cateCd=${c}&page={page}`),
    maxPages: 6,
  },
  {
    id: 'wbeans', name: '더블유빈즈', homepage: 'https://www.wbeans.com',
    source: 'html', platform: 'godomall',
    listUrls: ['024', '003', '004', '005', '027'].map((c) => `https://www.wbeans.com/goods/goods_list.php?cateCd=${c}&page={page}`),
    maxPages: 6,
  },
  {
    id: 'royal', name: '로얄커피코리아', homepage: 'https://www.royalcoffeekorea.co.kr',
    source: 'html', platform: 'godomall',
    listUrls: ['https://www.royalcoffeekorea.co.kr/goods/goods_list.php?cateCd=039&page={page}'], maxPages: 6,
  },
  {
    id: 'blessbean', name: '블레스빈', homepage: 'https://blessbean.co.kr',
    source: 'html', platform: 'youngcart',
    listUrls: ['2010', '2020', '2030', '2040'].map((c) => `https://blessbean.co.kr/shop/list.php?ca_id=${c}&page={page}`),
    maxPages: 6,
  },
  {
    id: 'sewoong', name: '세웅지씨', homepage: 'https://www.sewoonggc.com',
    source: 'html', platform: 'youngcart',
    listUrls: ['10', '20', '30', '40', '50', '60'].map((c) => `https://www.sewoonggc.com/shop/list.php?ca_id=${c}&page={page}`),
    maxPages: 6,
  },
  {
    id: 'sopex', name: '소펙스코리아', homepage: 'https://sopexkorea.com',
    source: 'html', platform: 'cafe24',
    listUrls: [24, 26, 27, 66, 74].map((c) => `https://sopexkorea.com/product/list.html?cate_no=${c}&page={page}`),
    maxPages: 6,
  },
  {
    id: 'coffeelibre', name: '커피리브레', homepage: 'https://coffeelibre.kr',
    source: 'html', platform: 'cafe24',
    listUrls: ['https://coffeelibre.kr/product/list.html?cate_no=57&page={page}'], maxPages: 5,
  },
  {
    id: 'rnc', name: '레햄코리아(RNC)', homepage: 'https://rnccoffee.kr',
    source: 'html', platform: 'cafe24',
    listUrls: [43, 44, 45, 46, 47].map((c) => `https://rnccoffee.kr/product/list.html?cate_no=${c}&page={page}`),
    maxPages: 6,
  },
  {
    id: 'namusairo', name: '나무사이로', homepage: 'https://namusairo.green',
    source: 'html', platform: 'cafe24',
    listUrls: ['https://namusairo.green/product/list.html?cate_no=24&page={page}'], maxPages: 5,
  },
  {
    id: 'coffeespell', name: '커피스펠', homepage: 'https://coffeespell.co.kr',
    source: 'html', platform: 'cafe24',
    listUrls: ['https://coffeespell.co.kr/product/list.html?cate_no=25&page={page}'], maxPages: 5,
  },
  {
    id: 'coffeemeup', name: '커피미업', homepage: 'https://coffeemeup.store',
    source: 'html', platform: 'cafe24',
    listUrls: ['https://coffeemeup.store/product/list.html?cate_no=78&page={page}'], maxPages: 5,
  },
  {
    id: 'asianbean', name: '에이션빈', homepage: 'https://www.asianbean.co.kr',
    source: 'html', platform: 'makeshop',
    listUrls: ['007', '009', '010', '008', '011', '014', '015'].map((x) => `https://www.asianbean.co.kr/shop/shopbrand.html?xcode=${x}&type=X&page={page}`),
    maxPages: 5,
  },
  {
    id: 'coffeeplant', name: '커피플랜트', homepage: 'https://coffeeplant.co.kr',
    source: 'html', platform: 'imweb',
    listUrls: ['https://coffeeplant.co.kr/?page={page}'], maxPages: 5,
  },
  {
    id: 'blackroad', name: '블랙로드커피', homepage: 'https://blackroad.kr',
    source: 'html', platform: 'imweb',
    listUrls: ['https://blackroad.kr/37?page={page}'], maxPages: 5,
  },
  {
    id: 'momos', name: '모모스커피', homepage: 'https://momos.co.kr',
    source: 'momos', apiUrl: 'https://office.momos.co.kr/api/public/green-beans',
  },
  {
    id: 'falcon', name: '팔콘 마이크로 코리아', homepage: 'https://korea.falcon-micro.com',
    source: 'shopify', collection: 'korea-store-all-coffee', maxPages: 5,
  },
];

// 생두가 아닌 상품(용품·원두 등)이 생두 카테고리에 섞여 있을 때 거른다.
export const NOT_GREEN_BEAN = /(드립백|캡슐|콜드\s*브루|더치\s*커피|티백|머그|그라인더|드리퍼|로스터기|로스팅\s*기계|저울|주전자|케틀|템퍼|배송비|샘플러\s*키트|트레이|포대\s*자루|마대|원두\s*\d|로스팅\s*원두|원두커피)/;
