from pydantic import BaseModel, model_validator, computed_field
from kubepyhound.models.entries import Node, NodeProperties
from kubepyhound.utils.guid import get_guid, NodeTypes
from typing_extensions import Self


class Cluster(BaseModel):
    name: str
    kind: str = "Cluster"

    @computed_field
    @property
    def uid(self) -> str:
        return get_guid(self.name, NodeTypes.K8sCluster, self.name)


class ClusterNode(Node):

    @property
    def edges(self):
        return []

    @classmethod
    def from_input(cls, **kwargs) -> "ClusterNode":
        cluster = Cluster(**kwargs)
        properties = NodeProperties(
            name=cluster.name, displayname=cluster.name, uid=cluster.uid
        )
        return cls(kinds=["K8sCluster"], properties=properties)
