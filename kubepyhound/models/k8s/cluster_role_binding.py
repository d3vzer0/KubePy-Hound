from pydantic import BaseModel, field_validator
from datetime import datetime
from kubepyhound.models.entries import (
    Node,
    NodeProperties,
    Edge,
    EdgePath,
    StaleReference,
    SourceRef,
)
from kubepyhound.models import lookups
from kubepyhound.utils.guid import get_guid, NodeTypes


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
    creation_timestamp: datetime
    labels: dict | None = None


class ClusterRoleBinding(BaseModel):
    kind: str | None = "ClusterRoleBinding"
    metadata: Metadata
    role_ref: RoleRef
    subjects: list[Subject] = []

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "ClusterRoleBinding"

    @field_validator("subjects", mode="before")
    def validate_subjects(cls, v):
        if not v:
            return []
        return v


class ExtendedProperties(NodeProperties):
    role_ref: str
    subjects: list[Subject] = []

    @field_validator("subjects", mode="before")
    def validate_subjects(cls, v):
        if not v:
            return []
        return v


class ClusterRoleBindingNode(Node):
    properties: ExtendedProperties

    @property
    def _role_path(self):
        role_id = get_guid(
            self.properties.role_ref,
            NodeTypes.K8sClusterRole,
            self._cluster,
        )
        edge_path = EdgePath(value=role_id, match_by="id")
        return edge_path

    @property
    def _role_edge(self):
        start_path = EdgePath(value=self.id, match_by="id")
        return Edge(kind="K8sReferencesRole", start=start_path, end=self._role_path)

    def _service_account_path(self, target: str, namespace):
        target_id = get_guid(
            target, NodeTypes.K8sServiceAccount, self._cluster, namespace
        )
        return EdgePath(value=target_id, match_by="id")

    def _get_target_user(self, target_name: str) -> "EdgePath":
        target_id = get_guid(target_name, NodeTypes.K8sUser, self._cluster)
        return EdgePath(value=target_id, match_by="id")

    def _get_target_group(self, target_name: str) -> "EdgePath":
        target_id = self._lookup.groups(target_name)
        target_id = get_guid(target_name, NodeTypes.K8sGroup, self._cluster)
        return EdgePath(value=target_id, match_by="id")

    @property
    def _subjects(self):
        edges = []
        rb_path = EdgePath(value=self.id, match_by="id")
        for target in self.properties.subjects:
            if target.kind == "ServiceAccount":
                get_sa_path = self._service_account_path(target.name, target.namespace)
                sa_edge = Edge(kind="K8sAuthorizes", start=rb_path, end=get_sa_path)

                role_edge = Edge(
                    kind="K8sInheritsRole",
                    start=get_sa_path,
                    end=self._role_path,
                    properties={"composed": True},
                )

                edges.append(sa_edge)
                edges.append(role_edge)

            elif target.kind == "User":
                end_path = self._get_target_user(target.name)
                edges.append(Edge(kind="K8sAuthorizes", start=rb_path, end=end_path))

            elif target.kind == "Group":
                end_path = self._get_target_group(target.name)
                edges.append(Edge(kind="K8sAuthorizes", start=rb_path, end=end_path))

        return edges

    @property
    def edges(self):
        return [self._role_edge, *self._subjects]

    @classmethod
    def from_input(cls, **kwargs) -> "ClusterRoleBindingNode":
        model = ClusterRoleBinding(**kwargs)
        properties = ExtendedProperties(
            name=model.metadata.name,
            displayname=model.metadata.name,
            role_ref=model.role_ref.name,
            subjects=model.subjects,
            uid=model.metadata.uid,
            namespace=None,
        )
        return cls(
            kinds=["K8sClusterRoleBinding", "K8sRoleBinding"],
            properties=properties,
        )
