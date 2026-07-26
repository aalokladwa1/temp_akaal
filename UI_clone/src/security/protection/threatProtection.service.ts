export class ThreatProtectionService {
  private static requestCounts = new Map<string, { count: number; windowStart: number }>();
  private static maxRequestsPerWindow = 100;
  private static windowMs = 60 * 1000;

  public static isRateLimited(ipAddress: string): boolean {
    const now = Date.now();
    const current = this.requestCounts.get(ipAddress);

    if (!current || now - current.windowStart > this.windowMs) {
      this.requestCounts.set(ipAddress, { count: 1, windowStart: now });
      return false;
    }

    current.count += 1;
    return current.count > this.maxRequestsPerWindow;
  }
}
