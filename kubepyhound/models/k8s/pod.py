from pydantic import BaseModel, ConfigDict, Field, BeforeValidator
from datetime import datetime
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from kubepyhound.models import lookups
from typing import Optional, Any, TypeVar, Annotated
from pydantic_core import PydanticUseDefault


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


class Container(BaseModel):
    image: str
    security_context: DefaultIfNone[SecurityContext | None] = Field(
        default_factory=SecurityContext
    )
    volume_mounts: list[VolumeMount] = []


class Spec(BaseModel):
    node_name: str
    service_account_name: Optional[str] = "default"
    containers: list[Container]


class Metadata(BaseModel):
    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime
    labels: dict


class Pod(BaseModel):
    metadata: Metadata
    spec: Spec


class ExtendedProperties(NodeProperties):
    model_config = ConfigDict(extra="allow")
    namespace: str
    node_name: str
    service_account_name: str


class PodNode(Node):
    properties: ExtendedProperties

    @property
    def _namespace_edge(self):
        target_id = lookups.namespaces(self.properties.namespace)
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sBelongsTo", start=start_path, end=end_path)
        return edge

    @property
    def _node_edge(self):
        target_id = lookups.nodes(self.properties.node_name)
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sRunsOn", start=start_path, end=end_path)
        return edge

    @property
    def _service_account_edge(self):
        target_id = lookups.service_accounts(
            self.properties.namespace, self.properties.service_account_name
        )
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sRunsOn", start=start_path, end=end_path)
        return edge

    @property
    def edges(self):
        return [self._node_edge, self._namespace_edge, self._service_account_edge]

    @classmethod
    def from_input(cls, **kwargs) -> "PodNode":
        kube_pod = Pod(**kwargs)
        if "name" in kube_pod.metadata.labels:
            del kube_pod.metadata.labels["name"]
        properties = ExtendedProperties(
            name=kube_pod.metadata.name,
            displayname=kube_pod.metadata.name,
            # objectid=kube_pod.metadata.uid,
            namespace=kube_pod.metadata.namespace,
            node_name=kube_pod.spec.node_name,
            service_account_name=kube_pod.spec.service_account_name,
            **kube_pod.metadata.labels,
            **kube_pod.spec.containers[0].security_context.model_dump(),
        )
        return cls(id=kube_pod.metadata.uid, kinds=["K8sPod"], properties=properties)
