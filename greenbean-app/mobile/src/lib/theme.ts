import { useColorScheme } from 'react-native';

const light = {
  bg: '#FAF7F2',
  card: '#FFFFFF',
  sunken: '#F1EBE3',
  text: '#2B211B',
  muted: '#7A6A5D',
  border: '#E6DCD0',
  accent: '#3E7B4F', // 생두 초록
  accentText: '#FFFFFF',
  accentSoft: '#E3F0E6',
  coffee: '#6F4E37',
  danger: '#C2413B',
  newBadge: '#E0533D',
  overlay: 'rgba(20,14,10,0.45)',
};

const dark: typeof light = {
  bg: '#151210',
  card: '#211B18',
  sunken: '#2A231F',
  text: '#F2EBE4',
  muted: '#B3A497',
  border: '#3A302A',
  accent: '#7BC08E',
  accentText: '#10200F',
  accentSoft: '#233A29',
  coffee: '#C69C7B',
  danger: '#F07A73',
  newBadge: '#FF7A61',
  overlay: 'rgba(0,0,0,0.6)',
};

export type Theme = typeof light;

export function useTheme(): Theme {
  return useColorScheme() === 'dark' ? dark : light;
}

/** 향미 색을 배경용으로 옅게 */
export const tint = (hex: string, alpha = 0.16) => {
  const a = Math.round(alpha * 255).toString(16).padStart(2, '0');
  return `${hex}${a}`;
};
