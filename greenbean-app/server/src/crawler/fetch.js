// HTTP 가져오기. EUC-KR 몰(오래된 영카트·위사 등)도 있어서 문자셋을 보고 디코딩한다.
// robots.txt 를 지키고, 같은 몰에는 요청 사이에 간격을 둔다.

const UA = process.env.CRAWLER_USER_AGENT || 'GreenBeanMirrorBot/1.0 (green coffee price mirror; polite crawling)';

function charsetOf(contentType, head) {
  const fromHeader = /charset=([\w-]+)/i.exec(contentType || '')?.[1];
  if (fromHeader) return fromHeader.toLowerCase();
  const fromMeta = /<meta[^>]+charset=["']?([\w-]+)/i.exec(head)?.[1];
  return (fromMeta || 'utf-8').toLowerCase();
}

export async function fetchText(url, { timeoutMs = 20000, accept = 'text/html,application/xhtml+xml,*/*;q=0.8' } = {}) {
  const res = await fetch(url, {
    headers: { 'user-agent': UA, accept, 'accept-language': 'ko-KR,ko;q=0.9,en;q=0.5' },
    redirect: 'follow',
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status} ${url}`);
  const buf = new Uint8Array(await res.arrayBuffer());
  const head = new TextDecoder('latin1').decode(buf.slice(0, 4096));
  let charset = charsetOf(res.headers.get('content-type'), head);
  if (charset === 'ks_c_5601-1987' || charset === 'cp949') charset = 'euc-kr';
  try {
    return new TextDecoder(charset).decode(buf);
  } catch {
    return new TextDecoder('utf-8').decode(buf);
  }
}

export async function fetchJson(url, opts = {}) {
  return JSON.parse(await fetchText(url, { ...opts, accept: 'application/json' }));
}

// --- robots.txt ---
const robotsCache = new Map();

export function parseRobots(txt) {
  // User-agent: * 그룹의 Disallow/Allow 만 본다
  const rules = [];
  let applies = false;
  let sawRule = false;
  for (const line of txt.split(/\r?\n/)) {
    const l = line.replace(/#.*/, '').trim();
    const m = /^([\w-]+)\s*:\s*(.*)$/.exec(l);
    if (!m) continue;
    const key = m[1].toLowerCase();
    const val = m[2].trim();
    if (key === 'user-agent') {
      if (sawRule) applies = false;
      sawRule = false;
      if (val === '*' || /greenbeanmirrorbot/i.test(val)) applies = true;
    } else if (key === 'disallow' || key === 'allow') {
      sawRule = true;
      if (applies && val) rules.push({ allow: key === 'allow', path: val });
    }
  }
  return rules;
}

export function robotsAllows(rules, pathAndQuery) {
  let best = null;
  for (const r of rules) {
    const re = new RegExp('^' + r.path.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*').replace(/\\\$$/, '$'));
    if (re.test(pathAndQuery) && (!best || r.path.length > best.path.length)) best = r;
  }
  return !best || best.allow;
}

export async function isAllowedByRobots(url, fetcher = fetchText) {
  const u = new URL(url);
  if (!robotsCache.has(u.origin)) {
    let rules = [];
    try {
      rules = parseRobots(await fetcher(`${u.origin}/robots.txt`, { timeoutMs: 8000, accept: 'text/plain' }));
    } catch {
      rules = []; // robots.txt 가 없으면 제한 없음
    }
    robotsCache.set(u.origin, rules);
  }
  return robotsAllows(robotsCache.get(u.origin), u.pathname + u.search);
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
