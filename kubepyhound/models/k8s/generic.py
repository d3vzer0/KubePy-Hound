from pydantic import BaseModel, ConfigDict, Field, BeforeValidator, computed_field
from datetime import datetime
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from kubepyhound.utils.guid import get_guid
from kubepyhound.utils.guid import NodeTypes
from typing import Optional


class Metadata(BaseModel):
    name: str
    uid: str | None = None
    namespace: str | None = None
    creation_timestamp: datetime | None = None
    labels: dict | None = None


class Generic(BaseModel):
    metadata: Metadata
    kind: str


class ExtendedProperties(NodeProperties):
    model_config = ConfigDict(extra="allow")
    uid: str | None
    kind: str


class GenericNode(Node):
    properties: ExtendedProperties

    @property
    def edges(self):
        return []

    @classmethod
    def from_input(cls, **kwargs) -> "GenericNode":
        model = Generic(**kwargs)
        # print(model)
        properties = ExtendedProperties(
            name=model.metadata.name,
            displayname=model.metadata.name,
            namespace=model.metadata.namespace,
            uid=model.metadata.uid,
            kind=model.kind,
        )
        return cls(kinds=[f"K8s{model.kind}"], properties=properties)
