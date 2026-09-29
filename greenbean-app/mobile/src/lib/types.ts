export type FlavorCategoryId =
  | 'floral' | 'citrus' | 'berry' | 'stonefruit' | 'tropical' | 'wine' | 'tea'
  | 'sweet' | 'chocolate' | 'nutty' | 'grain' | 'spice' | 'earthy';

export interface Note {
  label: string;
  category: FlavorCategoryId;
}

export interface Origin {
  country: string;
  en: string;
  flag: string;
  continent: string | null;
  region: string | null;
}

export interface Bean {
  id: string;
  shopId: string;
  shopName: string;
  name: string;
  url: string;
  imageUrl: string | null;
  price: number | null;
  listPrice: number | null;
  prevPrice?: number;
  weightGrams: number | null;
  pricePerKg: number | null;
  soldOut: boolean;
  delisted?: boolean;
  origin: Origin | null;
  varieties: string[];
  processes: string[];
  tags: string[];
  notes: Note[];
  flavorMix: { category: FlavorCategoryId; ratio: number }[];
  profile: { acidity: number; sweetness: number; body: number } | null;
  description: string | null;
  firstSeenAt: string;
  lastSeenAt: string;
  restockedAt?: string;
}

export interface FlavorCategory {
  id: FlavorCategoryId;
  name: string;
  emoji: string;
  color: string;
}

export interface ShopInfo {
  id: string;
  name: string;
  homepage: string;
  status?: { lastOkAt?: string; lastCount?: number; lastErrors?: string[] } | null;
}

export interface Meta {
  facets: {
    total: number;
    origins: { country: string; flag: string; continent: string | null; count: number }[];
    varieties: { name: string; count: number }[];
    processes: { name: string; count: number }[];
    tags: { name: string; count: number; group: string | null }[];
    flavors: (FlavorCategory & { count: number })[];
    notes: { label: string; count: number; category: FlavorCategoryId }[];
    shops: { id: string; name: string; count: number }[];
    price: { min: number; max: number } | null;
    pricePerKg: { min: number; max: number } | null;
  };
  keywordPresets: { group: string; keywords: string[] }[];
  flavorCategories: FlavorCategory[];
  shops: ShopInfo[];
  lastCrawlAt: string | null;
  kakaoConfigured: boolean;
}

export interface SearchResult {
  total: number;
  page: number;
  pageSize: number;
  items: Bean[];
}

export type SortKey = 'new' | 'price_asc' | 'price_desc' | 'kg_asc' | 'kg_desc' | 'name';

export interface Filters {
  q: string;
  origin: string[];
  variety: string[];
  process: string[];
  flavor: string[];
  shop: string[];
  keyword: string[];
  minPrice: number | null;
  maxPrice: number | null;
  priceBasis: 'item' | 'kg';
  sort: SortKey;
  inStock: boolean;
  newWithinDays: number | null;
}

export interface Alerts {
  enabled: boolean;
  newArrivals: boolean;
  restock: boolean;
  keywords: string[];
  origins: string[];
  shops: string[];
  maxPricePerKg: number | null;
}

export interface DeviceState {
  kakaoConfigured: boolean;
  kakaoConnected: boolean;
  kakaoError: string | null;
  nickname: string | null;
  alerts: Alerts;
  lastNotifiedAt: string | null;
}
