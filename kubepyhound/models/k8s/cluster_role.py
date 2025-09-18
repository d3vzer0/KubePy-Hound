from pydantic import BaseModel, field_validator, Field
from datetime import datetime
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from kubepyhound.models import lookups
from typing import Optional
from enum import Enum
import fnmatch


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
    impersonate = "impersonate"
    wildcard = "*"
    approve = "approve"
    sign = "sign"
    escalate = "escalate"
    bind = "bind"

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
    "impersonate": "K8sCanImpersonate",
    "approve": "K8sCanApprove",
    "sign": "K8sCanSign",
    "escalate": "K8sCanEscalate",
    "bind": "K8sCanBind",
    "*": "K8sCanAll",
}


class Metadata(BaseModel):
    name: str
    uid: str
    creation_timestamp: datetime
    labels: dict | None = None


class Rule(BaseModel):
    api_groups: Optional[list[str]] = ["__core__"]
    resources: Optional[list[str]] = []
    verbs: list[Verbs]
    resource_names: Optional[list[str]] = None

    @field_validator("api_groups")
    def validate_api_groups(cls, v):
        if not v or (len(v) == 1 and v[0] == ""):
            return ["__core__"]
        return v


class ClusterRole(BaseModel):
    metadata: Metadata
    rules: list[Rule] = []

    @field_validator("rules", mode="before")
    def validate_rules(cls, v):
        if not v:
            return []
        return v


class ExtendedProperties(NodeProperties):
    rules: list[Rule] = Field(exclude=True)

    @field_validator("rules")
    def validate_rules(cls, v):
        if not v:
            return []
        return v


class ClusterRoleNode(Node):
    properties: ExtendedProperties

    @property
    def _cluster_edge(self):
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=self._lookup.cluster["uid"], match_by="id")
        edge = Edge(kind="K8sBelongsTo", start=start_path, end=end_path)
        return edge

    def _matching_verbs(self, verbs: list) -> list:
        matched = []
        for verb in verbs:
            for key in VERB_TO_PERMISSION.keys():
                if fnmatch.fnmatch(key, verb.value) and key != "*":
                    matched.append(verb.value)

        return matched

    def _rule_edge(self, rule: Rule):
        targets = []
        if rule.api_groups:
            start_path = EdgePath(value=self.id, match_by="id")
            for target_group in rule.api_groups:
                if rule.resources:
                    resources = (
                        [
                            self._lookup.resource_definitions(rule)
                            for rule in rule.resources
                        ]
                        if target_group == "__core__"
                        else [
                            self._lookup.custom_resource_definitions(rule)
                            for rule in rule.resources
                        ]
                    )
                    for resource in resources:
                        end_path = EdgePath(value=resource, match_by="id")
                        matched_verbs = self._matching_verbs(rule.verbs)
                        for verb in matched_verbs:
                            verb_permission = VERB_TO_PERMISSION[verb]
                            edge = Edge(
                                kind=verb_permission, start=start_path, end=end_path
                            )
                            targets.append(edge)
        return targets

    @property
    def _rules_edge(self):
        edges = []
        for rule in self.properties.rules:
            edges.extend(self._rule_edge(rule))

        return edges

    @property
    def edges(self):
        return [self._cluster_edge, *self._rules_edge]

    @classmethod
    def from_input(cls, **kwargs) -> "ClusterRoleNode":
        model = ClusterRole(**kwargs)
        properties = ExtendedProperties(
            name=model.metadata.name, displayname=model.metadata.name, rules=model.rules
        )
        return cls(
            id=model.metadata.uid,
            kinds=["K8sClusterRole", "K8sRole"],
            properties=properties,
        )


# class ClusterRoleGraphEntries(GraphEntries):
#     nodes: list[ClusterRoleNode] = []
