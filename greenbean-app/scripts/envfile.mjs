// server/.env 읽기/쓰기 (KEY=VALUE 형식, 주석과 순서는 유지)
import fs from 'node:fs';

export function readEnv(file) {
  const values = {};
  if (!fs.existsSync(file)) return values;
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (m) values[m[1]] = m[2].replace(/^(['"])(.*)\1$/, '$2');
  }
  return values;
}

export function writeEnv(file, updates) {
  const lines = fs.existsSync(file) ? fs.readFileSync(file, 'utf8').split(/\r?\n/) : ['# 생두 알리미 서버 설정 (scripts/setup-kakao.mjs 가 만든 파일, 직접 고쳐도 됩니다)'];
  const done = new Set();
  const out = lines.map((line) => {
    const m = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=/);
    if (!m || !(m[1] in updates)) return line;
    done.add(m[1]);
    return updates[m[1]] == null || updates[m[1]] === '' ? null : `${m[1]}=${updates[m[1]]}`;
  }).filter((l) => l !== null);
  while (out.length && out.at(-1) === '') out.pop();
  for (const [k, v] of Object.entries(updates)) if (!done.has(k) && v != null && v !== '') out.push(`${k}=${v}`);
  while (out.length && out.at(-1) === '') out.pop();
  fs.writeFileSync(file, out.join('\n') + '\n');
}
