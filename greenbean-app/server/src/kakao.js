// 카카오톡 '나에게 보내기' 로 알림을 보낸다.
//  1) 앱에서 [카카오톡 연결] → 서버 /auth/kakao/login → 카카오 로그인(동의항목: 카카오톡 메시지 전송 talk_message)
//  2) 서버가 토큰을 받아 기기(deviceId)에 저장
//  3) 새 생두가 들어오면 서버가 그 사용자의 카카오톡 '나와의 채팅' 으로 메시지를 보낸다
// 문서: https://developers.kakao.com/docs/latest/ko/message/rest-api

const KAUTH = 'https://kauth.kakao.com';
const KAPI = 'https://kapi.kakao.com';

export class KakaoClient {
  /**
   * @param {object} cfg { restApiKey, clientSecret?, redirectUri }
   * @param {typeof fetch} [fetchImpl]
   */
  constructor(cfg, fetchImpl = fetch) {
    this.cfg = cfg;
    this.fetch = fetchImpl;
  }

  get configured() {
    return Boolean(this.cfg.restApiKey && this.cfg.redirectUri);
  }

  authorizeUrl(state) {
    const q = new URLSearchParams({
      client_id: this.cfg.restApiKey,
      redirect_uri: this.cfg.redirectUri,
      response_type: 'code',
      scope: 'talk_message',
      state,
    });
    return `${KAUTH}/oauth/authorize?${q}`;
  }

  async #token(params) {
    const body = new URLSearchParams({ client_id: this.cfg.restApiKey, ...params });
    if (this.cfg.clientSecret) body.set('client_secret', this.cfg.clientSecret);
    const res = await this.fetch(`${KAUTH}/oauth/token`, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded;charset=utf-8' },
      body,
    });
    const data = await res.json();
    if (!res.ok) throw new KakaoError(`토큰 요청 실패: ${data.error_description ?? data.error ?? res.status}`, res.status, data);
    return data;
  }

  /** 인가 코드 → 토큰 */
  async exchangeCode(code) {
    const t = await this.#token({ grant_type: 'authorization_code', redirect_uri: this.cfg.redirectUri, code });
    return toTokenRecord(t);
  }

  /** 액세스 토큰 갱신. 리프레시 토큰은 만료가 가까울 때만 새로 온다. */
  async refresh(kakao) {
    const t = await this.#token({ grant_type: 'refresh_token', refresh_token: kakao.refreshToken });
    return { ...kakao, ...toTokenRecord(t, kakao) };
  }

  async profile(accessToken) {
    const res = await this.fetch(`${KAPI}/v2/user/me`, { headers: { authorization: `Bearer ${accessToken}` } });
    const data = await res.json();
    if (!res.ok) throw new KakaoError('사용자 정보 조회 실패', res.status, data);
    return { kakaoUserId: data.id, nickname: data.kakao_account?.profile?.nickname ?? data.properties?.nickname ?? null };
  }

  async sendToMe(accessToken, templateObject) {
    const res = await this.fetch(`${KAPI}/v2/api/talk/memo/default/send`, {
      method: 'POST',
      headers: { authorization: `Bearer ${accessToken}`, 'content-type': 'application/x-www-form-urlencoded;charset=utf-8' },
      body: new URLSearchParams({ template_object: JSON.stringify(templateObject) }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.result_code !== 0) throw new KakaoError(`메시지 전송 실패: ${data.msg ?? res.status}`, res.status, data);
    return data;
  }

  /**
   * 토큰이 곧 만료되면 갱신한 뒤 보낸다. 갱신된 토큰을 돌려주니 호출한 쪽에서 저장해야 한다.
   * @returns {Promise<object>} 최신 kakao 토큰 레코드
   */
  async sendWithRefresh(kakao, templateObject, now = Date.now()) {
    let k = kakao;
    if (!k.expiresAt || new Date(k.expiresAt).getTime() - now < 60_000) k = await this.refresh(k);
    try {
      await this.sendToMe(k.accessToken, templateObject);
    } catch (e) {
      if (e.status !== 401) throw e;
      k = await this.refresh(k);
      await this.sendToMe(k.accessToken, templateObject);
    }
    return k;
  }
}

export class KakaoError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

function toTokenRecord(t, prev = {}) {
  const now = Date.now();
  return {
    accessToken: t.access_token,
    expiresAt: new Date(now + (t.expires_in ?? 21599) * 1000).toISOString(),
    refreshToken: t.refresh_token ?? prev.refreshToken,
    refreshExpiresAt: t.refresh_token_expires_in ? new Date(now + t.refresh_token_expires_in * 1000).toISOString() : prev.refreshExpiresAt ?? null,
  };
}

// ---------------- 메시지 템플릿 ----------------
const won = (n) => (n == null ? '' : `${n.toLocaleString('ko-KR')}원`);
const clip = (s, n) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

function beanLine(b) {
  const parts = [];
  if (b.origin) parts.push(`${b.origin.flag} ${b.origin.country}`);
  if (b.processes?.length) parts.push(b.processes[0]);
  if (b.price) parts.push(won(b.price) + (b.weightGrams ? `/${b.weightGrams >= 1000 ? `${b.weightGrams / 1000}kg` : `${b.weightGrams}g`}` : ''));
  const notes = (b.notes ?? []).slice(0, 3).map((n) => n.label).join(', ');
  return clip([parts.join(' · '), notes && `🎯 ${notes}`].filter(Boolean).join('\n'), 100);
}

/**
 * 새 생두 알림 템플릿.
 * 링크는 카카오 개발자 콘솔에 등록한 도메인(서버 주소)만 쓸 수 있어서, 서버의 /go/:id 로 보냈다가 쇼핑몰로 넘긴다.
 * @param {object[]} beans
 * @param {object} o { baseUrl, kind: 'new' | 'restock' }
 */
export function buildAlertTemplate(beans, { baseUrl, kind = 'new' }) {
  const label = kind === 'restock' ? '재입고' : '신규 입고';
  const go = (b) => {
    const url = `${baseUrl}/go/${encodeURIComponent(b.id)}`;
    return { web_url: url, mobile_web_url: url };
  };
  const listLink = { web_url: `${baseUrl}/`, mobile_web_url: `${baseUrl}/` };

  if (beans.length === 1) {
    const b = beans[0];
    return {
      object_type: 'feed',
      content: {
        title: clip(`[${label}] ${b.shopName} · ${b.name}`, 80),
        description: beanLine(b),
        image_url: b.imageUrl ?? undefined,
        image_width: 640,
        image_height: 640,
        link: go(b),
      },
      buttons: [{ title: '구매 페이지로 이동', link: go(b) }],
    };
  }
  return {
    object_type: 'list',
    header_title: clip(`☕ 생두 ${label} ${beans.length}건`, 40),
    header_link: listLink,
    contents: beans.slice(0, 3).map((b) => ({
      title: clip(`${b.shopName} · ${b.name}`, 60),
      description: clip(beanLine(b).replace(/\n/g, ' '), 60),
      image_url: b.imageUrl ?? undefined,
      image_width: 640,
      image_height: 640,
      link: go(b),
    })),
    buttons: [{ title: beans.length > 3 ? `외 ${beans.length - 3}건 더 보기` : '앱에서 보기', link: listLink }],
  };
}

export function buildTestTemplate(baseUrl) {
  return {
    object_type: 'text',
    text: '☕ 생두 알림 연결이 완료되었습니다.\n새 생두가 입고되면 이 채팅방으로 알려 드릴게요.',
    link: { web_url: `${baseUrl}/`, mobile_web_url: `${baseUrl}/` },
    button_title: '열기',
  };
}
