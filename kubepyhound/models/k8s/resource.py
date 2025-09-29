from pydantic import BaseModel, model_validator, computed_field
from kubepyhound.models.entries import Node, NodeProperties, Edge, EdgePath
from kubepyhound.utils.guid import get_guid, NodeTypes
from typing_extensions import Self
from typing import Optional


class Resource(BaseModel):
    name: str
    categories: Optional[list[str]] = []
    kind: str
    group: Optional[str] = None
    singular_name: str
    name: str
    namespaced: bool = False
    # uid: Optional[str] = None
    api_group_name: Optional[str] = ""
    api_group_uid: Optional[str] = ""

    @computed_field
    @property
    def uid(self) -> str:
        return get_guid(self.name, NodeTypes.K8sResource, "")

    # @model_validator(mode="after")
    # def set_guid(self) -> Self:
    #     self.uid = get_guid(
    #         self.name, scope="system", kube_type="resource", name=self.name
    #     )
    #     return self


class ExtendedProperties(NodeProperties):
    kind: str
    api_group_name: Optional[str] = ""
    api_group_uid: Optional[str] = ""


class ResourceNode(Node):
    properties: ExtendedProperties

    @property
    def _resource_group_edge(self):
        if self.properties.api_group_name:
            target_id = get_guid(
                self.properties.api_group_name,
                NodeTypes.K8sResourceGroup,
                self._cluster,
            )
            start_path = EdgePath(value=self.id, match_by="id")
            end_path = EdgePath(value=target_id, match_by="id")
            edge = Edge(kind="K8sInResourceGroup", start=start_path, end=end_path)
            return edge
        else:
            return None

    @property
    def edges(self):
        resource_group_edge = (
            [self._resource_group_edge] if self._resource_group_edge else []
        )
        return resource_group_edge

    @classmethod
    def from_input(cls, **kwargs) -> "ResourceNode":
        model = Resource(**kwargs)
        properties = ExtendedProperties(
            name=model.name,
            displayname=model.name,
            kind=model.kind,
            namespace=None,
            api_group_name=model.api_group_name,
            api_group_uid=model.api_group_uid,
            uid=model.uid,
        )
        return cls(kinds=["K8sResource"], properties=properties)


class CustomResourceNode(Node):
    properties: ExtendedProperties

    @property
    def _resource_group_edge(self):
        if self.properties.api_group_name:
            target_id = get_guid(
                self.properties.api_group_name,
                NodeTypes.K8sResourceGroup,
                self._cluster,
            )
            start_path = EdgePath(value=self.id, match_by="id")
            end_path = EdgePath(value=target_id, match_by="id")
            edge = Edge(kind="K8sInResourceGroup", start=start_path, end=end_path)
            return edge
        else:
            return None

    @property
    def edges(self):
        resource_group_edge = (
            [self._resource_group_edge] if self._resource_group_edge else []
        )
        return resource_group_edge

    @classmethod
    def from_input(cls, **kwargs) -> "CustomResourceNode":
        model = Resource(**kwargs)
        properties = ExtendedProperties(
            name=model.name,
            displayname=model.name,
            namespace=None,
            kind=model.kind,
            api_group_name=model.api_group_name,
            api_group_uid=model.api_group_uid,
            uid=model.uid,
        )
        return cls(kinds=["K8sResource"], properties=properties)
