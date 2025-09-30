from pydantic import BaseModel, Field, computed_field, ConfigDict
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from kubepyhound.utils.guid import get_guid, NodeTypes
from kubepyhound.models import lookups


class Volume(BaseModel):
    node_name: str
    path: str

    @computed_field
    @property
    def name(self) -> str:
        return f"fs://{self.node_name}{self.path}"

    @computed_field
    @property
    def uid(self) -> str:
        return get_guid(self.name, NodeTypes.K8sVolume, "")


class ExtendedProperties(NodeProperties):
    model_config = ConfigDict(extra="allow")
    node_name: str


class VolumeNode(Node):
    properties: ExtendedProperties

    @property
    def edges(self):
        return []

    @classmethod
    def from_input(cls, **kwargs) -> "VolumeNode":
        model = Volume(**kwargs)
        properties = ExtendedProperties(
            name=model.name,
            displayname=model.name,
            node_name=model.node_name,
            namespace=None,
            uid=model.uid,
        )
        node = cls(kinds=["K8sVolume"], properties=properties)
        return node
