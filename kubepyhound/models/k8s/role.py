from pydantic import BaseModel, field_validator, Field
from datetime import datetime
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from kubepyhound.models import lookups
from typing import Optional
from enum import Enum
import fnmatch
from kubepyhound.utils.guid import get_guid, get_generic_guid, NodeTypes


class Verbs(str, Enum):
    get = "get"
    list = "list"
    watch = "watch"
    create = "create"
    update = "update"
    patch = "patch"
    delete = "delete"
    deletecollection = "deletecollection"
    proxy = "proxy"
    wildcard = "*"

    def __str__(self):
        return self.value


VERB_TO_PERMISSION = {
    "get": "K8sCanGet",
    "list": "K8sCanList",
    "watch": "K8sCanWatch",
    "create": "K8sCanCreate",
    "update": "K8sCanUpdate",
    "patch": "K8sCanPatch",
    "delete": "K8sCanDelete",
    "deletecollection": "K8sCanDeleteCollection",
    "proxy": "K8sCanProxy",
    "*": "K8sCanAll",
}


class Spec(BaseModel):
    node_name: str


class Metadata(BaseModel):
    name: str
    uid: str
    namespace: str
    creation_timestamp: datetime
    labels: dict | None = None


class Rule(BaseModel):
    api_groups: list[str] = ["__core__"]
    resources: list[str]
    verbs: list[Verbs]
    resource_names: Optional[list[str]] = None

    @field_validator("api_groups")
    def validate_api_groups(cls, v):
        if not v or (len(v) == 1 and v[0] == ""):
            return ["__core__"]
        return v


class Role(BaseModel):
    metadata: Metadata
    rules: Optional[list[Rule]] = []
    kind: str | None = "Role"

    @field_validator("kind", mode="before")
    def set_default_if_none(cls, v):
        return v if v is not None else "Role"

    @field_validator("rules")
    def validate_rules(cls, v):
        if not v:
            return []
        return v


class ExtendedProperties(NodeProperties):
    # namespace: str
    rules: list[Rule] = Field(exclude=True)

    @field_validator("rules")
    def validate_rules(cls, v):
        if not v:
            return []
        return v


class RoleNode(Node):
    properties: ExtendedProperties

    def _matching_verbs(self, verbs: list) -> list:
        matched = []
        for verb in verbs:
            for key in VERB_TO_PERMISSION.keys():
                if fnmatch.fnmatch(key, verb.value) and key != "*":
                    matched.append(verb.value)

        return matched

    @property
    def _namespace_edge(self):
        target_id = get_guid(
            self.properties.namespace, NodeTypes.K8sNamespace, self._cluster
        )
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sBelongsTo", start=start_path, end=end_path)
        return edge

    def _rule_edge(self, rule: Rule):
        if not rule.api_groups or not rule.resources:
            return []

        start_path = EdgePath(value=self.id, match_by="id")
        matched_verbs = self._matching_verbs(rule.verbs)
        namespace = self.properties.namespace
        verb_permissions = [VERB_TO_PERMISSION[verb] for verb in matched_verbs]

        all_allowed_resources = []
        for resource in rule.resources:
            allowed_resources = self._lookup.allowed_namespaced_resources(
                resource, namespace
            )
            all_allowed_resources.extend(allowed_resources)

        targets = []
        for name, kind, singular, rd in all_allowed_resources:
            for verb_permission in verb_permissions:
                targets.append(
                    Edge(
                        kind=verb_permission,
                        start=start_path,
                        end=EdgePath(
                            value=get_generic_guid(
                                name, f"K8s{kind}", self._cluster, namespace
                            ),
                            match_by="id",
                        ),
                    )
                )

        return targets

    @property
    def _rules_edge(self):
        edges = []
        for rule in self.properties.rules:
            edges.extend(self._rule_edge(rule))
        return edges

    @property
    def edges(self):
        return [self._namespace_edge, *self._rules_edge]

    @classmethod
    def from_input(cls, **kwargs) -> "RoleNode":
        model = Role(**kwargs)
        properties = ExtendedProperties(
            rules=model.rules,
            name=model.metadata.name,
            displayname=model.metadata.name,
            namespace=model.metadata.namespace,
            uid=model.metadata.uid,
        )
        return cls(
            kinds=["K8sScopedRole", "K8sRole"],
            properties=properties,
        )
