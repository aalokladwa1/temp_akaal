export class GovernancePersistenceStore {
  public static getItem<T>(key: string, defaultData: T[]): T[] {
    if (typeof window === 'undefined') return defaultData;
    try {
      const stored = localStorage.getItem(`akaal_gov_${key}`);
      return stored ? JSON.parse(stored) : defaultData;
    } catch {
      return defaultData;
    }
  }

  public static setItem<T>(key: string, data: T[]): void {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(`akaal_gov_${key}`, JSON.stringify(data));
    } catch {
      // Storage unavailable
    }
  }
}
