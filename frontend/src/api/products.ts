import client from './client';
import type { Product, ProductListResponse, ProductCreateData, ProductUpdateData } from '../types';

export async function getProducts(page = 1, size = 50): Promise<ProductListResponse> {
  const res = await client.get<ProductListResponse>('/products/', {
    params: { page, size },
  });
  return res.data;
}

export async function getProduct(id: string): Promise<Product> {
  const res = await client.get<Product>(`/products/${id}`);
  return res.data;
}

export async function createProduct(data: ProductCreateData): Promise<Product> {
  const res = await client.post<Product>('/products/', data);
  return res.data;
}

export async function updateProduct(id: string, data: ProductUpdateData): Promise<Product> {
  const res = await client.patch<Product>('/products/' + id, data);
  return res.data;
}

export async function deleteProduct(id: string): Promise<void> {
  await client.delete(`/products/${id}`);
}

export async function deleteProducts(ids: number[]): Promise<void> {
  await Promise.all(ids.map((id) => client.delete(`/products/${id}`)));
}

export async function triggerScrape(id: string): Promise<void> {
  await client.post(`/products/${id}/scrape`);
}
