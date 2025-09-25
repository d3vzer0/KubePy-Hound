from pydantic import BaseModel, field_validator
from datetime import datetime
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from kubepyhound.models import lookups
from kubepyhound.utils.guid import get_guid
from kubepyhound.utils.guid import NodeTypes


class Secret(BaseModel):
    field_path: str
    name: str
    namespace: str
    uid: str


class Subject(BaseModel):
    api_group: str | None = None
    kind: str
    name: str
    namespace: str | None = None


class RoleRef(BaseModel):
    api_group: str
    kind: str
    name: str


class Metadata(BaseModel):
    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime
    labels: dict | None = None


class ServiceAccount(BaseModel):
    kind: str | None = "ServiceAccount"
    metadata: Metadata
    automount_service_account_token: bool | None = None
    secrets: list[Secret] | None = None
    exists: bool = True

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "ServiceAccount"


class ExtendedProperties(NodeProperties):
    # namespace: str
    bla: str | None = None


class ServiceAccountNode(Node):
    properties: ExtendedProperties

    @property
    def _namespace_edge(self):
        # target_id = self._lookup.namespaces(self.properties.namespace)
        target_id = get_guid(
            self.properties.namespace, NodeTypes.K8sNamespace, self._cluster
        )
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sBelongsTo", start=start_path, end=end_path)
        return edge

    @property
    def _authenticated_group_edge(self):
        # target_id = self._lookup.groups("system:authenticated")
        target_id = get_guid(
            "system:serviceaccounts", NodeTypes.K8sGroup, self._cluster
        )
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sMemberOf", start=start_path, end=end_path)
        return edge

    @property
    def _service_accounts_edge(self):
        # target_id = self._lookup.groups("system:serviceaccounts")
        target_id = get_guid(
            "system:serviceaccounts", NodeTypes.K8sServiceAccount, self._cluster
        )
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sMemberOf", start=start_path, end=end_path)
        return edge

    @property
    def edges(self) -> list:
        return [
            self._namespace_edge,
            self._authenticated_group_edge,
            self._service_accounts_edge,
        ]

    @classmethod
    def from_input(cls, **kwargs) -> "ServiceAccountNode":
        model = ServiceAccount(**kwargs)
        properties = ExtendedProperties(
            name=model.metadata.name,
            displayname=model.metadata.name,
            namespace=model.metadata.namespace,
            uid=model.metadata.uid,
        )
        return cls(kinds=["K8sServiceAccount"], properties=properties)
