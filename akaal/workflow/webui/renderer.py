"""Virtualized Graph Renderer Strategy for 10,000+ Step Workflow DAG Topologies."""

from dataclasses import dataclass, field
from typing import Any, List, Tuple
from akaal.workflow.models.metadata import WorkflowManifest
from akaal.workflow.utils.serialization import compute_sha256


@dataclass(frozen=True, slots=True)
class RenderedGraphTopology:
    """Rendered DAG Topology DTO for WebUI Canvas / Virtualized SVG display."""

    workflow_id: str
    total_nodes: int
    total_edges: int
    visible_node_ids: Tuple[str, ...]
    checksum: str = field(default="", init=False)

    def __post_init__(self) -> None:
        data = {
            "workflow_id": self.workflow_id,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "visible_node_ids": list(self.visible_node_ids),
        }
        object.__setattr__(self, "checksum", compute_sha256(data))


class VirtualizedGraphRenderer:
    """Generates virtualized viewport topologies for large workflow DAGs."""

    def render_manifest_viewport(self, manifest: WorkflowManifest, max_visible_nodes: int = 100) -> RenderedGraphTopology:
        total_nodes = len(manifest.step_definitions)
        visible = tuple(s.step_id for s in manifest.step_definitions[:max_visible_nodes])
        total_edges = sum(len(s.dependencies) for s in manifest.step_definitions)

        return RenderedGraphTopology(
            workflow_id=manifest.metadata.workflow_id,
            total_nodes=total_nodes,
            total_edges=total_edges,
            visible_node_ids=visible,
        )
