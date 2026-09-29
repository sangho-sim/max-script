// 쇼핑몰에서 긁어 온 원본 상품(이름·설명·상세 텍스트)을 앱이 쓰는 생두 레코드로 바꾼다.
import { ORIGINS } from './dictionaries/origins.js';
import { VARIETIES, PROCESSES, TAGS } from './dictionaries/attributes.js';
import { FLAVOR_CATEGORIES, FLAVOR_NOTES, PROFILE_WORDS } from './dictionaries/flavors.js';
import { buildMatcher, findAll, findEntries, normText } from './match.js';

const countryMatcher = buildMatcher(ORIGINS, (o) => [...o.aliases, o.country, o.en]);
const regionMatcher = buildMatcher(
  ORIGINS.flatMap((o) => o.regions.map((r) => ({ region: r, origin: o }))),
  (r) => [r.region],
);
const varietyMatcher = buildMatcher(VARIETIES, (v) => [v.name, v.en, ...v.aliases]);
const processMatcher = buildMatcher(PROCESSES, (p) => [p.name, p.en, ...p.aliases]);
const tagMatcher = buildMatcher(TAGS, (t) => [t.name, ...t.aliases]);
const noteMatcher = buildMatcher(FLAVOR_NOTES, (n) => [n.label, ...n.aliases]);
const CATEGORY = Object.fromEntries(FLAVOR_CATEGORIES.map((c) => [c.id, c]));

// 상세페이지 본문에서 컵노트가 적힌 부분만 떼어 낸다. 본문 전체를 쓰면 메뉴·추천상품 글자까지 노트로 잡힌다.
const NOTE_MARKER = /(컵\s*노트|cup\s*notes?|테이스팅\s*노트|tasting\s*notes?|향미\s*노트|플레이버|flavou?r\s*notes?|flavou?rs?|노트|향미|aroma|아로마|맛\s*표현|cupping\s*notes?)\s*[:：\-–>]?/gi;

export function extractNoteSegments(detailText, maxLen = 140) {
  const text = String(detailText ?? '').replace(/\s+/g, ' ');
  const segs = [];
  for (const m of text.matchAll(NOTE_MARKER)) {
    segs.push(text.slice(m.index + m[0].length, m.index + m[0].length + maxLen));
    if (segs.length >= 6) break;
  }
  return segs;
}

/** '1kg', '500 g', '0.5kg', '1키로' … → 그램 */
export function parseWeightGrams(text) {
  const t = String(text ?? '');
  const m = t.match(/(\d+(?:\.\d+)?)\s*(kg|킬로그램|킬로|키로|g|그램)(?![a-z])/i);
  if (!m) return null;
  const n = parseFloat(m[1]);
  if (!Number.isFinite(n) || n <= 0) return null;
  const unit = m[2].toLowerCase();
  const grams = unit === 'g' || unit === '그램' ? n : n * 1000;
  // 100g 미만/100kg 초과는 중량이 아니라 다른 숫자일 가능성이 크다
  if (grams < 100 || grams > 100000) return null;
  return Math.round(grams);
}

/** '12,500원', '₩ 9,900', '9900' → 숫자 */
export function parsePrice(text) {
  if (text == null) return null;
  if (typeof text === 'number') return Number.isFinite(text) && text > 0 ? Math.round(text) : null;
  const m = String(text).replace(/\s/g, '').match(/(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?/);
  if (!m) return null;
  const n = parseInt(m[1].replace(/,/g, ''), 10);
  return n > 0 ? n : null;
}

export function detectOrigin(...texts) {
  for (const text of texts) {
    if (!text) continue;
    const country = findEntries(text, countryMatcher)[0];
    const regionHits = findAll(text, regionMatcher);
    if (country) {
      const region = regionHits.find((h) => h.entry.origin === country);
      return originOut(country, region);
    }
    if (regionHits.length) return originOut(regionHits[0].entry.origin, regionHits[0]);
  }
  return null;
}

function originOut(o, regionHit) {
  return {
    country: o.country,
    en: o.en,
    flag: o.flag,
    continent: o.continent,
    region: regionHit ? prettyRegion(regionHit.entry.region) : null,
  };
}

function prettyRegion(r) {
  return /^[\x00-\x7f]+$/.test(r) ? r.replace(/\b\w/g, (c) => c.toUpperCase()) : r;
}

export function detectNotes(...texts) {
  const out = [];
  const seen = new Set();
  for (const text of texts) {
    for (const n of findEntries(text, noteMatcher)) {
      if (seen.has(n.label)) continue;
      seen.add(n.label);
      out.push({ label: n.label, category: n.category });
    }
  }
  return out.slice(0, 10);
}

/** 노트 카테고리와 '밝은 산미' 같은 표현으로 산미/단맛/바디를 1~5 로 어림한다. 근거가 없으면 null. */
export function estimateProfile(notes, text) {
  if (!notes.length) return null;
  const sum = { acidity: 0, sweetness: 0, body: 0 };
  for (const n of notes) {
    const p = CATEGORY[n.category]?.profile;
    if (!p) continue;
    for (const k of Object.keys(sum)) sum[k] += p[k];
  }
  const t = normText(text);
  for (const [k, words] of Object.entries(PROFILE_WORDS)) {
    for (const w of words) if (t.includes(w)) sum[k] += 0.7;
  }
  const max = Math.max(1.5, sum.acidity, sum.sweetness, sum.body);
  const scale = (v) => Math.max(1, Math.min(5, Math.round(1 + (v / max) * 4)));
  return { acidity: scale(sum.acidity), sweetness: scale(sum.sweetness), body: scale(sum.body) };
}

/** 노트 카테고리별 비중 (앱의 색 막대). */
export function flavorMix(notes) {
  const counts = {};
  for (const n of notes) counts[n.category] = (counts[n.category] ?? 0) + 1;
  const total = notes.length || 1;
  return Object.entries(counts)
    .map(([id, c]) => ({ category: id, ratio: Math.round((c / total) * 100) / 100 }))
    .sort((a, b) => b.ratio - a.ratio);
}

const uniq = (arr) => [...new Set(arr)];

/**
 * @param {object} raw  { productId, url, name, imageUrl, price, listPrice, soldOut, description, detailText, optionText }
 * @param {object} shop { id, name, homepage }
 */
export function normalizeProduct(raw, shop) {
  const name = String(raw.name ?? '').replace(/\s+/g, ' ').trim();
  const desc = String(raw.description ?? '').replace(/\s+/g, ' ').trim();
  // noteText: 예전에 상세 페이지에서 뽑아 둔 컵노트 부분 (상세를 다시 안 읽었을 때 재사용)
  const noteSegs = raw.noteText ?? extractNoteSegments(raw.detailText).join(' | ');
  const nameAndDesc = `${name} ${desc}`;

  const notes = detectNotes(noteSegs, name, desc);
  const weightGrams = parseWeightGrams(name) ?? parseWeightGrams(raw.optionText) ?? null;
  const price = parsePrice(raw.price);
  const listPrice = parsePrice(raw.listPrice);

  return {
    id: `${shop.id}:${raw.productId}`,
    shopId: shop.id,
    shopName: shop.name,
    productId: String(raw.productId),
    name,
    url: raw.url,
    imageUrl: raw.imageUrl ?? null,
    price,
    listPrice: listPrice && price && listPrice > price ? listPrice : null,
    weightGrams,
    pricePerKg: price && weightGrams ? Math.round((price * 1000) / weightGrams) : null,
    soldOut: Boolean(raw.soldOut),
    origin: detectOrigin(name, desc, noteSegs),
    varieties: uniq(findEntries(`${nameAndDesc} ${noteSegs}`, varietyMatcher).map((v) => v.name)),
    processes: uniq(findEntries(nameAndDesc, processMatcher).map((p) => p.name)),
    tags: uniq(findEntries(nameAndDesc, tagMatcher).map((t) => t.name)),
    notes,
    flavorMix: flavorMix(notes),
    profile: estimateProfile(notes, `${noteSegs} ${desc}`),
    description: desc.slice(0, 300) || null,
    // 다음 크롤에서 상세 페이지를 다시 읽지 않아도 같은 결과를 내도록 원문 일부를 보관 (API 응답에서는 뺀다)
    _src: {
      description: desc || null,
      noteText: noteSegs || null,
      optionText: raw.optionText || null,
      detailFetchedAt: raw.detailFetchedAt ?? null,
    },
  };
}
