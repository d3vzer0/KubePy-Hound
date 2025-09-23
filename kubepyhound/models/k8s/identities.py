from pydantic import BaseModel, Field, computed_field
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from kubepyhound.utils.guid import get_guid, NodeTypes
from kubepyhound.models import lookups


class User(BaseModel):
    name: str
    api_group: str
    groups: list[str] = []


class Group(BaseModel):
    name: str
    api_group: str
    members: list[str] = []


class UserNode(Node):

    @property
    def _authenticated_group_edge(self):
        # target_id = self._lookup.groups("system:authenticated")
        target_id = get_guid("system:authenticated", NodeTypes.K8sGroup, self._cluster)
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
        properties = NodeProperties(name=model.name, displayname=model.name, uid="")
        return cls(kinds=["K8sUser"], properties=properties)


class GroupNode(Node):
    @property
    def edges(self):
        return []

    @classmethod
    def from_input(cls, **kwargs) -> "GroupNode":
        model = Group(**kwargs)
        properties = NodeProperties(name=model.name, displayname=model.name, uid="")
        return cls(kinds=["K8sGroup"], properties=properties)
