from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    BeforeValidator,
    computed_field,
    field_validator,
)
from datetime import datetime
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from typing import Optional, Any, TypeVar, Annotated
from pydantic_core import PydanticUseDefault
from kubepyhound.utils.guid import get_guid
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


class Metadata(BaseModel):
    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime
    labels: dict


class Pod(BaseModel):
    metadata: Metadata
    spec: Spec
    kind: str | None = "Pod"

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "Pod"


class ExtendedProperties(NodeProperties):
    model_config = ConfigDict(extra="allow")
    # namespace: str
    node_name: str | None = None
    service_account_name: str


class PodNode(Node):
    properties: ExtendedProperties

    @property
    def _namespace_edge(self):
        # target_id = self._lookup.namespaces(self.properties.namespace)
        target_id = get_guid(
            self.properties.namespace, NodeTypes.K8sNamespace, self._cluster
        )
        # print(self.properties.namespace, NodeTypes.K8sNamespace.value, self._cluster)
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sBelongsTo", start=start_path, end=end_path)
        return edge

    @property
    def _node_edge(self):
        # target_id = self._lookup.nodes(self.properties.node_name)
        # print(self.properties.node_name, NodeTypes.K8sNode.name, self._cluster)
        target_id = get_guid(
            self.properties.node_name, NodeTypes.K8sNode, self._cluster
        )
        # resource_path = f"{self.properties.node_name}.{NodeTypes.K8sNode.value}.system.{self._cluster}"

        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sRunsOn", start=start_path, end=end_path)
        return edge

    @property
    def _service_account_edge(self):
        # target_id = self._lookup.service_accounts(
        #     self.properties.namespace, self.properties.service_account_name
        # )
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
            uid=kube_pod.metadata.uid,
            service_account_name=kube_pod.spec.service_account_name,
            **kube_pod.metadata.labels,
            **kube_pod.spec.containers[0].security_context.model_dump(),
        )
        return cls(kinds=["K8sPod"], properties=properties)
