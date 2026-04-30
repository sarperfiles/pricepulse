import client from './client';
import type { User } from '../types';

export const getMe = async (): Promise<User> => {
  const res = await client.get<User>('/users/me');
  return res.data;
};

export async function changePassword(data: {
  current_password: string;
  new_password: string;
}): Promise<void> {
  await client.post('/users/me/password', data);
}
