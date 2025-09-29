from pydantic import BaseModel, field_validator, ConfigDict, PrivateAttr
from datetime import datetime

from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath

# from pydantic_core import PydanticUseDefault
from kubepyhound.utils.guid import get_guid, get_generic_guid
from kubepyhound.utils.guid import NodeTypes
from kubepyhound.models.k8s.pod import Container


class OwnerReferences(BaseModel):
    api_version: str
    controller: bool
    kind: str
    name: str
    uid: str


class Metadata(BaseModel):
    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime
    labels: dict | None = {}
    owner_references: list[OwnerReferences] | None = None

    @field_validator("labels", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else {}


class ReplicaSet(BaseModel):
    kind: str | None = "ReplicaSet"
    metadata: Metadata

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "ReplicaSet"


class ExtendedProperties(NodeProperties):
    model_config = ConfigDict(extra="allow")
    namespace: str


class ReplicaSetNode(Node):
    properties: ExtendedProperties
    _replicaset: ReplicaSet = PrivateAttr()

    @property
    def _owned_by(self):
        edges = []
        start_path = EdgePath(value=self.id, match_by="id")
        if self._replicaset.metadata.owner_references:
            for owner in self._replicaset.metadata.owner_references:
                end_path_id = get_generic_guid(
                    owner.name,
                    f"K8s{owner.kind}",
                    cluster=self._cluster,
                    namespace=self.properties.namespace,
                )
                end_path = EdgePath(value=end_path_id, match_by="id")
                edges.append(Edge(kind="K8sOwnedBy", start=start_path, end=end_path))
        return edges

    @property
    def edges(self):
        return [*self._owned_by]

    @classmethod
    def from_input(cls, **kwargs) -> "ReplicaSetNode":
        model = ReplicaSet(**kwargs)
        properties = ExtendedProperties(
            name=model.metadata.name,
            displayname=model.metadata.name,
            namespace=model.metadata.namespace,
            uid=model.metadata.uid,
        )
        node = cls(kinds=["K8sReplicaSet"], properties=properties)
        node._replicaset = model
        return node
