from pydantic import BaseModel, field_validator
from datetime import datetime
from models.entries import (
    Node,
    NodeProperties,
    Edge,
    EdgePath,
    StaleReference,
    SourceRef,
)
from models import lookups


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
    kind: str | None = None
    metadata: Metadata
    role_ref: RoleRef
    subjects: list[Subject] = []

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
    def _role_edge(self):
        target_id = lookups.cluster_roles(self.properties.role_ref)
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sReferencesRole", start=start_path, end=end_path)
        return edge

    def _service_account(self, start_path, target, namespace):
        target_id = lookups.service_accounts(target.name, namespace)
        if not target_id:
            source_ref = SourceRef(name=self.properties.name, uid=self.id)
            self._stale_collection.add(
                StaleReference(
                    resource_type="K8sServiceAccount",
                    name=target.name,
                    source_ref=source_ref,
                    edge_type="K8sAuthorizes",
                )
            )
            return None

        else:
            end_path = EdgePath(value=target_id, match_by="id")
            return Edge(kind="K8sAuthorizes", start=start_path, end=end_path)

    def _get_target_user(self, target_name: str) -> "EdgePath":
        target_id = lookups.users(target_name)
        return EdgePath(value=target_id, match_by="id")

    def _get_target_group(self, target_name: str) -> "EdgePath":
        target_id = lookups.groups(target_name)
        return EdgePath(value=target_id, match_by="id")

    @property
    def _subjects(self):
        edges = []
        start_path = EdgePath(value=self.id, match_by="id")
        for target in self.properties.subjects:
            if target.kind == "ServiceAccount":
                namespace = target.namespace
                # if namespace in lookups.service_accounts:
                get_service_account_edge = self._service_account(
                    start_path, target, namespace
                )
                # TODO CHECK NONE
                if get_service_account_edge:
                    edges.append(get_service_account_edge)
                    # else:
                    # print(f"Unsupported subject kind: {target.kind} in ClusterRoleBinding {self.properties.name}")

            elif target.kind == "User":
                end_path = self._get_target_user(target.name)
                edges.append(Edge(kind="K8sAuthorizes", start=start_path, end=end_path))

            elif target.kind == "Group":
                end_path = self._get_target_group(target.name)
                edges.append(Edge(kind="K8sAuthorizes", start=start_path, end=end_path))

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
        )
        return cls(
            id=model.metadata.uid,
            kinds=["K8sClusterRoleBinding", "K8sRoleBinding"],
            properties=properties,
        )
