import client from './client';
import type { NotificationListResponse } from '../types';

export async function getNotifications(
  params?: { page?: number; size?: number; unread_only?: boolean }
): Promise<NotificationListResponse> {
  const response = await client.get<NotificationListResponse>('/notifications/', {
    params,
  });
  return response.data;
}

export async function markAsRead(id: string): Promise<void> {
  await client.patch(`/notifications/${id}/read`);
}

export async function markAllAsRead(): Promise<void> {
  await client.post('/notifications/read-all');
}

export const getUnreadCount = async (): Promise<number> => {
  const response = await client.get<{ count: number }>('/notifications/unread-count');
  return response.data.count;
};
