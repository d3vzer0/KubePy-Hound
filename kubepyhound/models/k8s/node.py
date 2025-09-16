from pydantic import BaseModel
from datetime import datetime
from kubepyhound.models.entries import NodeProperties, Edge, EdgePath
from kubepyhound.models.entries import Node as GraphNode
from kubepyhound.models import lookups


class Metadata(BaseModel):
    name: str
    uid: str
    creation_timestamp: datetime
    labels: dict = {}


class Node(BaseModel):
    metadata: Metadata


class NodeOutput(GraphNode):

    @property
    def _authenticated_group_edge(self):
        target_id = lookups.groups("system:authenticated")
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sMemberOf", start=start_path, end=end_path)
        return edge

    @property
    def _nodes_group_edge(self):
        target_id = lookups.groups("system:nodes")
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sMemberOf", start=start_path, end=end_path)
        return edge

    @property
    def _cluster_edge(self):
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=lookups.cluster["uid"], match_by="id")
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
            name=node_out.metadata.name, displayname=node_out.metadata.name
        )
        return cls(id=node_out.metadata.uid, kinds=["K8sNode"], properties=properties)
