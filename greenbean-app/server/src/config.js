import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

// server/.env 에 적어 둔 설정을 읽는다 (간편 설정 스크립트가 만드는 파일). 이미 있는 환경 변수가 우선.
try {
  process.loadEnvFile(path.join(root, '.env'));
} catch {
  /* .env 가 없으면 무시 */
}
const env = process.env;
// `node src/server.js --demo` : 샘플 데이터로 실행 (운영 데이터와 섞이지 않게 파일도 따로)
const demo = process.argv.includes('--demo') || env.DEMO_DATA === '1';
const port = Number(env.PORT ?? 8787);
const baseUrl = (env.PUBLIC_BASE_URL ?? `http://localhost:${port}`).replace(/\/$/, '');

export const config = {
  port,
  baseUrl,
  dataFile: env.DATA_FILE ?? path.join(root, 'data', demo ? 'demo.json' : 'db.json'),
  crawlIntervalMin: Number(env.CRAWL_INTERVAL_MIN ?? 60),
  crawlOnStart: env.CRAWL_ON_START !== '0',
  crawlConcurrency: Number(env.CRAWL_CONCURRENCY ?? 4),
  // 쉼표로 몰 id 를 주면 그 몰만 긁는다 (예: SHOPS=gsc,almacielo)
  shopFilter: (env.SHOPS ?? '').split(',').map((s) => s.trim()).filter(Boolean),
  adminToken: env.ADMIN_TOKEN ?? null,
  demoData: demo,
  appScheme: env.APP_SCHEME ?? 'greenbean',
  kakao: {
    restApiKey: env.KAKAO_REST_API_KEY ?? '',
    clientSecret: env.KAKAO_CLIENT_SECRET ?? '',
    redirectUri: env.KAKAO_REDIRECT_URI ?? `${baseUrl}/auth/kakao/callback`,
  },
};
