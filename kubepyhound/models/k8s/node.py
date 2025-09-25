from pydantic import BaseModel, field_validator
from datetime import datetime
from kubepyhound.models.entries import NodeProperties, Edge, EdgePath
from kubepyhound.models.entries import Node as GraphNode
from kubepyhound.models import lookups
from kubepyhound.utils.guid import get_guid, NodeTypes


class Metadata(BaseModel):
    name: str
    uid: str
    creation_timestamp: datetime
    labels: dict = {}


class Node(BaseModel):
    metadata: Metadata
    kind: str | None = "Node"

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "Node"


class NodeOutput(GraphNode):

    @property
    def _authenticated_group_edge(self):
        # target_id = self._lookup.groups("system:authenticated")
        target_id = get_guid("system:authenticated", NodeTypes.K8sGroup, self._cluster)
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sMemberOf", start=start_path, end=end_path)
        return edge

    @property
    def _nodes_group_edge(self):
        # target_id = self._lookup.groups("system:nodes")
        target_id = get_guid("system:nodes", NodeTypes.K8sGroup, self._cluster)
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sMemberOf", start=start_path, end=end_path)
        return edge

    @property
    def _cluster_edge(self):
        target_id = get_guid(self._cluster, NodeTypes.K8sCluster, self._cluster)
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sBelongsTo", start=start_path, end=end_path)
        return edge

    @property
    def edges(self):
        return [
            self._cluster_edge,
            self._authenticated_group_edge,
            self._nodes_group_edge,
        ]

    @classmethod
    def from_input(cls, **kwargs) -> "NodeOutput":
        node_out = Node(**kwargs)
        properties = NodeProperties(
            name=node_out.metadata.name,
            displayname=node_out.metadata.name,
            uid=node_out.metadata.uid,
        )
        # resource_path = f"{properties.name}.{NodeTypes.K8sNode.value}.system.a0704eb1-8213-5055-b822-238ec31feeca"
        # print(resource_path)
        return cls(kinds=["K8sNode"], properties=properties)
