import type { ProjectConnection, DatabaseEngine } from '../types/migration';

type ConnectionChangeListener = (connections: ProjectConnection[]) => void;

class ConnectionRepository {
  private connections: ProjectConnection[] = [];
  private listeners: Set<ConnectionChangeListener> = new Set();

  public getConnections(projectId?: string): ProjectConnection[] {
    if (!projectId) return [...this.connections];
    return this.connections.filter((c) => c.projectId === projectId);
  }

  public subscribe(listener: ConnectionChangeListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    const copy = [...this.connections];
    this.listeners.forEach((fn) => fn(copy));
  }

  public addConnection(
    projectId: string,
    name: string,
    engine: DatabaseEngine,
    endpoint: string,
    environment: 'Production' | 'Staging' | 'UAT' | 'Development' = 'Production'
  ): ProjectConnection {
    const conn: ProjectConnection = {
      id: `conn-${Date.now()}`,
      projectId,
      name,
      engine,
      endpoint,
      environment,
      sslStatus: 'Enforced',
      vaultReference: `vault://connections/${projectId}/${Date.now()}`,
      status: 'Unvalidated',
      latencyMs: 0,
      lastValidatedAt: 'Pending Validation',
    };

    this.connections = [conn, ...this.connections];
    this.notify();
    return conn;
  }

  public removeConnection(id: string): void {
    this.connections = this.connections.filter((c) => c.id !== id);
    this.notify();
  }

  public setConnectionsFromIPC(incoming: ProjectConnection[]): void {
    this.connections = incoming;
    this.notify();
  }
}

export const connectionRepository = new ConnectionRepository();
