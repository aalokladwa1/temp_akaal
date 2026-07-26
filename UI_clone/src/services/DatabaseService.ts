import { ApiClient, ApiResponse } from './apiClient';
import { DatabaseModel } from '../types/models';

export class DatabaseService {
  public static async getDatabases(): Promise<ApiResponse<DatabaseModel[]>> {
    return ApiClient.get<DatabaseModel[]>('/databases');
  }

  public static async testConnection(id: string): Promise<ApiResponse<{ success: boolean; latencyMs: number }>> {
    return ApiClient.post<{ success: boolean; latencyMs: number }>(`/databases/${id}/test`, {});
  }

  public static async createDatabase(db: Partial<DatabaseModel>): Promise<ApiResponse<DatabaseModel>> {
    return ApiClient.post<DatabaseModel>('/databases', db);
  }

  public static async deleteDatabase(id: string): Promise<ApiResponse<{ deleted: boolean }>> {
    return ApiClient.delete<{ deleted: boolean }>(`/databases/${id}`);
  }
}
