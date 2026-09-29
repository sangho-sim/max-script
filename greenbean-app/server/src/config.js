import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const env = process.env;
const port = Number(env.PORT ?? 8787);
const baseUrl = (env.PUBLIC_BASE_URL ?? `http://localhost:${port}`).replace(/\/$/, '');

export const config = {
  port,
  baseUrl,
  dataFile: env.DATA_FILE ?? path.join(root, 'data', 'db.json'),
  crawlIntervalMin: Number(env.CRAWL_INTERVAL_MIN ?? 60),
  crawlOnStart: env.CRAWL_ON_START !== '0',
  crawlConcurrency: Number(env.CRAWL_CONCURRENCY ?? 4),
  // 쉼표로 몰 id 를 주면 그 몰만 긁는다 (예: SHOPS=gsc,almacielo)
  shopFilter: (env.SHOPS ?? '').split(',').map((s) => s.trim()).filter(Boolean),
  adminToken: env.ADMIN_TOKEN ?? null,
  demoData: env.DEMO_DATA === '1',
  appScheme: env.APP_SCHEME ?? 'greenbean',
  kakao: {
    restApiKey: env.KAKAO_REST_API_KEY ?? '',
    clientSecret: env.KAKAO_CLIENT_SECRET ?? '',
    redirectUri: env.KAKAO_REDIRECT_URI ?? `${baseUrl}/auth/kakao/callback`,
  },
};
