from pydantic import BaseModel, Field
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from kubepyhound.utils.guid import get_guid
from kubepyhound.models import lookups


class User(BaseModel):
    name: str
    api_group: str
    uid: str = Field(
        default_factory=lambda data: get_guid(
            data["name"], scope="system", kube_type="user", name=data["name"]
        )
    )
    groups: list[str] = []


class Group(BaseModel):
    name: str
    api_group: str
    uid: str = Field(
        default_factory=lambda data: get_guid(
            data["name"], scope="system", kube_type="group", name=data["name"]
        )
    )
    members: list[str] = []


class UserNode(Node):

    @property
    def _authenticated_group_edge(self):
        target_id = lookups.groups("system:authenticated")
        start_path = EdgePath(value=self.id, match_by="id")
        end_path = EdgePath(value=target_id, match_by="id")
        edge = Edge(kind="K8sMemberOf", start=start_path, end=end_path)
        return edge

    @property
    def edges(self):
        return [self._authenticated_group_edge]

    @classmethod
    def from_input(cls, **kwargs) -> "UserNode":
        model = User(**kwargs)
        properties = NodeProperties(name=model.name, displayname=model.name)
        return cls(id=model.uid, kinds=["K8sUser"], properties=properties)


class GroupNode(Node):
    @property
    def edges(self):
        return []

    @classmethod
    def from_input(cls, **kwargs) -> "GroupNode":
        model = Group(**kwargs)
        properties = NodeProperties(name=model.name, displayname=model.name)
        return cls(id=model.uid, kinds=["K8sGroup"], properties=properties)
