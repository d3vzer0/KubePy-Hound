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
from kubepyhound.utils.guid import get_guid
from kubepyhound.utils.guid import NodeTypes


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
    kind: str | None = "RoleBinding"
    subjects: list[Subject] = []
    metadata: Metadata
    role_ref: RoleRef
    subjects: list[Subject]

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "RoleBinding"

    @field_validator("subjects", mode="before")
    def validate_subjects(cls, v):
        if not v:
            return []
        return v


class ExtendedProperties(NodeProperties):
    # namespace: str
    role_ref: str
    subjects: list[Subject]


class RoleBindingNode(Node):
    properties: ExtendedProperties

    def _get_target_user(self, target_name: str) -> "EdgePath":
        target_id = get_guid(target_name, NodeTypes.K8sUser, self._cluster)
        return EdgePath(value=target_id, match_by="id")

    def _get_target_group(self, target_name: str) -> "EdgePath":
        target_id = get_guid(target_name, NodeTypes.K8sUser, self._cluster)
        return EdgePath(value=target_id, match_by="id")

    def _service_account_path(self, target: str, namespace):
        target_id = get_guid(
            target, NodeTypes.K8sServiceAccount, self._cluster, namespace
        )
        return EdgePath(value=target_id, match_by="id")

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
    def _role_path(self):
        role_id = get_guid(
            self.properties.role_ref,
            NodeTypes.K8sScopedRole,
            self._cluster,
            namespace=self.properties.namespace,
        )
        edge_path = EdgePath(value=role_id, match_by="id")
        return edge_path

    @property
    def _role_edge(self):
        start_path = EdgePath(value=self.id, match_by="id")
        edge = Edge(kind="K8sReferencesRole", start=start_path, end=self._role_path)
        return edge

    @property
    def _subjects(self):
        edges = []
        rb_path = EdgePath(value=self.id, match_by="id")
        for target in self.properties.subjects:
            if target.kind == "ServiceAccount":
                namespace = (
                    target.namespace if target.namespace else self.properties.namespace
                )
                get_sa_path = self._service_account_path(target.name, namespace)
                sa_edge = Edge(kind="K8sAuthorizes", start=rb_path, end=get_sa_path)

                role_edge = Edge(
                    kind="K8sInheritsRole",
                    start=get_sa_path,
                    end=self._role_path,
                    properties={"composed": True},
                )

                edges.append(sa_edge)
                edges.append(role_edge)

                # if not target_id:
                #     source_ref = SourceRef(name=self.properties.name, uid=self.id)
                #     self._stale_collection.add(
                #         StaleReference(
                #             resource_type="KubeServiceAccount",
                #             name=target.name,
                #             source_ref=source_ref,
                #             edge_type="AUTHORIZES",
                #         )
                #     )

            elif target.kind == "User":
                end_path = self._get_target_user(target.name)
                edges.append(Edge(kind="K8sAuthorizes", start=rb_path, end=end_path))

            elif target.kind == "Group":
                end_path = self._get_target_group(target.name)
                edges.append(Edge(kind="K8sAuthorizes", start=rb_path, end=end_path))

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
            uid=model.metadata.uid,
        )
        return cls(
            kinds=["K8sScopedRoleBinding", "K8sRoleBinding"],
            properties=properties,
        )
