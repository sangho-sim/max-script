import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { parseListing, parseDetail } from '../src/crawler/parse.js';
import { PLATFORMS } from '../src/crawler/platforms.js';
import { crawlShop } from '../src/crawler/crawl.js';
import { parseRobots, robotsAllows } from '../src/crawler/fetch.js';

const fixture = (n) => fs.readFileSync(new URL(`./fixtures/${n}`, import.meta.url), 'utf8');

test('Cafe24 목록: 숨김 항목명 제거, 적립금 무시, 품절 아이콘, 지연 로딩 이미지, 다른 카테고리 배너 제외', () => {
  const items = parseListing(fixture('cafe24_list.html'), 'https://sopexkorea.com/product/list.html?cate_no=24&page=1', PLATFORMS.cafe24);
  const byId = Object.fromEntries(items.map((i) => [i.productId, i]));
  assert.deepEqual(Object.keys(byId).sort(), ['101', '102', '103', '104']);
  assert.equal(byId['101'].name, '에티오피아 예가체프 G1 워시드 코케 1kg');
  assert.equal(byId['101'].price, 16500);
  assert.equal(byId['101'].soldOut, false);
  assert.equal(byId['101'].url, 'https://sopexkorea.com/product/detail.html?product_no=101');
  assert.equal(byId['101'].imageUrl, 'https://sopexkorea.com/web/product/medium/202609/abc.jpg');
  assert.equal(byId['102'].price, 45000);
  assert.equal(byId['102'].listPrice, 52000);
  assert.equal(byId['102'].soldOut, true);
  assert.equal(byId['102'].imageUrl, 'https://sopexkorea.com/web/product/medium/202609/def.jpg');
  assert.equal(byId['103'].price, 12500);
});

test('고도몰 목록', () => {
  const items = parseListing(fixture('godomall_list.html'), 'https://www.micoffee.co.kr/goods/goods_list.php?cateCd=001', PLATFORMS.godomall);
  assert.equal(items.length, 2);
  assert.equal(items[0].name, '[1월 추천 생두] 콜롬비아 라 알데아 게이샤 워시드');
  assert.equal(items[0].price, 68000);
  assert.equal(items[1].price, 27000);
  assert.equal(items[1].listPrice, 30000);
  assert.equal(items[1].soldOut, true);
});

test('영카트 목록', () => {
  const items = parseListing(fixture('youngcart_list.html'), 'https://blessbean.co.kr/shop/list.php?ca_id=2010', PLATFORMS.youngcart);
  assert.equal(items.length, 2);
  assert.equal(items[0].name, '케냐 AA 키암부 가퉁구루 (1kg)');
  assert.equal(items[0].price, 19800);
  assert.equal(items[1].soldOut, true);
});

test('상세 페이지: og/상품 메타, 옵션, 본문', () => {
  const d = parseDetail(fixture('cafe24_detail.html'), 'https://sopexkorea.com/product/detail.html?product_no=101');
  assert.equal(d.price, 16500);
  assert.equal(d.listPrice, 18000);
  assert.equal(d.soldOut, false);
  assert.equal(d.imageUrl, 'https://sopexkorea.com/web/product/big/202609/abc.jpg');
  assert.match(d.optionText, /1kg \/ 5kg/);
  assert.match(d.detailText, /Cup Note : 자스민/);
  assert.doesNotMatch(d.detailText, /var x/);
});

test('crawlShop: 페이지 순회, 반복 페이지에서 멈춤, 새 상품만 상세 읽기, 생두 아닌 상품 제외', async () => {
  const requested = [];
  const fake = async (url) => {
    requested.push(url);
    if (url.includes('product_no=101')) return fixture('cafe24_detail.html');
    if (url.includes('detail.html')) return '<html><body>상세</body></html>';
    return fixture('cafe24_list.html'); // 모든 페이지가 같은 목록 → 2쪽에서 멈춰야 함
  };
  const shop = { id: 'sopex', name: '소펙스', source: 'html', platform: 'cafe24', listUrls: ['https://sopexkorea.com/product/list.html?cate_no=24&page={page}'], maxPages: 5 };
  const res = await crawlShop(shop, { fetchText: fake, robots: false, delayMs: 0, needsDetail: (id) => id === '101' });
  assert.equal(res.pages, 2);
  assert.deepEqual(res.products.map((p) => p.productId).sort(), ['101', '102', '103']); // 104 드립백 제외
  assert.equal(requested.filter((u) => u.includes('detail.html')).length, 1);
  const p101 = res.products.find((p) => p.productId === '101');
  assert.match(p101.detailText, /자스민/);
});

test('robots.txt', () => {
  const rules = parseRobots('User-agent: Googlebot\nDisallow: /\n\nUser-agent: *\nDisallow: /myshop/\nDisallow: /order/*.php$\nAllow: /myshop/public\n');
  assert.equal(robotsAllows(rules, '/product/list.html?cate_no=24'), true);
  assert.equal(robotsAllows(rules, '/myshop/index.html'), false);
  assert.equal(robotsAllows(rules, '/myshop/public/x'), true);
  assert.equal(robotsAllows(rules, '/order/basket.php'), false);
});
