from pydantic import BaseModel, Field
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from kubepyhound.utils.guid import get_guid
from kubepyhound.models import lookups


class IAMUser(BaseModel):
    name: str
    arn: str
    uid: str = Field(
        default_factory=lambda data: get_guid(
            data["name"], scope="aws", kube_type="iam-user", name=data["name"]
        )
    )
    groups: list[str]


class ExtendedProperties(NodeProperties):
    groups: list[str]


class IAMUserNode(Node):
    properties: ExtendedProperties

    @property
    def _authenticated_group_edge(self):
        target_id = lookups.groups["system:authenticated"]
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="MEMBER_OF", start=start_path, end=end_path)
        return edge

    @property
    def _all_groups(self):
        groups = []
        start_path = EdgePath(value=self.id, match_by="id")
        for group in self.properties.groups:
            if group in lookups.groups:
                target_id = lookups.groups[group]
                end_path = EdgePath(value=target_id, match_by="id")
                edge = Edge(kind="MEMBER_OF", start=start_path, end=end_path)
                groups.append(edge)

        return groups

    @property
    def edges(self):
        return [self._authenticated_group_edge, *self._all_groups]

    @classmethod
    def from_input(cls, **kwargs) -> "IAMUserNode":
        model = IAMUser(**kwargs)
        properties = ExtendedProperties(
            name=model.name,
            displayname=model.name,
            objectid=model.uid,
            groups=model.groups,
        )
        return cls(
            id=model.uid, kinds=["AWSIAMUser", "KubeUser"], properties=properties
        )
