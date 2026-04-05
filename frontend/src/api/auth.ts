import type { TokenResponse } from '../types';
import client from './client';

export async function login(email: string, password: string): Promise<TokenResponse> {
  const response = await client.post<TokenResponse>('/auth/login', { email, password });
  return response.data;
}

export async function refreshToken(refresh: string): Promise<TokenResponse> {
  const res = await client.post<TokenResponse>('/auth/refresh', {
    refresh_token: refresh,
  });
  return res.data;
}

export async function logout(): Promise<void> {
  try {
    await client.post('/auth/logout');
  } finally {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }
}
