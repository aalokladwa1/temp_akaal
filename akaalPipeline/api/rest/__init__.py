"""
akaalPipeline.api.rest
========================
P7A.6 Enterprise API Platform (REST). A thin adapter into PipelineUnifiedCaller --
NOT a second orchestration backend. Every request becomes a CommandEnvelope/QueryEnvelope
handled by the exact same handle_command()/handle_query() path every other AKAAL caller
(CLI, IPC transport, tests) uses, so this layer inherits P7 authentication/authorization,
tenant isolation, idempotency, and anti-enumeration for free rather than reimplementing any
of it.

GraphQL: deliberately not built. No GraphQL library is installed in this environment and
no dependency manifest exists to add one reproducibly (see progress.md Sec 18); building a
GraphQL layer here would mean either an unimplemented stand-in or an unreproducible new
dependency, neither of which is honest. REST is the real, testable P7A.6 deliverable.
"""

from akaalPipeline.api.rest.app import create_app

__all__ = ["create_app"]
