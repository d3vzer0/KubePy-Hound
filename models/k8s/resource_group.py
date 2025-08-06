from pydantic import BaseModel, model_validator
from models.entries import Node, NodeProperties, Edge, EdgePath
from utils.guid import get_guid
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
    uid: Optional[str] = None

    @model_validator(mode='after')
    def set_guid(self) -> Self:
        self.uid = get_guid(self.name, scope="system", kube_type="resource_group", name=self.name)
        return self


class ResourceGroupNode(Node):

    @property
    def edges(self):
        return []

    @classmethod
    def from_input(cls, **kwargs) -> "ResourceGroupNode":
        model = ResourceGroup(**kwargs)
        properties = NodeProperties(name=model.name, displayname=model.name)
        return cls(id=model.uid, kinds=["KubeResourceGroup"], properties=properties)
