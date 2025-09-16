from pydantic import BaseModel
from datetime import datetime
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from kubepyhound.models import lookups


class Metadata(BaseModel):
    name: str
    uid: str
    creation_timestamp: datetime
    labels: dict


class Namespace(BaseModel):
    metadata: Metadata


class NamespaceNode(Node):

    @property
    def _cluster_edge(self):
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=lookups.cluster["uid"], match_by="id")
        edge = Edge(kind="K8sBelongsTo", start=start_path, end=end_path)
        return edge

    @property
    def edges(self):
        return [self._cluster_edge]

    @classmethod
    def from_input(cls, **kwargs) -> "NamespaceNode":
        ns_node = Namespace(**kwargs)
        properties = NodeProperties(
            name=ns_node.metadata.name, displayname=ns_node.metadata.name
        )
        return cls(
            id=ns_node.metadata.uid, kinds=["K8sNamespace"], properties=properties
        )
