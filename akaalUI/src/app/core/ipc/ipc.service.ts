import { Injectable } from '@angular/core';
import { Observable, from, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import {
  CommandEnvelope,
  QueryEnvelope,
  ResponseEnvelope,
  ResponseStatus,
  RequestKind,
  CURRENT_PROTOCOL_VERSION,
  ActorContext,
  CorrelationContext,
} from './models';

@Injectable({
  providedIn: 'root',
})
export class IpcService {
  private activeActor: ActorContext = {
    actor: {
      actor_id: 'usr-local-admin',
      actor_type: 'user',
      display_name: 'Local Administrator',
    },
    organization_id: 'org-primary',
    workspace_id: 'ws-default',
    roles: ['admin'],
  };

  /**
   * Dispatches a typed CommandEnvelope to akaalIPC
   */
  public executeCommand<TPayload = any, TResult = any>(
    requestType: string,
    payload: TPayload,
    schemaVersion: string = '1.0.0'
  ): Observable<ResponseEnvelope<TResult>> {
    const requestId = this.generateUuid('req');
    const commandId = this.generateUuid('cmd');
    const correlationId = this.generateUuid('corr');

    const envelope: CommandEnvelope<TPayload> = {
      protocol_version: CURRENT_PROTOCOL_VERSION,
      request_id: requestId,
      schema_version: schemaVersion,
      request_type: requestType,
      kind: RequestKind.COMMAND,
      actor: this.activeActor,
      correlation: {
        request_id: requestId,
        correlation_id: correlationId,
      },
      command_id: commandId,
      payload,
    };

    return this.dispatchToTauriBridge<CommandEnvelope<TPayload>, TResult>('dispatch_command', envelope);
  }

  /**
   * Dispatches a typed QueryEnvelope to akaalIPC
   */
  public executeQuery<TPayload = any, TResult = any>(
    requestType: string,
    payload: TPayload,
    schemaVersion: string = '1.0.0'
  ): Observable<ResponseEnvelope<TResult>> {
    const requestId = this.generateUuid('req');
    const correlationId = this.generateUuid('corr');

    const envelope: QueryEnvelope<TPayload> = {
      protocol_version: CURRENT_PROTOCOL_VERSION,
      request_id: requestId,
      schema_version: schemaVersion,
      request_type: requestType,
      kind: RequestKind.QUERY,
      actor: this.activeActor,
      correlation: {
        request_id: requestId,
        correlation_id: correlationId,
      },
      payload,
    };

    return this.dispatchToTauriBridge<QueryEnvelope<TPayload>, TResult>('dispatch_query', envelope);
  }

  private dispatchToTauriBridge<TEnvelope, TResult>(
    channel: string,
    envelope: TEnvelope
  ): Observable<ResponseEnvelope<TResult>> {
    // Check if running inside Tauri webview
    if (typeof window !== 'undefined' && (window as any).__TAURI_INTERNALS__) {
      return from(
        (window as any).__TAURI_INTERNALS__.invoke(channel, { envelope }) as Promise<ResponseEnvelope<TResult>>
      ).pipe(
        catchError((err) =>
          of({
            protocol_version: CURRENT_PROTOCOL_VERSION,
            request_id: (envelope as any).request_id || 'err',
            correlation_id: (envelope as any).correlation?.correlation_id || 'err',
            schema_version: '1.0.0',
            status: ResponseStatus.ERROR,
            error: {
              code: 'TAURI_IPC_FAILURE',
              message: String(err),
              retryable: false,
            },
          })
        )
      );
    } else {
      // Browser Development Fallback Mock
      console.log(`[IpcService Mock Dispatch -> ${channel}]`, envelope);
      return of({
        protocol_version: CURRENT_PROTOCOL_VERSION,
        request_id: (envelope as any).request_id || 'mock',
        correlation_id: (envelope as any).correlation?.correlation_id || 'mock',
        schema_version: '1.0.0',
        status: ResponseStatus.OK,
        result: {
          acknowledged: true,
          mock: true,
          channel,
        } as unknown as TResult,
      });
    }
  }

  private generateUuid(prefix: string): string {
    return `${prefix}-${Math.random().toString(36).substring(2, 10)}`;
  }
}
