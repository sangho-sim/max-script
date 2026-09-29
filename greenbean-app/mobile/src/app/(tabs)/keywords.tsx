// 키워드 설정: 목록 화면 상단에 보일 '내 키워드' 칩을 고른다.
// 추천 키워드는 국내 생두몰들의 카테고리 분류(가공방식·등급·품종·특징·인증·용도·유명 산지)를 참고해 묶었다.
import { useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Chip } from '@/components/Chip';
import { DEFAULT_KEYWORDS, useAppState } from '@/lib/app-state';
import { useTheme } from '@/lib/theme';

export default function KeywordsScreen() {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { keywords, setKeywords, toggleKeyword, meta } = useAppState();
  const [input, setInput] = useState('');

  const add = () => {
    const words = input.split(',').map((s) => s.trim()).filter(Boolean);
    if (words.length) setKeywords([...keywords, ...words.filter((w) => !keywords.includes(w))]);
    setInput('');
  };

  const popularNotes = meta?.facets.notes.slice(0, 24) ?? [];
  const popularVarieties = meta?.facets.varieties.slice(0, 16) ?? [];

  return (
    <ScrollView style={{ backgroundColor: t.bg }} contentContainerStyle={[styles.container, { paddingTop: insets.top + 12 }]} keyboardShouldPersistTaps="handled">
      <Text style={[styles.title, { color: t.text }]}>🏷️ 검색 키워드</Text>
      <Text style={[styles.lead, { color: t.muted }]}>고른 키워드는 생두 목록 위에 칩으로 나타나고, 눌러서 바로 걸러 볼 수 있어요.</Text>

      <View style={[styles.card, { backgroundColor: t.card, borderColor: t.border }]}>
        <Text style={[styles.h2, { color: t.text }]}>내 키워드 {keywords.length}</Text>
        <View style={styles.wrap}>
          {keywords.map((k) => (
            <Chip key={k} small selected label={`#${k}`} trailing="✕" onPress={() => toggleKeyword(k)} />
          ))}
          {!keywords.length ? <Text style={{ color: t.muted }}>아래에서 골라 보세요</Text> : null}
        </View>
        <View style={styles.inputRow}>
          <TextInput
            value={input}
            onChangeText={setInput}
            onSubmitEditing={add}
            placeholder="직접 입력 (예: 코케, 시드라)"
            placeholderTextColor={t.muted}
            style={[styles.input, { borderColor: t.border, color: t.text, backgroundColor: t.bg }]}
            returnKeyType="done"
          />
          <Pressable onPress={add} style={[styles.addBtn, { backgroundColor: t.accent }]}>
            <Text style={{ color: t.accentText, fontWeight: '700' }}>추가</Text>
          </Pressable>
        </View>
        <Pressable onPress={() => setKeywords(DEFAULT_KEYWORDS)}>
          <Text style={{ color: t.muted, fontSize: 13 }}>기본값으로 되돌리기</Text>
        </Pressable>
      </View>

      {(meta?.keywordPresets ?? []).map((g) => (
        <View key={g.group} style={styles.group}>
          <Text style={[styles.h3, { color: t.text }]}>{g.group}</Text>
          <View style={styles.wrap}>
            {g.keywords.map((k) => (
              <Chip key={k} small label={k} selected={keywords.includes(k)} onPress={() => toggleKeyword(k)} />
            ))}
          </View>
        </View>
      ))}

      {popularVarieties.length ? (
        <View style={styles.group}>
          <Text style={[styles.h3, { color: t.text }]}>지금 판매 중인 품종</Text>
          <View style={styles.wrap}>
            {popularVarieties.map((v) => (
              <Chip key={v.name} small label={v.name} count={v.count} selected={keywords.includes(v.name)} onPress={() => toggleKeyword(v.name)} />
            ))}
          </View>
        </View>
      ) : null}

      {popularNotes.length ? (
        <View style={styles.group}>
          <Text style={[styles.h3, { color: t.text }]}>많이 쓰인 컵노트</Text>
          <View style={styles.wrap}>
            {popularNotes.map((n) => (
              <Chip key={n.label} small label={n.label} count={n.count} selected={keywords.includes(n.label)} onPress={() => toggleKeyword(n.label)} />
            ))}
          </View>
        </View>
      ) : null}
      {!meta ? <Text style={{ color: t.muted }}>서버에 연결되면 추천 키워드가 나타납니다.</Text> : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 16, paddingBottom: 40 },
  title: { fontSize: 24, fontWeight: '800' },
  lead: { fontSize: 14, lineHeight: 20, marginTop: -8 },
  card: { borderRadius: 14, borderWidth: StyleSheet.hairlineWidth, padding: 14, gap: 12 },
  h2: { fontSize: 16, fontWeight: '700' },
  h3: { fontSize: 15, fontWeight: '700' },
  group: { gap: 8 },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  inputRow: { flexDirection: 'row', gap: 8 },
  input: { flex: 1, borderWidth: 1, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10, fontSize: 15 },
  addBtn: { borderRadius: 10, paddingHorizontal: 16, justifyContent: 'center' },
});
