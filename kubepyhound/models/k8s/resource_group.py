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
    # uid: Optional[str] = None

    @computed_field
    @property
    def uid(self) -> str:
        return get_guid(self.name, NodeTypes.K8sResourceGroup, "")

    # @model_validator(mode="after")
    # def set_guid(self) -> Self:
    #     self.uid = get_guid(
    #         self.name, scope="system", kube_type="resource_group", name=self.name
    #     )
    #     return self


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
