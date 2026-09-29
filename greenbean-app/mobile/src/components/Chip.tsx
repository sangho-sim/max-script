import { Pressable, StyleSheet, Text, type StyleProp, type ViewStyle } from 'react-native';
import { useTheme } from '@/lib/theme';

interface Props {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  onLongPress?: () => void;
  count?: number;
  small?: boolean;
  trailing?: string;
  style?: StyleProp<ViewStyle>;
}

export function Chip({ label, selected, onPress, onLongPress, count, small, trailing, style }: Props) {
  const t = useTheme();
  return (
    <Pressable
      onPress={onPress}
      onLongPress={onLongPress}
      accessibilityRole="button"
      accessibilityState={{ selected: !!selected }}
      style={({ pressed }) => [
        styles.chip,
        small && styles.small,
        {
          backgroundColor: selected ? t.accent : t.card,
          borderColor: selected ? t.accent : t.border,
          opacity: pressed ? 0.7 : 1,
        },
        style,
      ]}
    >
      <Text style={[styles.text, small && styles.smallText, { color: selected ? t.accentText : t.text }]} numberOfLines={1}>
        {label}
        {count != null ? <Text style={{ color: selected ? t.accentText : t.muted }}> {count}</Text> : null}
        {trailing ? <Text style={{ color: selected ? t.accentText : t.muted }}> {trailing}</Text> : null}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: { paddingHorizontal: 12, paddingVertical: 7, borderRadius: 999, borderWidth: 1 },
  small: { paddingHorizontal: 10, paddingVertical: 5 },
  text: { fontSize: 14, fontWeight: '500' },
  smallText: { fontSize: 13 },
});
