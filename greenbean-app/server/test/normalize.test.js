import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeProduct, detectOrigin, detectNotes, parseWeightGrams, parsePrice, extractNoteSegments } from '../src/normalize.js';

const shop = { id: 'x', name: '테스트몰' };

test('산지: 국가명·지역명·영문 모두 인식', () => {
  assert.equal(detectOrigin('에티오피아 예가체프 G1').country, '에티오피아');
  assert.equal(detectOrigin('예가체프 코케 워시드').country, '에티오피아');
  assert.equal(detectOrigin('예가체프 코케 워시드').region, '예가체프');
  assert.equal(detectOrigin('Kenya Nyeri AA').country, '케냐');
  assert.equal(detectOrigin('타라주 레드허니').country, '코스타리카');
  assert.equal(detectOrigin('수마트라 만델링 G1').country, '인도네시아');
});

test('산지: 짧은 이름이 긴 이름 안에서 잘못 잡히지 않음', () => {
  assert.equal(detectOrigin('인도네시아 아체 가요').country, '인도네시아');
  assert.equal(detectOrigin('인도 몬순드 말라바 AA').country, '인도');
  assert.equal(detectOrigin('과테말라 라 에스페란사').country, '과테말라');
});

test('노트: 긴 표현 우선, 한 글자 노트는 단어 경계 필요', () => {
  const labels = (t) => detectNotes(t).map((n) => n.label);
  assert.deepEqual(labels('블루베리, 다크 초콜릿, 자스민'), ['블루베리', '다크초콜릿', '자스민']);
  assert.deepEqual(labels('컬럼비아 수프리모'), []); // '럼' 이 잡히면 안 됨
  assert.deepEqual(labels('꿀, 귤'), ['꿀', '귤']);
  assert.deepEqual(labels('꿀향과 귤맛'), ['꿀', '귤']);
  assert.deepEqual(labels('리치한 바디감'), []); // rich ≠ 리치(lychee)
  assert.deepEqual(labels('커피 체리를 통째로 건조'), []);
});

test('중량/가격 파싱', () => {
  assert.equal(parseWeightGrams('케냐 AA 1kg'), 1000);
  assert.equal(parseWeightGrams('게이샤 200g'), 200);
  assert.equal(parseWeightGrams('0.5 KG'), 500);
  assert.equal(parseWeightGrams('SHB 17/18'), null);
  assert.equal(parsePrice('12,500원'), 12500);
  assert.equal(parsePrice('₩ 9,900'), 9900);
  assert.equal(parsePrice(''), null);
});

test('컵노트 구간만 떼어 냄 (메뉴 글자는 무시)', () => {
  const segs = extractNoteSegments('메뉴: 초콜릿 소스 | 원두 ... 상품설명 ... 컵노트: 자스민, 레몬');
  assert.equal(segs.length, 1);
  assert.match(segs[0], /자스민, 레몬/);
});

test('상품 하나를 앱용 레코드로', () => {
  const b = normalizeProduct(
    {
      productId: '7',
      url: 'https://shop/7',
      name: '콜롬비아 우일라 핑크버번 무산소 내추럴 500g',
      price: '29,000원',
      listPrice: '32,000원',
      detailText: 'Tasting Notes: 딸기, 리치, 요거트, 장미',
    },
    shop,
  );
  assert.equal(b.id, 'x:7');
  assert.equal(b.origin.country, '콜롬비아');
  assert.equal(b.origin.region, '우일라');
  assert.deepEqual(b.varieties, ['핑크 버번']);
  assert.deepEqual(b.processes, ['무산소 발효', '내추럴']);
  assert.deepEqual(b.notes.map((n) => n.label), ['딸기', '리치', '요거트', '장미']);
  assert.equal(b.weightGrams, 500);
  assert.equal(b.pricePerKg, 58000);
  assert.equal(b.listPrice, 32000);
  assert.ok(b.profile.acidity >= 3);
  assert.equal(b.flavorMix.reduce((s, m) => s + m.ratio, 0), 1);
});
