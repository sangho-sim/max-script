'use strict';
/* MaxPlayer — dependency-free mobile video player (PWA) */
const $ = s => document.querySelector(s);
const v = $('#v'), P = $('#player'), T = $('#touch');
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, x) { try { localStorage.setItem(k, JSON.stringify(x)); } catch {} }
};
const S = Object.assign({ aspect: 0, subSize: 22, loop: 0 }, store.get('mx.settings', {}));
const saveSettings = () => store.set('mx.settings', S);
const ASPECTS = [['', '맞춤'], ['fill', '채우기(크롭)'], ['stretch', '늘리기'], ['orig', '원본 크기']];
const SPEEDS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 3, 4];
const SUB_EXT = /\.(srt|vtt|smi|sami|ass|ssa)$/i;
const base = n => n.replace(/\.[^.]+$/, '').toLowerCase();

let pl = [], idx = -1, curUrl = '', locked = false, zoom = 1, bright = 1, volLvl = 1;
let cues = [], cueKey = '', subOff = 0, resumeAt = 0, sleepAt = 0, sleepTimer = 0;
let abA = null, abB = null, uiTimer = 0, raf = 0, lastTick = 0, lastSave = 0, wake = null;
let ctx = null, gain = null, seeking = false;

/* ---------- helpers ---------- */
const fmt = t => {
  if (!isFinite(t)) return '0:00';
  t = Math.max(0, Math.floor(t));
  const h = (t / 3600) | 0, m = ((t % 3600) / 60) | 0, s = t % 60;
  return (h ? h + ':' + String(m).padStart(2, '0') : m) + ':' + String(s).padStart(2, '0');
};
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));
let toastEl, toastT = 0;
function toast(msg) {
  if (!toastEl) { toastEl = document.createElement('div'); toastEl.id = 'toast'; document.body.append(toastEl); }
  toastEl.textContent = msg; toastEl.hidden = false;
  clearTimeout(toastT); toastT = setTimeout(() => toastEl.hidden = true, 2500);
}
const hudEl = $('#hud'); let hudT = 0;
function hud(msg, ms = 700) {
  hudEl.textContent = msg; hudEl.classList.add('on');
  clearTimeout(hudT); if (ms) hudT = setTimeout(() => hudEl.classList.remove('on'), ms);
}
const hudOff = () => hudEl.classList.remove('on');

/* ---------- history (resume) ---------- */
const hkey = f => f.name + '|' + f.size;
const hist = () => store.get('mx.hist', {});
function saveProg() {
  if (idx < 0 || !isFinite(v.duration) || !v.duration) return;
  const h = hist(), f = pl[idx].file;
  h[hkey(f)] = { n: f.name, t: v.currentTime, d: v.duration, ts: Date.now() };
  const keys = Object.keys(h);
  if (keys.length > 50) keys.sort((a, b) => h[a].ts - h[b].ts).slice(0, keys.length - 50).forEach(k => delete h[k]);
  store.set('mx.hist', h);
}
function renderHome() {
  const h = hist(), list = Object.values(h).sort((a, b) => b.ts - a.ts);
  $('#recent').hidden = !list.length;
  $('#rlist').replaceChildren(...list.map(e => {
    const li = document.createElement('li'), r = e.d ? clamp(e.t / e.d, 0, 1) : 0;
    li.innerHTML = '<div class="n"></div><div class="m"><span></span><span></span></div><div class="p"><i></i></div>';
    li.querySelector('.n').textContent = e.n;
    const sp = li.querySelectorAll('.m span');
    sp[0].textContent = fmt(e.t) + ' / ' + fmt(e.d); sp[1].textContent = Math.round(r * 100) + '%';
    li.querySelector('i').style.width = r * 100 + '%';
    return li;
  }));
}
$('#rlist').onclick = () => { toast('같은 파일을 선택하면 이어서 재생됩니다'); $('#fv').click(); };
$('#clear').onclick = () => { store.set('mx.hist', {}); renderHome(); };

/* ---------- opening files ---------- */
$('#open').onclick = () => $('#fv').click();
$('#fv').onchange = e => { openFiles([...e.target.files]); e.target.value = ''; };
addEventListener('dragover', e => e.preventDefault());
addEventListener('drop', e => { e.preventDefault(); openFiles([...e.dataTransfer.files]); });

function openFiles(files) {
  const subs = files.filter(f => SUB_EXT.test(f.name));
  const media = files.filter(f => !SUB_EXT.test(f.name) && (/^(video|audio)\//.test(f.type) || /\.(mkv|avi|ts|mov|flv|wmv|m4v|mp4|webm|3gp|mp3|m4a|flac|ogg|wav|opus)$/i.test(f.name)));
  if (!media.length) { toast('재생할 수 있는 파일이 없습니다'); return; }
  media.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }));
  pl = media.map(f => ({ file: f, sub: subs.find(s => base(s.name) === base(f.name)) || (subs.length === 1 && media.length === 1 ? subs[0] : null) }));
  load(0);
}

function load(i) {
  if (i < 0 || i >= pl.length) return;
  saveProg();
  idx = i;
  const it = pl[i], f = it.file;
  if (curUrl) URL.revokeObjectURL(curUrl);
  curUrl = URL.createObjectURL(f);
  abA = abB = null; paintAB();
  v.src = curUrl;
  v.loop = S.loop === 1;
  $('#title').textContent = f.name;
  P.classList.toggle('audio', f.type.startsWith('audio/') || /\.(mp3|m4a|flac|ogg|wav|opus)$/i.test(f.name));
  const h = hist()[hkey(f)];
  resumeAt = h && h.t > 5 && h.d && h.t < h.d - 10 ? h.t : 0;
  setSubFile(it.sub);
  $('#home').hidden = true; P.hidden = false;
  applyAspect(); applyZoom();
  $('#bPrev').disabled = i === 0; $('#bNext').disabled = i === pl.length - 1;
  $('#bPrev').style.opacity = i === 0 ? .35 : 1; $('#bNext').style.opacity = i === pl.length - 1 ? .35 : 1;
  v.play().catch(() => {});
  showUI();
  if ('mediaSession' in navigator) navigator.mediaSession.metadata = new MediaMetadata({ title: f.name, artist: 'MaxPlayer' });
}
function closePlayer() {
  saveProg(); v.pause(); v.removeAttribute('src'); v.load();
  if (curUrl) URL.revokeObjectURL(curUrl); curUrl = '';
  idx = -1; pl = []; cues = []; $('#subs').textContent = '';
  P.hidden = true; $('#home').hidden = false;
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
  try { screen.orientation.unlock(); } catch {}
  renderHome();
}

/* ---------- video events ---------- */
v.addEventListener('loadedmetadata', () => {
  if (resumeAt) { v.currentTime = resumeAt; hud('이어보기 ' + fmt(resumeAt), 1200); resumeAt = 0; }
  $('#tDur').textContent = fmt(v.duration); tick(true);
  $('#bPip').hidden = !document.pictureInPictureEnabled || !v.videoWidth;
  $('#bPip').style.display = $('#bPip').hidden ? 'none' : '';
});
v.addEventListener('play', () => { setPlayIcon(); startLoop(); lockWake(); armHide(); });
v.addEventListener('pause', () => { setPlayIcon(); tick(true); saveProg(); unlockWake(); showUI(); });
v.addEventListener('seeked', () => tick(true));
v.addEventListener('ended', () => {
  if (S.loop === 1) return;
  if (idx < pl.length - 1) load(idx + 1);
  else if (S.loop === 2) load(0);
  else showUI(true);
});
v.addEventListener('error', () => {
  toast('재생할 수 없는 형식입니다 (브라우저가 코덱을 지원하지 않음)');
});
function setPlayIcon() { $('#bPlay use').setAttribute('href', v.paused ? '#i-play' : '#i-pause'); }
const togglePlay = () => v.paused ? v.play().catch(() => {}) : v.pause();
$('#bPlay').onclick = () => { togglePlay(); armHide(); };
$('#bPrev').onclick = () => load(idx - 1);
$('#bNext').onclick = () => load(idx + 1);
$('#bBack').onclick = closePlayer;
const skip = d => { if (!isFinite(v.duration)) return; v.currentTime = clamp(v.currentTime + d, 0, v.duration); };

/* ---------- render loop (≈10Hz, only while playing) ---------- */
function startLoop() { if (!raf) raf = requestAnimationFrame(loop); }
function loop(ts) {
  if (v.paused || P.hidden) { raf = 0; return; }
  raf = requestAnimationFrame(loop);
  if (ts - lastTick < 100) return;
  lastTick = ts; tick();
}
let lastSec = -1;
function tick(force) {
  const t = v.currentTime, d = v.duration;
  if (!seeking && (P.classList.contains('ui') || force)) {
    $('#bar').style.setProperty('--p', d ? t / d : 0);
    const s = Math.floor(t);
    if (s !== lastSec) { lastSec = s; $('#tCur').textContent = fmt(t); }
  }
  paintSub(t);
  if (abB !== null && abA !== null && t >= abB) v.currentTime = abA;
  const now = Date.now();
  if (now - lastSave > 5000) { lastSave = now; saveProg(); }
}

/* ---------- UI show/hide ---------- */
function showUI(sticky) {
  if (locked) return;
  P.classList.add('ui'); tick(true);
  clearTimeout(uiTimer);
  if (!sticky) armHide();
}
function armHide() {
  clearTimeout(uiTimer);
  if (!v.paused && P.classList.contains('ui')) uiTimer = setTimeout(() => P.classList.remove('ui'), 3500);
}
const toggleUI = () => P.classList.contains('ui') ? (clearTimeout(uiTimer), P.classList.remove('ui')) : showUI();

/* ---------- seek bar ---------- */
const bar = $('#bar');
let seekT = 0;
function barSeek(e, commit) {
  const r = bar.getBoundingClientRect(), p = clamp((e.clientX - r.left) / r.width, 0, 1);
  bar.style.setProperty('--p', p);
  const t = p * (v.duration || 0);
  $('#tCur').textContent = fmt(t);
  hud(fmt(t) + ' / ' + fmt(v.duration), 0);
  const now = performance.now();
  if (commit || now - seekT > 120) { seekT = now; v.currentTime = t; }
}
bar.addEventListener('pointerdown', e => { seeking = true; bar.setPointerCapture(e.pointerId); clearTimeout(uiTimer); barSeek(e); });
bar.addEventListener('pointermove', e => { if (seeking) barSeek(e); });
const endSeek = e => { if (!seeking) return; barSeek(e, true); seeking = false; hudOff(); armHide(); };
bar.addEventListener('pointerup', endSeek);
bar.addEventListener('pointercancel', () => { seeking = false; hudOff(); });

/* ---------- aspect / zoom ---------- */
function applyAspect() { v.className = ASPECTS[S.aspect][0]; }
function applyZoom() { v.style.transform = zoom === 1 ? '' : `scale(${zoom})`; }
$('#bAspect').onclick = () => { S.aspect = (S.aspect + 1) % ASPECTS.length; zoom = 1; applyZoom(); applyAspect(); saveSettings(); hud(ASPECTS[S.aspect][1]); armHide(); };

/* ---------- brightness / volume ---------- */
function setBright(b) {
  bright = clamp(b, 0, 2);
  $('#dim').style.opacity = bright < 1 ? (1 - bright) * .9 : 0;
  v.style.filter = bright > 1 ? `brightness(${bright})` : '';
  hud('☀ ' + Math.round(bright * 100) + '%', 0);
}
function setVol(l) {
  volLvl = clamp(l, 0, 2);
  if (volLvl > 1 && !ctx) {
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      gain = ctx.createGain();
      ctx.createMediaElementSource(v).connect(gain).connect(ctx.destination);
    } catch { volLvl = 1; }
  }
  if (ctx && ctx.state === 'suspended') ctx.resume();
  v.volume = Math.min(volLvl, 1);
  if (gain) gain.gain.value = Math.max(volLvl, 1);
  hud((volLvl === 0 ? '🔇 ' : '🔊 ') + Math.round(volLvl * 100) + '%', 0);
}

/* ---------- touch gestures ---------- */
let g = null, pinch = null, lastTap = 0, lastTapX = 0, tapTimer = 0, pressT = 0, prevRate = 1, skipAcc = 0, skipT = 0;
T.addEventListener('touchstart', e => {
  if (locked) return;
  if (e.touches.length === 2) {
    clearTimeout(pressT); endPress(); g = null;
    pinch = { d: dist(e.touches), z: zoom };
    return;
  }
  const t = e.touches[0], W = innerWidth;
  if (t.clientX < 20 || t.clientX > W - 20) { g = null; return; } // leave system-edge gestures alone
  g = { x: t.clientX, y: t.clientY, mode: null, t0: v.currentTime, br: bright, vo: volLvl, target: 0 };
  clearTimeout(pressT);
  pressT = setTimeout(() => {
    if (g && !g.mode && !v.paused) { g.mode = 'press'; prevRate = v.playbackRate; v.playbackRate = 2; hud('▶▶ 2x 배속', 0); }
  }, 450);
}, { passive: true });

T.addEventListener('touchmove', e => {
  if (locked) return;
  if (pinch && e.touches.length === 2) {
    zoom = clamp(pinch.z * dist(e.touches) / pinch.d, .5, 4);
    applyZoom(); hud(Math.round(zoom * 100) + '%', 0);
    return;
  }
  if (!g || e.touches.length !== 1) return;
  const t = e.touches[0], dx = t.clientX - g.x, dy = t.clientY - g.y, W = innerWidth, H = innerHeight;
  if (!g.mode) {
    if (Math.abs(dx) < 14 && Math.abs(dy) < 14) return;
    clearTimeout(pressT); clearTimeout(tapTimer); lastTap = 0;
    g.mode = Math.abs(dx) > Math.abs(dy) ? 'seek' : (g.x < W / 2 ? 'bright' : 'vol');
    if (g.mode === 'seek' && !isFinite(v.duration)) g.mode = 'none';
    g.x0 = t.clientX; g.y0 = t.clientY;
  }
  if (g.mode === 'seek') {
    const span = Math.min(v.duration, 240);
    g.target = clamp(g.t0 + (t.clientX - g.x) / W * span, 0, v.duration);
    const d = g.target - g.t0;
    hud((d >= 0 ? '+' : '−') + fmt(Math.abs(d)) + '\n' + fmt(g.target) + ' / ' + fmt(v.duration), 0);
  } else if (g.mode === 'bright') setBright(g.br - (t.clientY - g.y) / (H * .7));
  else if (g.mode === 'vol') setVol(g.vo - (t.clientY - g.y) / (H * .7));
  e.preventDefault();
}, { passive: false });

function endPress() { if (g && g.mode === 'press') { v.playbackRate = prevRate; hudOff(); } }
T.addEventListener('touchend', e => {
  if (locked) { showUnlock(); return; }
  if (pinch) {
    if (e.touches.length < 2) { if (zoom > .9 && zoom < 1.1) { zoom = 1; applyZoom(); } pinch = null; hudOff(); }
    return;
  }
  if (!g) return;
  clearTimeout(pressT);
  const m = g.mode;
  if (m === 'press') endPress();
  else if (m === 'seek') { v.currentTime = g.target; hudOff(); }
  else if (m === 'bright' || m === 'vol' || m === 'none') hudOff();
  else if (!m) {
    const now = performance.now();
    if (now - lastTap < 300 && Math.abs(g.x - lastTapX) < 70) {
      clearTimeout(tapTimer); lastTap = 0; dbl(g.x);
    } else {
      lastTap = now; lastTapX = g.x; tapTimer = setTimeout(toggleUI, 260);
    }
  }
  g = null;
}, { passive: true });
T.addEventListener('touchcancel', () => { endPress(); hudOff(); g = null; pinch = null; });
const dist = t => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY);

function dbl(x) {
  const r = x / innerWidth;
  if (r < .4 || r > .6) {
    const d = r < .5 ? -10 : 10;
    skipAcc = (skipAcc && Math.sign(skipAcc) === Math.sign(d)) ? skipAcc + d : d;
    skip(d); hud((skipAcc > 0 ? '⏩ +' : '⏪ −') + Math.abs(skipAcc) + '초', 600);
    clearTimeout(skipT); skipT = setTimeout(() => skipAcc = 0, 700);
  } else { togglePlay(); }
}
// desktop mouse fallback
T.addEventListener('click', e => { if (e.pointerType === 'mouse' || e.detail) { if (!('ontouchstart' in window)) toggleUI(); } });
T.addEventListener('dblclick', e => { if (!('ontouchstart' in window)) dbl(e.clientX); });

/* ---------- lock ---------- */
let unlockT = 0;
function showUnlock() { $('#unlock').classList.remove('off'); clearTimeout(unlockT); unlockT = setTimeout(() => $('#unlock').classList.add('off'), 2000); }
$('#bLock').onclick = () => { locked = true; P.classList.remove('ui'); $('#unlock').hidden = false; showUnlock(); hud('화면 잠김', 900); };
$('#unlock').onclick = () => { locked = false; $('#unlock').hidden = true; showUI(); };

/* ---------- fullscreen / rotate / pip ---------- */
$('#bRot').onclick = async () => {
  try {
    if (!document.fullscreenElement) {
      await P.requestFullscreen({ navigationUI: 'hide' });
      if (v.videoWidth >= v.videoHeight) await screen.orientation.lock('landscape').catch(() => {});
    } else {
      const o = screen.orientation && screen.orientation.type;
      if (o && o.startsWith('landscape')) await screen.orientation.lock('portrait').catch(() => {});
      else await screen.orientation.lock('landscape').catch(() => {});
    }
  } catch { toast('이 기기에서는 지원하지 않습니다'); }
  armHide();
};
$('#bPip').onclick = async () => {
  try { document.pictureInPictureElement ? await document.exitPictureInPicture() : await v.requestPictureInPicture(); } catch { toast('PIP를 사용할 수 없습니다'); }
};

/* ---------- sheet menus ---------- */
const sheetEl = $('#sheet'), scrim = $('#scrim');
function sheet(title, items) {
  sheetEl.replaceChildren();
  const h = document.createElement('h3'); h.textContent = title; sheetEl.append(h);
  for (const it of items) {
    const b = document.createElement('button');
    b.className = it.on ? 'on' : '';
    const a = document.createElement('span'); a.textContent = it.t; b.append(a);
    if (it.s) { const s = document.createElement('small'); s.textContent = it.s; b.append(s); }
    b.onclick = () => { if (!it.keep) closeSheet(); it.f && it.f(); };
    sheetEl.append(b);
  }
  sheetEl.hidden = scrim.hidden = false; clearTimeout(uiTimer);
}
function closeSheet() { sheetEl.hidden = scrim.hidden = true; armHide(); }
scrim.onclick = closeSheet;

const speedMenu = () => sheet('재생 속도', SPEEDS.map(s => ({ t: s + 'x', on: v.playbackRate === s, f: () => setSpeed(s) })));
function setSpeed(s) { v.playbackRate = s; $('#bSpeed').textContent = s + 'x'; hud(s + 'x 배속'); }
$('#bSpeed').onclick = speedMenu;

function subMenu() {
  sheet('자막' + (cues.length ? ` · 싱크 ${subOff >= 0 ? '+' : ''}${subOff.toFixed(1)}s · 크기 ${S.subSize}` : ''), [
    { t: '자막 끄기', on: !cues.length, f: () => setCues([], '') },
    { t: '자막 파일 불러오기', s: 'srt · smi · vtt · ass', f: () => $('#fs').click() },
    { t: '싱크 −0.5초 (자막 늦추기)', keep: 1, f: () => { subOff -= .5; subMenu(); } },
    { t: '싱크 +0.5초 (자막 당기기)', keep: 1, f: () => { subOff += .5; subMenu(); } },
    { t: '글자 크게', keep: 1, f: () => { S.subSize = Math.min(48, S.subSize + 2); applySubSize(); subMenu(); } },
    { t: '글자 작게', keep: 1, f: () => { S.subSize = Math.max(12, S.subSize - 2); applySubSize(); subMenu(); } }
  ]);
}
$('#bCC').onclick = subMenu;

function audioMenu() {
  const at = v.audioTracks;
  if (!at || at.length < 2) { toast('선택 가능한 오디오 트랙이 없습니다'); return; }
  sheet('오디오 트랙', [...at].map((t, i) => ({ t: t.label || t.language || '트랙 ' + (i + 1), on: t.enabled, f: () => { [...at].forEach((x, j) => x.enabled = j === i); } })));
}
function loopMenu() {
  const L = ['반복 없음', '한 곡/영상 반복', '전체 반복'];
  sheet('반복', L.map((t, i) => ({ t, on: S.loop === i, f: () => { S.loop = i; v.loop = i === 1; saveSettings(); } })));
}
function sleepMenu() {
  const opts = [0, 10, 20, 30, 60, 90];
  sheet('취침 타이머' + (sleepAt ? ` · ${Math.ceil((sleepAt - Date.now()) / 60000)}분 남음` : ''), opts.map(m => ({
    t: m ? m + '분 후 정지' : '끄기', on: !m && !sleepAt,
    f: () => { clearTimeout(sleepTimer); sleepAt = 0; if (m) { sleepAt = Date.now() + m * 60000; sleepTimer = setTimeout(() => { v.pause(); sleepAt = 0; toast('취침 타이머: 재생 정지'); }, m * 60000); toast(m + '분 후 정지'); } }
  })));
}
function abMenu() {
  if (abA === null) { abA = v.currentTime; hud('구간 반복: A 지점 ' + fmt(abA)); }
  else if (abB === null) { if (v.currentTime <= abA) return toast('B 지점은 A 이후여야 합니다'); abB = v.currentTime; hud('구간 반복 ' + fmt(abA) + ' ~ ' + fmt(abB)); }
  else { abA = abB = null; hud('구간 반복 해제'); }
  paintAB();
}
function paintAB() {
  const el = $('#ab'), d = v.duration;
  if (abA === null || !d) { el.hidden = true; return; }
  el.hidden = false; el.style.left = abA / d * 100 + '%';
  el.style.width = ((abB ?? abA) - abA) / d * 100 + '%'; if (abB === null) el.style.width = '2px';
}
function infoMenu() {
  const f = pl[idx].file;
  sheet('정보', [
    { t: f.name, keep: 1 },
    { t: '크기', s: (f.size / 1048576).toFixed(1) + ' MB', keep: 1 },
    { t: '해상도', s: v.videoWidth ? v.videoWidth + '×' + v.videoHeight : '-', keep: 1 },
    { t: '길이', s: fmt(v.duration), keep: 1 }
  ]);
}
$('#bMore').onclick = () => sheet('더보기', [
  { t: '오디오 트랙', f: audioMenu },
  { t: '구간 반복 (A-B)', s: abA === null ? 'A 지정' : abB === null ? 'B 지정' : '해제', f: abMenu },
  { t: '반복 모드', s: ['끔', '한 개', '전체'][S.loop], f: loopMenu },
  { t: '취침 타이머', s: sleepAt ? '켜짐' : '', f: sleepMenu },
  { t: '현재 화면 캡처', f: capture },
  { t: '파일 정보', f: infoMenu }
]);
function capture() {
  if (!v.videoWidth) return;
  const c = document.createElement('canvas'); c.width = v.videoWidth; c.height = v.videoHeight;
  c.getContext('2d').drawImage(v, 0, 0);
  c.toBlob(b => {
    const a = document.createElement('a'); a.href = URL.createObjectURL(b);
    a.download = base(pl[idx].file.name) + '_' + Math.floor(v.currentTime) + 's.png'; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  });
}

/* ---------- subtitles ---------- */
const subsEl = $('#subs');
function applySubSize() { document.documentElement.style.setProperty('--sub', S.subSize + 'px'); saveSettings(); }
applySubSize();
$('#fs').onchange = e => { const f = e.target.files[0]; e.target.value = ''; if (f) setSubFile(f, true); };
async function setSubFile(f, announce) {
  if (!f) { setCues([], ''); return; }
  try {
    const m = f.name.match(/\.(\w+)$/), c = parseSubs(await readText(f), (m ? m[1] : 'srt').toLowerCase());
    setCues(c, f.name);
    if (announce) toast(c.length ? '자막 ' + c.length + '줄 불러옴' : '자막을 읽지 못했습니다');
  } catch { toast('자막을 읽지 못했습니다'); }
}
function setCues(c, name) { cues = c; subOff = 0; cueKey = ''; subsEl.textContent = ''; }
async function readText(f) {
  const b = await f.arrayBuffer();
  try { return new TextDecoder('utf-8', { fatal: true }).decode(b); }
  catch { try { return new TextDecoder('euc-kr').decode(b); } catch { return new TextDecoder().decode(b); } }
}
const tm = (h, m, s, ms) => (+h || 0) * 3600 + +m * 60 + +s + parseFloat('0.' + (ms || '0'));
const clean = s => s.replace(/\{[^}]*\}/g, '').replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '').replace(/&nbsp;/gi, ' ').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/\\N/g, '\n').trim();
function parseSubs(txt, ext) {
  txt = txt.replace(/^﻿/, '').replace(/\r/g, '');
  const out = [];
  if (ext === 'smi' || ext === 'sami') {
    const re = /<sync\s+start\s*=\s*"?(\d+)"?[^>]*>([\s\S]*?)(?=<sync|<\/body|$)/gi; let m, prev = null;
    while ((m = re.exec(txt))) {
      const s = +m[1] / 1000;
      if (prev) prev.e = s;
      const body = m[2].replace(/<\/?p[^>]*>/gi, ''), t = clean(body);
      prev = t ? { s, e: s + 5, t } : null;
      if (prev) out.push(prev);
    }
  } else if (ext === 'ass' || ext === 'ssa') {
    const T2 = x => { const q = x.trim().match(/(\d+):(\d+):(\d+)[.](\d+)/); return q ? tm(q[1], q[2], q[3], q[4]) : 0; };
    for (const ln of txt.split('\n')) {
      if (!ln.startsWith('Dialogue:')) continue;
      const p = ln.slice(9).split(','); if (p.length < 10) continue;
      const t = clean(p.slice(9).join(','));
      if (t) out.push({ s: T2(p[1]), e: T2(p[2]), t });
    }
  } else {
    const re = /(?:(\d+):)?(\d+):(\d+)[.,](\d+)\s*-->\s*(?:(\d+):)?(\d+):(\d+)[.,](\d+)[^\n]*\n([\s\S]*?)(?=\n\s*\n|$)/g; let m;
    while ((m = re.exec(txt))) {
      const t = clean(m[9]);
      if (t) out.push({ s: tm(m[1], m[2], m[3], m[4]), e: tm(m[5], m[6], m[7], m[8]), t });
    }
  }
  return out.sort((a, b) => a.s - b.s);
}
function paintSub(t) {
  if (!cues.length) return;
  t -= subOff;
  let lo = 0, hi = cues.length - 1, k = -1;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (cues[m].s <= t) { k = m; lo = m + 1; } else hi = m - 1; }
  let txt = '', key = '';
  for (let i = k, n = 0; i >= 0 && n < 4; i--, n++) if (cues[i].e > t) { txt = cues[i].t + (txt ? '\n' + txt : ''); key += i + ','; }
  if (key !== cueKey) { cueKey = key; subsEl.textContent = txt; }
}

/* ---------- wake lock / media session / lifecycle ---------- */
async function lockWake() { try { if (!wake && navigator.wakeLock) { wake = await navigator.wakeLock.request('screen'); wake.onrelease = () => wake = null; } } catch {} }
function unlockWake() { try { wake && wake.release(); } catch {} wake = null; }
document.addEventListener('visibilitychange', () => {
  if (document.hidden) saveProg(); else if (!v.paused) lockWake();
});
addEventListener('pagehide', saveProg);
if ('mediaSession' in navigator) {
  const ms = navigator.mediaSession;
  const set = (a, f) => { try { ms.setActionHandler(a, f); } catch {} };
  set('play', () => v.play()); set('pause', () => v.pause());
  set('previoustrack', () => load(idx - 1)); set('nexttrack', () => load(idx + 1));
  set('seekbackward', () => skip(-10)); set('seekforward', () => skip(10));
  set('seekto', d => { v.currentTime = d.seekTime; });
}

/* ---------- keyboard (desktop) ---------- */
addEventListener('keydown', e => {
  if (P.hidden || e.target.tagName === 'INPUT') return;
  const k = e.key;
  if (k === ' ' || k === 'k') { togglePlay(); e.preventDefault(); }
  else if (k === 'ArrowLeft') skip(-5); else if (k === 'ArrowRight') skip(5);
  else if (k === 'ArrowUp') setVol(volLvl + .05); else if (k === 'ArrowDown') setVol(volLvl - .05);
  else if (k === 'f') $('#bRot').click(); else if (k === 'm') { v.muted = !v.muted; hud(v.muted ? '음소거' : '음소거 해제'); }
  else if (k === 'Escape' && !document.fullscreenElement) closePlayer();
  if (k.startsWith('Arrow')) { hudT = 0; setTimeout(hudOff, 600); }
});

/* ---------- Android back button ---------- */
history.replaceState({ h: 1 }, '');
new MutationObserver(() => {
  if (!P.hidden && !history.state?.p) history.pushState({ p: 1 }, '');
}).observe(P, { attributes: true, attributeFilter: ['hidden'] });
addEventListener('popstate', () => {
  if (!sheetEl.hidden) { closeSheet(); history.pushState({ p: 1 }, ''); }
  else if (!P.hidden) closePlayer();
});

/* ---------- boot ---------- */
renderHome();
if ('serviceWorker' in navigator && location.protocol.startsWith('http')) navigator.serviceWorker.register('sw.js').catch(() => {});
