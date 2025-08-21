from pydantic import BaseModel, model_validator
from models.entries import Node, NodeProperties, Edge, EdgePath
from utils.guid import get_guid
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
    uid: Optional[str] = None
    api_group_name: Optional[str] = ""
    api_group_uid: Optional[str] = ""

    @model_validator(mode='after')
    def set_guid(self) -> Self:
        self.uid = get_guid(self.name, scope="system", kube_type="resource", name=self.name)
        return self


class ExtendedProperties(NodeProperties):
    kind: str
    api_group_name: Optional[str] = ""
    api_group_uid: Optional[str] = ""


class ResourceNode(Node):
    properties: ExtendedProperties

    @property
    def _resource_group_edge(self):
        if self.properties.api_group_uid:
            start_path = EdgePath(value=self.id, match_by='id')
            end_path = EdgePath(value=self.properties.api_group_uid, match_by='id')
            edge = Edge(kind='InResourceGroup', start=start_path, end=end_path)
            return edge
        else:
            return None

    @property
    def edges(self):
        resource_group_edge = [self._resource_group_edge] if self._resource_group_edge else []
        return resource_group_edge

    @classmethod
    def from_input(cls, **kwargs) -> "ResourceNode":
        model = Resource(**kwargs)
        properties = ExtendedProperties(name=model.name,
                                        displayname=model.name,
                                        # objectid=model.uid,
                                        kind=model.kind,
                                        # group=model.group,
                                        api_group_name=model.api_group_name,
                                        api_group_uid=model.api_group_uid,
                                        )
        return cls(id=model.uid, kinds=["KubeResource"], properties=properties)
