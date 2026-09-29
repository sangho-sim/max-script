import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pickLanIp } from './launch.mjs';
import { readEnv, writeEnv } from './envfile.mjs';

const v4 = (address, internal = false) => ({ family: 'IPv4', address, internal });

test('내부 IP: 가상 어댑터(WSL·도커)보다 와이파이를 고름', () => {
  assert.equal(
    pickLanIp({
      'vEthernet (WSL)': [v4('172.20.64.1')],
      'Loopback Pseudo-Interface 1': [v4('127.0.0.1', true)],
      'Wi-Fi': [v4('192.168.0.23'), { family: 'IPv6', address: 'fe80::1', internal: false }],
      docker0: [v4('172.17.0.1')],
    }),
    '192.168.0.23',
  );
  assert.equal(pickLanIp({ en0: [v4('10.0.0.5')], utun3: [v4('100.64.0.2')] }), '10.0.0.5');
  assert.equal(pickLanIp({ lo: [v4('127.0.0.1', true)] }), null);
  assert.equal(pickLanIp({ 이더넷: [v4('169.254.10.1')], 'Wi-Fi 2': [v4('192.168.35.7')] }), '192.168.35.7');
});

test('.env: 있는 값은 바꾸고, 빈 값은 지우고, 주석과 다른 줄은 유지', () => {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'gb-')), '.env');
  fs.writeFileSync(file, '# 메모\nPORT=8788\nKAKAO_REST_API_KEY=old\nKAKAO_CLIENT_SECRET="s"\n');
  writeEnv(file, { KAKAO_REST_API_KEY: 'new', KAKAO_CLIENT_SECRET: '', PUBLIC_BASE_URL: 'http://192.168.0.2:8788' });
  assert.equal(fs.readFileSync(file, 'utf8'), '# 메모\nPORT=8788\nKAKAO_REST_API_KEY=new\nPUBLIC_BASE_URL=http://192.168.0.2:8788\n');
  assert.deepEqual(readEnv(file), { PORT: '8788', KAKAO_REST_API_KEY: 'new', PUBLIC_BASE_URL: 'http://192.168.0.2:8788' });
  // 서버도 같은 파일을 읽을 수 있어야 함
  const loaded = {};
  const before = { ...process.env };
  process.loadEnvFile(file);
  for (const k of ['PORT', 'KAKAO_REST_API_KEY']) loaded[k] = process.env[k];
  for (const k of Object.keys(process.env)) if (!(k in before)) delete process.env[k];
  assert.deepEqual(loaded, { PORT: '8788', KAKAO_REST_API_KEY: 'new' });
});
