from kubepyhound.models.entries import Node, Edge
from kubepyhound.models.k8s.pod import PodNode
from kubepyhound.models.k8s.role import RoleNode
from kubepyhound.models.k8s.cluster_role import ClusterRoleNode
from kubepyhound.models.k8s.resource import ResourceNode
from pydantic import BaseModel, ConfigDict, Field
from typing import Union

# from enum import Enum


# class NodeTypes(str, Enum):
#     K8sCluster = "K8sCluster"
#     K8sNamespace = "K8sNamespace"
#     K8sScopedRole = "K8sScopedRole"
#     K8sScopedRoleBinding = "K8sScopedRoleBinding"
#     K8sNode = "K8sNode"
#     K8sPod = "K8sPod"
#     K8sServiceAccount = "K8sServiceAccount"
#     K8sClusterRole = "K8sClusterRole"
#     K8sClusterRoleBinding = "K8sClusterRoleBinding"
#     K8sResource = "K8sResource"
#     K8sResourceGroup = "K8sResourceGroup"
#     K8sUser = "K8sUser"
#     K8sGroup = "K8sGroup"


class GraphEntries(BaseModel):
    nodes: list[Union[Node, PodNode, RoleNode, ClusterRoleNode, ResourceNode]] = []
    edges: list[Edge] = []


class CollectorProperties(BaseModel):
    model_config = ConfigDict(extra="allow")
    collection_methods: list[str] = ["Custom Method"]
    windows_server_version: str = "n/a"


class MetaDataCollector(BaseModel):
    name: str = "KubePyHound-0.0.1"
    version: str = "beta"
    properties: CollectorProperties = Field(default_factory=CollectorProperties)


class MetaData(BaseModel):
    ingest_version: str = "v1"
    collector: MetaDataCollector = Field(default_factory=MetaDataCollector)


class Graph(BaseModel):
    graph: GraphEntries
    metadata: MetaData = Field(default_factory=MetaData)
