# AKAAL Phase 10 Parts 4–6 – Master Implementation Roadmap & Engineering Blueprint
## CLI, Control Plane WebUI, SDK & Cloud Production Infrastructure

**Document Version:** 1.0.0 (Frozen Master Engineering Plan)  
**Target Architecture Contracts:** `PHASE10_PART1_IMPLEMENTATION_PLAN.md` (v1.3.0 Frozen), `PHASE10_PART3_ENTERPRISE_MASTER_BLUEPRINT_V4.md` (v4.0.0 Frozen)  
**Status:** **FROZEN & CERTIFIED FOR EXECUTION PLANNING ONLY**  
**Architectural Authority:** Independent Architecture Review Board (ARB), Chief Software Architect, Distinguished Software Engineer, Principal Distributed Systems Engineer, Enterprise Solution Architect, Workflow Orchestration Expert, Platform Engineering Lead, Senior SRE, Security Architect, Performance Architect, Principal QA Architect, DevOps Architect, Database Architect  

---

## 1. Executive Summary

### 1.1 Objectives
This master implementation plan establishes the definitive engineering roadmap for **AKAAL Phase 10 Parts 4, 5, and 6**:
- **Part 4**: Enterprise Operational CLI, Control Plane REST/gRPC API Gateway, and Python/REST SDK Client Subsystem (`akaal/workflow/cli/`, `akaal/workflow/api/`, `akaal/workflow/sdk/`).
- **Part 5**: Real-Time WebUI Control Plane, Live Workflow Graph Inspector, and Operational Monitoring Dashboard (`akaal/workflow/webui/`).
- **Part 6**: Enterprise Cloud Infrastructure, Kubernetes Helm Charts, Terraform Multi-Region Deployment, and Production Operations (`deploy/`, `helm/`, `terraform/`).

### 1.2 Scope
Integrated into the frozen Phase 10 Part 1–3 foundation without breaking any existing contracts or introducing circular dependencies.

### 1.3 Deliverables
1. **AKAAL CLI (`akaal-cli`)**: Production-grade command-line interface for workflow submission, status inspection, pause/resume/cancel commands, approval gate sign-off, replay, and worker cluster management.
2. **Control Plane Gateway (`akaal-gateway`)**: FastAPI/gRPC API server exposing OpenAPI v3 endpoints for external client integration.
3. **AKAAL Python SDK (`akaal-sdk`)**: Typed client library providing fluent client APIs for enterprise applications.
4. **AKAAL Live WebUI Dashboard (`akaal-webui`)**: Reactive single-page web dashboard displaying live workflow execution topologies, node health, flame graphs, and approval queues.
5. **Production Deployment Suite**: Production-grade Helm charts, Docker containers, multi-region Terraform modules, Prometheus alert rules, and Grafana dashboards.

### 1.4 Success Criteria
- **100% API Specification Compliance**: All endpoints documented via OpenAPI v3 / gRPC Protobuf v3.
- **Sub-100ms API Latency**: $p_{99} < 100\text{ms}$ for state query endpoints.
- **Zero Breaking Changes**: 100% backward compatibility with Phase 10 Parts 1–3.
- **100% Test Pass Rate**: All unit, integration, contract, security, and chaos tests passing.

---

## 2. Repository Impact Analysis

| Directory Path | Action | Package Ownership | Purpose & Responsibility |
|---|---|---|---|
| `akaal/workflow/cli/` | **Create** | CLI Subsystem | Command-line interface parser, formatter, and commands (`akaal-cli`) |
| `akaal/workflow/api/` | **Create** | API Gateway | REST & gRPC API gateway routers, request schemas, and middleware |
| `akaal/workflow/sdk/` | **Create** | SDK Client | Client library facade, connection pooling, and SDK models |
| `akaal/workflow/webui/` | **Create** | Web Control Plane | WebUI static server, WebSocket live event streaming backend, and topology renderer |
| `deploy/kubernetes/` | **Create** | DevOps Infrastructure | Production Kubernetes manifests & Helm charts |
| `deploy/terraform/` | **Create** | Cloud Infrastructure | Multi-region AWS/Azure/GCP Terraform infrastructure modules |
| `docs/` | **Modify** | Documentation | Update API references, CLI manuals, and deployment guides |

---

## 3. Dependency Analysis

```
                        [ Client Tier ]
          ┌────────────────────┼────────────────────┐
          ▼                    ▼                    ▼
     [AKAAL CLI]          [Python SDK]        [WebUI React App]
          │                    │                    │
          └────────────────────┼────────────────────┘
                               ▼
                   [ API & gRPC Gateway ]
               (FastAPI / OpenTelemetry / Auth)
                               │
                               ▼
                   [ ControlPlaneEngine ]
               (Phase 10 Part 3 Foundation)
                               │
                               ▼
                   [ WorkflowExecutionEngine ]
```

- **Upstream Dependencies**: Depends strictly on `ControlPlaneEngine`, `WorkflowExecutionEngine`, `WorkflowScheduler`, `StateController`, `ApprovalEngine`, `EventStore`.
- **Downstream Dependencies**: Exposes endpoints consumed by CLI, Python SDK, WebUI, and external CI/CD pipelines.

---

## 4. Component Inventory

1. `CliApplication`: Argument parser and command router for `akaal-cli`.
2. `ApiGatewayServer`: FastAPI REST/gRPC server serving API endpoints.
3. `WorkflowSdkClient`: Typed Python client interface for workflow lifecycle management.
4. `WebUiStreamer`: WebSocket real-time event streaming coordinator.
5. `ClusterManager`: Cluster node status, draining, and quarantine management interface.

---

## 5. Class Inventory

### 5.1 `akaal/workflow/cli/main.py`
- `CliApplication`: Entry point parsing sys.argv and invoking subcommands.
- `WorkflowCliCommands`: Subcommands (`submit`, `status`, `pause`, `resume`, `cancel`, `approve`, `reject`, `replay`).

### 5.2 `akaal/workflow/api/server.py`
- `ApiGatewayServer`: Configures FastAPI app, CORS, OAuth2 JWT auth middleware, and OpenTelemetry instrumentation.
- `WorkflowRouter`: Endpoints (`POST /v1/workflows`, `GET /v1/workflows/{id}`, `POST /v1/workflows/{id}/approve`).

### 5.3 `akaal/workflow/sdk/client.py`
- `AkaalClient`: Fluent client SDK with connection retry, exponential backoff, and async support.

### 5.4 `akaal/workflow/webui/streamer.py`
- `WebSocketEventBroadcaster`: Subscribes to `IEventDispatcher` and broadcasts CloudEvents to WebUI clients via WebSocket.

---

## 6. Interface Inventory

```python
class IAkaalClient(Protocol):
    def submit_workflow(self, manifest_path: str, parameters: dict) -> str: ...
    def get_status(self, workflow_id: str) -> dict: ...
    def approve_gate(self, request_id: str, token: str) -> bool: ...

class IWebUiBroadcaster(Protocol):
    def broadcast_event(self, event: dict) -> None: ...
```

---

## 7. Data Flow Specifications

```text
[ User / CLI / WebUI ] ──► [ HTTP POST /v1/workflows ]
                                    │
                                    ▼
                         [ ApiGatewayServer ]
                        (OAuth2 JWT + CEL Auth)
                                    │
                                    ▼
                         [ ControlPlaneEngine ]
                      (Admission Check & Plan)
                                    │
                                    ▼
                     [ WorkflowExecutionEngine ]
```

---

## 8. Concurrency & Async Boundary Model

- API Server: Async non-blocking ASGI (`uvicorn` / `FastAPI`).
- WebSocket Streamer: Async asyncio event loop broadcasting domain events.
- CLI: Synchronous execution with progress spinners.

---

## 9. Failure & Recovery Model

- API Transient Failure: Automatic retry with jitter in Python SDK (`AkaalClient`).
- WebSocket Disconnection: Client-side automatic exponential reconnection.
- Gateway Crash: Stateless API servers behind load balancer automatically replaced by Kubernetes HPA.

---

## 10. Security & Compliance Model

- **Authentication**: OAuth2 Bearer Tokens (JWT with RSA-256 signatures).
- **Authorization**: Fine-grained RBAC/ABAC policies via `SecurityPolicyEngine` (CEL/Rego).
- **Transport Security**: TLS 1.3 enforced for all REST, gRPC, and WebSocket connections.
- **Audit**: All CLI commands, API calls, and WebUI approvals logged to `AuditLogger` with user identity and IP address.

---

## 11. Performance & Latency Targets

- **API Throughput**: $\ge 5,000$ requests/sec per API gateway node.
- **Query Latency**: $p_{95} < 20\text{ms}$, $p_{99} < 50\text{ms}$.
- **WebSocket Latency**: Real-time event delivery $< 100\text{ms}$ end-to-end.

---

## 12. Observability & Alerting Plan

- **Prometheus Metrics**: `akaal_api_requests_total`, `akaal_api_latency_seconds`, `akaal_active_websocket_connections`.
- **Distributed Tracing**: OpenTelemetry W3C `traceparent` headers injected across API -> ControlPlane -> Worker boundaries.
- **Alert Rules**: Alert SRE when API $p_{99}$ latency exceeds $200\text{ms}$ or HTTP 5xx error rate exceeds $1\%$.

---

## 13. Configuration Hierarchy & Defaults

- Configuration loaded from:
  1. CLI flags (`--gateway-url`)
  2. Environment variables (`AKAAL_GATEWAY_URL`)
  3. Config file (`akaal_config.json`)
  4. Built-in defaults

---

## 14. Testing Strategy

1. **Unit Tests**: Test CLI parsing, API request validation, SDK retry logic, WebSocket payload serialization.
2. **Integration Tests**: End-to-end tests from CLI/SDK through API Gateway to `WorkflowExecutionEngine`.
3. **Contract Tests**: OpenAPI v3 schema validation and gRPC proto compatibility.
4. **Security Tests**: Test OAuth2 JWT forgery rejection, RBAC permission denial, cross-tenant isolation.
5. **Load & Stress Tests**: Locust/k6 load testing at 10,000 RPS.

---

## 15. Verification Checklist

- [ ] OpenAPI v3 schema generated and valid.
- [ ] AKAAL CLI binary/package buildable via `pip install -e .`.
- [ ] Python SDK published and importable as `import akaal.sdk`.
- [ ] Live WebUI static bundle served cleanly.
- [ ] Helm charts valid (`helm lint deploy/kubernetes/akaal`).
- [ ] 100% type annotations across all new modules.
- [ ] Zero circular imports.

---

## 16. Production Readiness Checklist

- [ ] Multi-region AWS/Azure Terraform scripts tested.
- [ ] Auto-scaling rules configured (CPU > 70%, Memory > 80%).
- [ ] Disaster recovery RPO = 0, RTO < 60 seconds verified.
- [ ] TLS 1.3 certificate auto-renewal configured via cert-manager.

---

## 17. Risk Register

| Risk ID | Category | Severity | Mitigation |
|---|---|:---:|---|
| RSK-P4-01 | API Gateway memory leak under high WebSocket concurrency | High | Asyncio connection limits & backpressure |
| RSK-P5-01 | WebUI rendering lag with 10,000+ step DAGs | Medium | Virtualized DAG graph rendering |
| RSK-P6-01 | Cross-region network partition latency spikes | High | Local regional read-replicas |

---

## 18. Documentation Plan

- `docs/CLI_USER_GUIDE.md`
- `docs/REST_API_SPECIFICATION.md`
- `docs/PYTHON_SDK_GUIDE.md`
- `docs/WEBUI_OPERATIONS_MANUAL.md`
- `docs/KUBERNETES_DEPLOYMENT_GUIDE.md`

---

## 19. Git Strategy

Standard Git flow:
```bash
git status
git add -A
git commit -m "feat(phase10): implement parts 4-6 CLI, WebUI, SDK & cloud deployment"
git push origin main
git pull --rebase origin main
```

---

## 20. Definition of Done

- All Parts 4, 5, and 6 components implemented, tested, and verified.
- 100% type hint annotation coverage across all Python files.
- All workspace tests passing with zero failures and zero regressions.
- Git repository clean and synchronized with `origin/main`.
