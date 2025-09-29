from pydantic import BaseModel, field_validator, ConfigDict
from datetime import datetime
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from kubepyhound.utils.guid import get_guid
from kubepyhound.utils.guid import NodeTypes
from kubepyhound.models.k8s.pod import Container


class Metadata(BaseModel):
    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime
    labels: dict | None = {}

    @field_validator("labels", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else {}


class HostPath(BaseModel):
    path: str


class Volume(BaseModel):
    name: str
    hostPath: HostPath | None = None


class TemplateSpec(BaseModel):
    containers: list[Container] | None = None
    volumes: list[Volume] | None = None


class Template(BaseModel):
    # metadata: Metadata
    spec: TemplateSpec


class Spec(BaseModel):
    template: Template


class DaemonSet(BaseModel):
    kind: str | None = "DaemonSet"
    metadata: Metadata
    spec: Spec

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "DaemonSet"


class ExtendedProperties(NodeProperties):
    model_config = ConfigDict(extra="allow")


class DaemonSetNode(Node):
    properties: ExtendedProperties

    @classmethod
    def from_input(cls, **kwargs) -> "DaemonSetNode":
        model = DaemonSet(**kwargs)
        properties = ExtendedProperties(
            name=model.metadata.name,
            displayname=model.metadata.name,
            namespace=model.metadata.namespace,
            uid=model.metadata.uid,
        )
        node = cls(kinds=["K8sDaemonSet"], properties=properties)
        return node
