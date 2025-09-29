from pydantic import BaseModel, model_validator, computed_field
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from kubepyhound.utils.guid import get_guid, NodeTypes
from typing_extensions import Self
from typing import Optional


class GroupVersion(BaseModel):
    group_version: str
    version: str


class ResourceGroup(BaseModel):
    name: str
    api_version: Optional[str] = None
    preferred_version: GroupVersion
    versions: list[GroupVersion]

    @computed_field
    @property
    def uid(self) -> str:
        return get_guid(self.name, NodeTypes.K8sResourceGroup, "")


class ResourceGroupNode(Node):

    @property
    def edges(self):
        return []

    @classmethod
    def from_input(cls, **kwargs) -> "ResourceGroupNode":
        model = ResourceGroup(**kwargs)
        properties = NodeProperties(
            name=model.name, displayname=model.name, uid=model.uid, namespace=None
        )
        return cls(kinds=["K8sResourceGroup"], properties=properties)
