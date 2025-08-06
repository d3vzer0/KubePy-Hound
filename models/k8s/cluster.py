from pydantic import BaseModel, model_validator
from models.entries import Node, NodeProperties
from utils.guid import get_guid
from typing_extensions import Self


class Cluster(BaseModel):
    name: str
    uid: str | None = None

    @model_validator(mode='after')
    def set_guid(self) -> Self:
        self.uid = get_guid(self.name, scope="system", kube_type="cluster", name=self.name)
        return self


class ClusterNode(Node):

    @property
    def edges(self):
        return []

    @classmethod
    def from_input(cls, **kwargs) -> "ClusterNode":
        cluster = Cluster(**kwargs)
        properties = NodeProperties(name=cluster.name, displayname=cluster.name)
        return cls(id=cluster.uid, kinds=["KubeCluster"], properties=properties)
