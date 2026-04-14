import client from './client';
import type { PriceHistory, PriceStats } from '../types';

export const getPriceHistory = async (
  productId: string,
  params?: { days?: number; limit?: number }
): Promise<PriceHistory[]> => {
  const res = await client.get<PriceHistory[]>(
    `/products/${productId}/prices`,
    { params }
  );
  return res.data;
};

export async function getPriceStats(productId: string): Promise<PriceStats> {
  const res = await client.get<PriceStats>(
    `/products/${productId}/prices/stats`
  );
  return res.data;
}
