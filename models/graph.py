from models.entries import Node, Edge
from models.k8s.pod import PodNode
from models.k8s.role import RoleNode
from models.k8s.cluster_role import ClusterRoleNode
from models.k8s.resource import ResourceNode
from pydantic import BaseModel, ConfigDict, Field
from typing import Union


class GraphEntries(BaseModel):
    nodes: list[Union[Node, PodNode, RoleNode, ClusterRoleNode, ResourceNode]] = []
    edges: list[Edge] = []


class CollectorProperties(BaseModel):
    model_config = ConfigDict(extra='allow')
    collection_methods: list[str] = ["Custom Method"]
    windows_server_version: str = "n/a"


class MetaDataCollector(BaseModel):
    name: str = "KupyHound-0.0.3"
    version: str = "beta"
    properties: CollectorProperties = Field(default_factory=CollectorProperties)


class MetaData(BaseModel):
    ingest_version: str = "v1"
    collector: MetaDataCollector = Field(default_factory=MetaDataCollector)


class Graph(BaseModel):
    graph: GraphEntries
    metadata: MetaData = Field(default_factory=MetaData)
