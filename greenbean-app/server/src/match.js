// 사전 기반 키워드 매칭. 여러 사전(산지·품종·노트…)이 같은 방식으로 텍스트에서 항목을 찾는다.
//  - 대소문자 무시, 공백은 하나로
//  - 영문/숫자 별칭은 단어 경계가 있어야 매칭 ('aa' 가 'kenyaa' 안에서 잡히지 않게)
//  - 한 글자 한글 별칭(귤, 꿀, 럼…)은 앞뒤가 다른 한글 음절과 붙어 있으면 무시 ('럼' ⊄ '컬럼비아')
//  - 겹치는 매칭은 더 긴 쪽이 이긴다 ('블루베리' 가 '베리' 보다 우선)

const HANGUL = /[가-힣]/;
const ASCII_WORD = /[a-z0-9]/;
// 한 글자 한글 별칭 뒤에 붙어도 되는 글자들 (꿀향, 귤맛, 꽃과 …)
const SINGLE_SUFFIX_OK = new Set(['향', '맛', '류', '과', '와', '의', '을', '를', '이', '가', '같', '처', '빛']);

export function normText(s) {
  return String(s ?? '').toLowerCase().replace(/\s+/g, ' ').trim();
}

/**
 * @param {Array<object>} entries 사전 항목
 * @param {(e: object) => string[]} aliasesOf 항목에서 별칭 목록을 꺼내는 함수
 */
export function buildMatcher(entries, aliasesOf) {
  const list = [];
  for (const entry of entries) {
    for (const alias of new Set(aliasesOf(entry).map(normText))) {
      if (!alias) continue;
      list.push({
        alias,
        entry,
        ascii: /^[\x00-\x7f]+$/.test(alias),
        single: alias.length === 1 && HANGUL.test(alias),
      });
    }
  }
  // 긴 별칭부터 — 같은 시작 위치에서 긴 것이 먼저 잡히게
  list.sort((a, b) => b.alias.length - a.alias.length);
  return list;
}

function okBoundary(text, start, end, m) {
  const prev = text[start - 1] ?? '';
  const next = text[end] ?? '';
  if (m.ascii) {
    const firstIsWord = ASCII_WORD.test(m.alias[0]);
    const lastIsWord = ASCII_WORD.test(m.alias[m.alias.length - 1]);
    if (firstIsWord && ASCII_WORD.test(prev)) return false;
    if (lastIsWord && ASCII_WORD.test(next)) return false;
    return true;
  }
  if (m.single) {
    if (HANGUL.test(prev)) return false;
    if (HANGUL.test(next) && !SINGLE_SUFFIX_OK.has(next)) return false;
  }
  const excludes = m.entry.exclude;
  if (excludes) {
    const around = text.slice(Math.max(0, start - 8), end + 8);
    if (excludes.some((x) => around.includes(x))) return false;
  }
  return true;
}

/**
 * 텍스트에서 겹치지 않는 매칭들을 등장 순서대로 돌려준다.
 * @returns {Array<{start:number,end:number,entry:object,alias:string,text:string}>}
 */
export function findAll(rawText, matcher) {
  const text = normText(rawText);
  if (!text) return [];
  const hits = [];
  for (const m of matcher) {
    let from = 0;
    for (;;) {
      const i = text.indexOf(m.alias, from);
      if (i < 0) break;
      const end = i + m.alias.length;
      if (okBoundary(text, i, end, m)) hits.push({ start: i, end, entry: m.entry, alias: m.alias, text: text.slice(i, end) });
      from = i + 1;
    }
  }
  hits.sort((a, b) => a.start - b.start || b.end - b.start - (a.end - a.start));
  const out = [];
  let lastEnd = -1;
  for (const h of hits) {
    if (h.start < lastEnd) continue;
    out.push(h);
    lastEnd = h.end;
  }
  return out;
}

/** 등장 순서대로, 같은 항목은 한 번만. */
export function findEntries(text, matcher) {
  const out = [];
  const seen = new Set();
  for (const h of findAll(text, matcher)) {
    if (seen.has(h.entry)) continue;
    seen.add(h.entry);
    out.push(h.entry);
  }
  return out;
}
