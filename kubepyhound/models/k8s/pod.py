from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    BeforeValidator,
    computed_field,
    field_validator,
    PrivateAttr,
)
from datetime import datetime
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from typing import Optional, Any, TypeVar, Annotated
from pydantic_core import PydanticUseDefault
from kubepyhound.utils.guid import get_guid, get_generic_guid
from kubepyhound.utils.guid import NodeTypes


def default_if_none(value: Any) -> Any:
    if value is None:
        raise PydanticUseDefault()
    return value


T = TypeVar("T")
DefaultIfNone = Annotated[T, BeforeValidator(default_if_none)]


class SecurityContext(BaseModel):
    allow_privilege_escalation: DefaultIfNone[bool | None] = False
    privileged: DefaultIfNone[bool | None] = False


class VolumeMount(BaseModel):
    mount_path: str
    name: str


class HostPath(BaseModel):
    path: str


class Volume(BaseModel):
    name: str
    host_path: HostPath | None = None


class Container(BaseModel):
    image: str
    security_context: DefaultIfNone[SecurityContext | None] = Field(
        default_factory=SecurityContext
    )
    volume_mounts: list[VolumeMount] | None = []


class Spec(BaseModel):
    node_name: str | None = None
    service_account_name: Optional[str] = "default"
    containers: list[Container]
    # volumes: list[Volume] | None = None

    volumes: DefaultIfNone[list[Volume] | None] = Field(default=[])


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


class Pod(BaseModel):
    metadata: Metadata
    spec: Spec
    kind: str | None = "Pod"

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "Pod"


class ExtendedProperties(NodeProperties):
    model_config = ConfigDict(extra="allow")
    namespace: str
    node_name: str | None = None
    service_account_name: str


class PodNode(Node):
    properties: ExtendedProperties
    _pod: Pod = PrivateAttr()

    @property
    def _namespace_edge(self):
        target_id = get_guid(
            self.properties.namespace, NodeTypes.K8sNamespace, self._cluster
        )
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sBelongsTo", start=start_path, end=end_path)
        return edge

    @property
    def _node_edge(self):
        if self.properties.node_name:
            target_id = get_guid(
                self.properties.node_name, NodeTypes.K8sNode, self._cluster
            )
            start_path = EdgePath(value=self.id, match_by="id")
            end_path = EdgePath(value=target_id, match_by="id")
            edge = Edge(kind="K8sRunsOn", start=start_path, end=end_path)
            return edge
        else:
            return None

    @property
    def _service_account_edge(self):
        target_id = get_guid(
            self.properties.service_account_name,
            NodeTypes.K8sServiceAccount,
            self._cluster,
            namespace=self.properties.namespace,
        )
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sRunsAs", start=start_path, end=end_path)
        return edge

    @property
    def _owned_by(self):
        edges = []
        start_path = EdgePath(value=self.id, match_by="id")
        if self._pod.metadata.owner_references:
            for owner in self._pod.metadata.owner_references:
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
    def _volume_edges(self):
        edges = []
        # if self._pod.spec.volumes:
        for volume in self._pod.spec.volumes:
            if volume.host_path:
                start_path_id = get_generic_guid(
                    owner.name,
                    f"K8s{owner.kind}",
                    cluster=self._cluster,
                    namespace=self.properties.namespace,
                )
                print(volume)
        return edges

    @property
    def edges(self):
        return [
            self._node_edge,
            self._namespace_edge,
            self._service_account_edge,
            *self._owned_by,
            *self._volume_edges,
        ]

    @classmethod
    def from_input(cls, **kwargs) -> "PodNode":
        kube_pod = Pod(**kwargs)
        properties = ExtendedProperties(
            name=kube_pod.metadata.name,
            displayname=kube_pod.metadata.name,
            namespace=kube_pod.metadata.namespace,
            node_name=kube_pod.spec.node_name,
            uid=kube_pod.metadata.uid,
            service_account_name=kube_pod.spec.service_account_name,
            **kube_pod.metadata.labels,
            **kube_pod.spec.containers[0].security_context.model_dump(),
        )
        node = cls(kinds=["K8sPod"], properties=properties)
        node._pod = kube_pod
        return node
