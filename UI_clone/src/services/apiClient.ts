import { envConfig } from '../config/env.config';

export interface ApiResponse<T> {
  data: T | null;
  error: string | null;
  statusCode: number;
}

export class ApiClient {
  private static async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    const url = `${envConfig.apiBaseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    try {
      if (envConfig.mockMode) {
        // Mock mode bypasses real network call and returns successful envelope
        return { data: null, error: null, statusCode: 200 };
      }

      const res = await fetch(url, { ...options, headers });
      if (!res.ok) {
        const errorText = await res.text();
        return {
          data: null,
          error: `HTTP Error ${res.status}: ${errorText || res.statusText}`,
          statusCode: res.status,
        };
      }

      const data = await res.json();
      return { data, error: null, statusCode: res.status };
    } catch (err: any) {
      return {
        data: null,
        error: err.message || 'Network Timeout or Host Unreachable',
        statusCode: 503,
      };
    }
  }

  public static get<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  public static post<T>(endpoint: string, body: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'POST', body: JSON.stringify(body) });
  }

  public static put<T>(endpoint: string, body: any): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'PUT', body: JSON.stringify(body) });
  }

  public static delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}
