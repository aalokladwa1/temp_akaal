export class GovernancePersistenceStore {
  private static memoryStore = new Map<string, string>();

  public static getItem<T>(key: string, defaultData: T[]): T[] {
    if (typeof window === 'undefined') {
      const mem = this.memoryStore.get(`akaal_gov_${key}`);
      return mem ? JSON.parse(mem) : defaultData;
    }
    try {
      const stored = localStorage.getItem(`akaal_gov_${key}`);
      return stored ? JSON.parse(stored) : defaultData;
    } catch {
      return defaultData;
    }
  }

  public static setItem<T>(key: string, data: T[]): void {
    if (typeof window === 'undefined') {
      this.memoryStore.set(`akaal_gov_${key}`, JSON.stringify(data));
      return;
    }
    try {
      localStorage.setItem(`akaal_gov_${key}`, JSON.stringify(data));
    } catch {
      // Storage unavailable
    }
  }
}
