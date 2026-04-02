export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Product {
  id: number;
  name: string;
  url: string;
  platform: string;
  current_price: number | null;
  currency: string;
  scrape_interval: string;
  custom_selector: string | null;
  is_active: boolean;
  last_scraped_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  page: number;
  size: number;
}

export interface ProductCreateData {
  name?: string;
  url: string;
  platform?: string;
  custom_selector?: string;
  scrape_interval?: string;
}

export interface ProductUpdateData {
  name?: string;
  url?: string;
  platform?: string;
  custom_selector?: string | null;
  scrape_interval?: string;
  is_active?: boolean;
}

export interface PriceHistory {
  id: number;
  product_id: number;
  price: number;
  currency: string;
  scraped_at: string;
}

export interface PriceStats {
  min_price: number;
  max_price: number;
  avg_price: number;
  current_price: number;
  price_change_24h: number | null;
  price_change_7d: number | null;
  total_records: number;
}

export interface AlertRule {
  id: number;
  product_id: number;
  rule_type: 'price_below' | 'price_above' | 'price_change_pct' | 'price_drop';
  threshold: number;
  is_active: boolean;
  created_at: string;
}

export interface AlertRuleCreateData {
  rule_type: string;
  threshold: number;
  is_active?: boolean;
}

export interface AlertRuleUpdateData {
  rule_type?: string;
  threshold?: number;
  is_active?: boolean;
}

export interface Notification {
  id: number;
  title: string;
  message: string;
  notification_type: string;
  is_read: boolean;
  old_price: number | null;
  new_price: number | null;
  product_id: number | null;
  product_name: string | null;
  created_at: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  page: number;
  size: number;
  unread_count: number;
}

export interface User {
  id: number;
  email: string;
  display_name: string;
  api_key: string;
}
