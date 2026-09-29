// 카카오톡 알림 설정: 카카오 연결, 신규/재입고, 받을 쇼핑몰·산지·키워드·kg당 가격 조건
import * as Linking from 'expo-linking';
import { useFocusEffect } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Chip } from '@/components/Chip';
import { api } from '@/lib/api';
import { useAppState } from '@/lib/app-state';
import { ago } from '@/lib/format';
import { useTheme } from '@/lib/theme';
import type { Alerts, DeviceState } from '@/lib/types';

export default function AlertsScreen() {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { deviceId, meta, keywords: myKeywords } = useAppState();
  const [state, setState] = useState<DeviceState | null>(null);
  const [alerts, setAlerts] = useState<Alerts | null>(null);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [kwInput, setKwInput] = useState('');
  const [shopQuery, setShopQuery] = useState('');

  const refresh = useCallback(async () => {
    if (!deviceId) return;
    try {
      const s = await api.device(deviceId);
      setState(s);
      setAlerts(s.alerts);
      setDirty(false);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [deviceId]);

  useFocusEffect(
    useCallback(() => {
      refresh();
    }, [refresh]),
  );

  const patch = (p: Partial<Alerts>) => {
    setAlerts((a) => (a ? { ...a, ...p } : a));
    setDirty(true);
  };
  const toggleIn = (key: 'shops' | 'origins' | 'keywords', v: string) =>
    alerts && patch({ [key]: alerts[key].includes(v) ? alerts[key].filter((x) => x !== v) : [...alerts[key], v] });

  const save = async () => {
    if (!deviceId || !alerts) return;
    setBusy(true);
    try {
      const r = await api.saveAlerts(deviceId, alerts);
      setAlerts(r.alerts);
      setDirty(false);
    } catch (e) {
      Alert.alert('저장 실패', (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const connectKakao = async () => {
    if (!deviceId) return;
    const returnUrl = Linking.createURL('alerts');
    await WebBrowser.openAuthSessionAsync(api.kakaoLoginUrl(deviceId, returnUrl), returnUrl);
    await refresh();
  };

  const test = async () => {
    if (!deviceId) return;
    try {
      await api.testAlert(deviceId);
      Alert.alert('보냈어요', '카카오톡 “나와의 채팅”을 확인해 보세요.');
    } catch (e) {
      Alert.alert('전송 실패', (e as Error).message);
    }
  };

  const disconnect = async () => {
    if (!deviceId) return;
    await api.disconnectKakao(deviceId).catch(() => {});
    refresh();
  };

  if (!alerts || !state) {
    return (
      <View style={[styles.center, { backgroundColor: t.bg }]}>
        {error ? <Text style={{ color: t.danger, textAlign: 'center' }}>서버에 연결할 수 없습니다{'\n'}{error}</Text> : <ActivityIndicator color={t.muted} />}
      </View>
    );
  }

  const shops = (meta?.shops ?? []).filter((s) => !shopQuery || s.name.includes(shopQuery));
  const allShops = alerts.shops.length === 0;
  const suggestKeywords = myKeywords.filter((k) => !alerts.keywords.includes(k));

  return (
    <View style={{ flex: 1, backgroundColor: t.bg }}>
      <ScrollView contentContainerStyle={[styles.container, { paddingTop: insets.top + 12, paddingBottom: 110 }]} keyboardShouldPersistTaps="handled">
        <Text style={[styles.title, { color: t.text }]}>🔔 입고 알림</Text>
        <Text style={[styles.lead, { color: t.muted }]}>조건에 맞는 생두가 새로 들어오면 카카오톡 “나와의 채팅”으로 알려 드려요.</Text>

        {/* 카카오톡 연결 */}
        <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
          <View style={styles.rowBetween}>
            <Text style={[styles.h2, { color: t.text }]}>💬 카카오톡</Text>
            <Text style={{ color: state.kakaoConnected ? t.accent : t.muted, fontWeight: '600' }}>
              {state.kakaoConnected ? `연결됨${state.nickname ? ` · ${state.nickname}` : ''}` : '연결 안 됨'}
            </Text>
          </View>
          {!state.kakaoConfigured ? (
            <Text style={{ color: t.muted, fontSize: 13.5 }}>서버에 카카오 앱 키(KAKAO_REST_API_KEY)가 설정되지 않았습니다. README의 “카카오톡 알림 설정”을 참고해 주세요.</Text>
          ) : state.kakaoConnected ? (
            <View style={styles.row}>
              <Pressable style={[styles.btn, { borderColor: t.border }]} onPress={test}>
                <Text style={{ color: t.text, fontWeight: '600' }}>테스트 알림</Text>
              </Pressable>
              <Pressable style={[styles.btn, { borderColor: t.border }]} onPress={disconnect}>
                <Text style={{ color: t.danger, fontWeight: '600' }}>연결 해제</Text>
              </Pressable>
            </View>
          ) : (
            <Pressable style={[styles.kakaoBtn]} onPress={connectKakao}>
              <Text style={styles.kakaoText}>카카오톡으로 알림 받기</Text>
            </Pressable>
          )}
          {state.kakaoError ? <Text style={{ color: t.danger, fontSize: 13 }}>연결이 만료되었습니다. 다시 연결해 주세요. ({state.kakaoError})</Text> : null}
          {state.lastNotifiedAt ? <Text style={{ color: t.muted, fontSize: 12.5 }}>마지막 알림: {ago(state.lastNotifiedAt)}</Text> : null}
        </View>

        {/* 무엇을 받을지 */}
        <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
          <SwitchRow label="알림 켜기" value={alerts.enabled} onChange={(v) => patch({ enabled: v })} />
          <SwitchRow label="신규 입고" hint="처음 보는 생두가 올라오면" value={alerts.newArrivals} onChange={(v) => patch({ newArrivals: v })} disabled={!alerts.enabled} />
          <SwitchRow label="재입고" hint="품절이던 생두가 다시 판매되면" value={alerts.restock} onChange={(v) => patch({ restock: v })} disabled={!alerts.enabled} />
        </View>

        {/* 쇼핑몰 선택 */}
        <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
          <View style={styles.rowBetween}>
            <Text style={[styles.h2, { color: t.text }]}>🏪 알림 받을 쇼핑몰</Text>
            <Text style={{ color: t.muted, fontSize: 13 }}>{allShops ? '전체' : `${alerts.shops.length}곳 선택`}</Text>
          </View>
          <Text style={[styles.hint, { color: t.muted }]}>선택한 쇼핑몰에 입고될 때만 알림이 와요. 아무것도 고르지 않으면 모든 쇼핑몰이 대상입니다.</Text>
          <View style={styles.row}>
            <Chip small label="전체 쇼핑몰" selected={allShops} onPress={() => patch({ shops: [] })} />
            {!allShops ? <Chip small label="선택 해제" onPress={() => patch({ shops: [] })} /> : null}
          </View>
          {(meta?.shops.length ?? 0) > 8 ? (
            <TextInput
              value={shopQuery}
              onChangeText={setShopQuery}
              placeholder="쇼핑몰 찾기"
              placeholderTextColor={t.muted}
              style={[styles.input, { borderColor: t.border, color: t.text, backgroundColor: t.bg }]}
            />
          ) : null}
          {shops.map((s) => {
            const on = alerts.shops.includes(s.id);
            const count = meta?.facets.shops.find((f) => f.id === s.id)?.count;
            return (
              <Pressable key={s.id} onPress={() => toggleIn('shops', s.id)} style={[styles.shopRow, { borderColor: t.border }]} accessibilityRole="checkbox" accessibilityState={{ checked: on }}>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: t.text, fontSize: 15, fontWeight: on ? '700' : '400' }}>{s.name}</Text>
                  <Text style={{ color: t.muted, fontSize: 12 }}>
                    {count != null ? `생두 ${count}개` : ''}
                    {s.status?.lastOkAt ? ` · ${ago(s.status.lastOkAt)} 확인` : s.status?.lastErrors?.length ? ' · 수집 오류' : ''}
                  </Text>
                </View>
                <View style={[styles.check, { borderColor: on ? t.accent : t.border, backgroundColor: on ? t.accent : 'transparent' }]}>
                  {on ? <Text style={{ color: t.accentText, fontWeight: '800' }}>✓</Text> : null}
                </View>
              </Pressable>
            );
          })}
        </View>

        {/* 산지 */}
        <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
          <Text style={[styles.h2, { color: t.text }]}>🌍 산지</Text>
          <Text style={[styles.hint, { color: t.muted }]}>고르지 않으면 모든 산지</Text>
          <View style={styles.wrap}>
            {(meta?.facets.origins ?? []).map((o) => (
              <Chip key={o.country} small label={`${o.flag} ${o.country}`} selected={alerts.origins.includes(o.country)} onPress={() => toggleIn('origins', o.country)} />
            ))}
          </View>
        </View>

        {/* 키워드 */}
        <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
          <Text style={[styles.h2, { color: t.text }]}>🏷️ 키워드</Text>
          <Text style={[styles.hint, { color: t.muted }]}>하나라도 들어 있으면 알림 (예: 게이샤, 무산소, 딸기). 비워 두면 모든 생두</Text>
          <View style={styles.wrap}>
            {alerts.keywords.map((k) => (
              <Chip key={k} small selected label={k} trailing="✕" onPress={() => toggleIn('keywords', k)} />
            ))}
          </View>
          <View style={styles.row}>
            <TextInput
              value={kwInput}
              onChangeText={setKwInput}
              onSubmitEditing={() => {
                const w = kwInput.trim();
                if (w && !alerts.keywords.includes(w)) patch({ keywords: [...alerts.keywords, w] });
                setKwInput('');
              }}
              placeholder="키워드 입력 후 완료"
              placeholderTextColor={t.muted}
              style={[styles.input, { flex: 1, borderColor: t.border, color: t.text, backgroundColor: t.bg }]}
              returnKeyType="done"
            />
          </View>
          {suggestKeywords.length ? (
            <>
              <Text style={[styles.hint, { color: t.muted }]}>내 키워드에서 추가</Text>
              <View style={styles.wrap}>
                {suggestKeywords.map((k) => (
                  <Chip key={k} small label={`+ ${k}`} onPress={() => toggleIn('keywords', k)} />
                ))}
              </View>
            </>
          ) : null}
        </View>

        {/* 가격 */}
        <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
          <Text style={[styles.h2, { color: t.text }]}>💰 1kg당 최대 가격</Text>
          <View style={[styles.row, { alignItems: 'center' }]}>
            <TextInput
              value={alerts.maxPricePerKg ? alerts.maxPricePerKg.toLocaleString('ko-KR') : ''}
              onChangeText={(s) => {
                const n = parseInt(s.replace(/[^\d]/g, ''), 10);
                patch({ maxPricePerKg: Number.isFinite(n) && n > 0 ? n : null });
              }}
              keyboardType="number-pad"
              placeholder="제한 없음"
              placeholderTextColor={t.muted}
              style={[styles.input, { flex: 1, borderColor: t.border, color: t.text, backgroundColor: t.bg }]}
            />
            <Text style={{ color: t.muted }}>원 이하</Text>
          </View>
        </View>
      </ScrollView>

      {dirty ? (
        <View style={[styles.saveBar, { paddingBottom: 12, backgroundColor: t.bg, borderColor: t.border }]}>
          <Pressable onPress={save} disabled={busy} style={[styles.saveBtn, { backgroundColor: t.accent, opacity: busy ? 0.6 : 1 }]}>
            <Text style={{ color: t.accentText, fontWeight: '700', fontSize: 16 }}>{busy ? '저장 중…' : '알림 설정 저장'}</Text>
          </Pressable>
        </View>
      ) : null}
    </View>
  );
}

function SwitchRow({ label, hint, value, onChange, disabled }: { label: string; hint?: string; value: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  const t = useTheme();
  return (
    <View style={[styles.rowBetween, { opacity: disabled ? 0.45 : 1 }]}>
      <View>
        <Text style={{ color: t.text, fontSize: 15.5, fontWeight: '500' }}>{label}</Text>
        {hint ? <Text style={{ color: t.muted, fontSize: 12.5 }}>{hint}</Text> : null}
      </View>
      <Switch value={value} onValueChange={onChange} disabled={disabled} trackColor={{ true: t.accent }} />
    </View>
  );
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  container: { padding: 16, gap: 14 },
  title: { fontSize: 24, fontWeight: '800' },
  lead: { fontSize: 14, lineHeight: 20, marginTop: -6 },
  card: { borderRadius: 14, borderWidth: StyleSheet.hairlineWidth, padding: 14, gap: 10 },
  h2: { fontSize: 16, fontWeight: '700' },
  hint: { fontSize: 12.5, lineHeight: 18 },
  row: { flexDirection: 'row', gap: 8 },
  rowBetween: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12 },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  btn: { flex: 1, borderWidth: 1, borderRadius: 10, paddingVertical: 11, alignItems: 'center' },
  kakaoBtn: { backgroundColor: '#FEE500', borderRadius: 10, paddingVertical: 13, alignItems: 'center' },
  kakaoText: { color: '#191919', fontWeight: '700', fontSize: 15 },
  input: { borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15 },
  shopRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderTopWidth: StyleSheet.hairlineWidth, gap: 12 },
  check: { width: 24, height: 24, borderRadius: 6, borderWidth: 1.5, alignItems: 'center', justifyContent: 'center' },
  saveBar: { position: 'absolute', left: 0, right: 0, bottom: 0, paddingHorizontal: 16, paddingTop: 10, borderTopWidth: StyleSheet.hairlineWidth },
  saveBtn: { borderRadius: 14, paddingVertical: 15, alignItems: 'center' },
});
