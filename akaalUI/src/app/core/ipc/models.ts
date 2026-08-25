/**
 * akaalUI IPC Protocol Contracts
 * Strictly mirrors akaalIPC.protocol envelopes and schemas 1:1.
 */

export const CURRENT_PROTOCOL_VERSION = '1.0.0';

export enum RequestKind {
  COMMAND = 'command',
  QUERY = 'query',
  SUBSCRIPTION = 'subscription',
}

export enum ResponseStatus {
  OK = 'ok',
  ACCEPTED = 'accepted',
  ERROR = 'error',
  INVALID = 'invalid',
  UNAUTHORIZED = 'unauthorized',
  FORBIDDEN = 'forbidden',
  NOT_FOUND = 'not_found',
  CONFLICT = 'conflict',
}

export interface ActorReference {
  actor_id: string;
  actor_type: string;
  display_name: string;
}

export interface ActorContext {
  actor: ActorReference;
  organization_id?: string;
  workspace_id?: string;
  project_id?: string;
  roles?: string[];
}

export interface CorrelationContext {
  request_id: string;
  correlation_id: string;
  causation_id?: string;
  session_id?: string;
}

export interface CommandEnvelope<T = Record<string, any>> {
  protocol_version: string;
  request_id: string;
  schema_version: string;
  request_type: string;
  kind: RequestKind.COMMAND;
  actor: ActorContext;
  correlation: CorrelationContext;
  command_id: string;
  payload: T;
}

export interface QueryEnvelope<T = Record<string, any>> {
  protocol_version: string;
  request_id: string;
  schema_version: string;
  request_type: string;
  kind: RequestKind.QUERY;
  actor: ActorContext;
  correlation: CorrelationContext;
  payload: T;
}

export interface ErrorDetail {
  code: string;
  message: string;
  details?: Record<string, any>;
  retryable?: boolean;
}

export interface ResponseEnvelope<T = any> {
  protocol_version: string;
  request_id: string;
  correlation_id: string;
  schema_version: string;
  status: ResponseStatus;
  result?: T;
  error?: ErrorDetail;
  meta?: Record<string, any>;
}
