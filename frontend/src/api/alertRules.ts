import type { AlertRule, AlertRuleCreateData, AlertRuleUpdateData } from '../types';
import client from './client';

export async function getAlertRules(productId: string): Promise<AlertRule[]> {
  const res = await client.get<AlertRule[]>(
    `/products/${productId}/alerts`
  );
  return res.data;
}

export async function createAlertRule(
  productId: string,
  data: AlertRuleCreateData
): Promise<AlertRule> {
  const res = await client.post<AlertRule>(
    `/products/${productId}/alerts`,
    data
  );
  return res.data;
}

// TODO: maybe add bulk update later
export async function updateAlertRule(
  id: string,
  data: AlertRuleUpdateData
): Promise<AlertRule> {
  const res = await client.patch<AlertRule>(`/products/alerts/${id}`, data);
  return res.data;
}

export async function deleteAlertRule(id: string): Promise<void> {
  await client.delete(`/products/alerts/${id}`);
}
