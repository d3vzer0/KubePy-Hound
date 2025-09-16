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


class RoleBinding(BaseModel):
    kind: str | None = None
    subjects: list[Subject] = []
    metadata: Metadata
    role_ref: RoleRef
    subjects: list[Subject]

    @field_validator("subjects", mode="before")
    def validate_subjects(cls, v):
        if not v:
            return []
        return v


class ExtendedProperties(NodeProperties):
    namespace: str
    role_ref: str
    subjects: list[Subject]


class RoleBindingNode(Node):
    properties: ExtendedProperties

    def _get_target_user(self, target_name: str) -> "EdgePath":
        target_id = lookups.users(target_name)
        return EdgePath(value=target_id, match_by="id")

    def _get_target_group(self, target_name: str) -> "EdgePath":
        target_id = lookups.groups(target_name)
        return EdgePath(value=target_id, match_by="id")

    @property
    def _namespace_edge(self):
        target_id = lookups.namespaces(self.properties.namespace)
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sBelongsTo", start=start_path, end=end_path)
        return edge

    @property
    def _role_edge(self):
        target_id = lookups.roles(self.properties.role_ref, self.properties.namespace)
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sReferencesRole", start=start_path, end=end_path)
        return edge

    @property
    def _subjects(self):
        edges = []
        start_path = EdgePath(value=self.id, match_by="id")
        for target in self.properties.subjects:
            if target.kind == "ServiceAccount":
                namespace = (
                    target.namespace if target.namespace else self.properties.namespace
                )
                target_id = lookups.service_accounts(target.name, namespace)
                if target_id:
                    end_path = EdgePath(value=target_id, match_by="id")
                    edges.append(
                        Edge(kind="K8sAuthorizes", start=start_path, end=end_path)
                    )
                if not target_id:
                    source_ref = SourceRef(name=self.properties.name, uid=self.id)
                    self._stale_collection.add(
                        StaleReference(
                            resource_type="KubeServiceAccount",
                            name=target.name,
                            source_ref=source_ref,
                            edge_type="AUTHORIZES",
                        )
                    )

            elif target.kind == "User":
                end_path = self._get_target_user(target.name)
                edges.append(Edge(kind="K8sAuthorizes", start=start_path, end=end_path))

            elif target.kind == "Group":
                end_path = self._get_target_group(target.name)
                edges.append(Edge(kind="K8sAuthorizes", start=start_path, end=end_path))

            else:
                print(
                    f"Unsupported subject kind: {target.kind} in RoleBinding {self.properties.name}"
                )

        return edges

    @property
    def edges(self):
        all_edges = self._subjects
        return [self._namespace_edge, self._role_edge, *all_edges]

    @classmethod
    def from_input(cls, **kwargs) -> "RoleBindingNode":
        model = RoleBinding(**kwargs)
        properties = ExtendedProperties(
            name=model.metadata.name,
            displayname=model.metadata.name,
            # objectid=model.metadata.uid,
            namespace=model.metadata.namespace,
            role_ref=model.role_ref.name,
            subjects=model.subjects,
        )
        return cls(
            id=model.metadata.uid,
            kinds=["K8sScopedRoleBinding", "K8sRoleBinding"],
            properties=properties,
        )
