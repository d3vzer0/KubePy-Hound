import uuid
from enum import Enum


# from kubepyhound.utils.guid import NodeTypes
class NodeTypes(str, Enum):
    K8sCluster = "K8sCluster"
    K8sNamespace = "K8sNamespace"
    K8sScopedRole = "K8sScopedRole"
    K8sScopedRoleBinding = "K8sScopedRoleBinding"
    K8sNode = "K8sNode"
    K8sPod = "K8sPod"
    K8sServiceAccount = "K8sServiceAccount"
    K8sClusterRole = "K8sClusterRole"
    K8sClusterRoleBinding = "K8sClusterRoleBinding"
    K8sResource = "K8sResource"
    K8sResourceGroup = "K8sResourceGroup"
    K8sUser = "K8sUser"
    K8sGroup = "K8sGroup"


def get_guid(
    name: str, resource_type: NodeTypes, cluster: str, namespace: str = "__global__"
) -> str:
    uuid_namespace = uuid.NAMESPACE_DNS
    # name = f"kubecluster/{cluster}/{scope}/{resource_type}/{name}"
    # print(resource_type.value, name, cluster, namespace)
    resource_path = f"{name}.{resource_type.value}.{namespace}.{cluster}"
    # print(resource_path)
    return str(uuid.uuid5(uuid_namespace, resource_path))


def get_generic_guid(
    name: str, resource_type: str, cluster: str, namespace: str = "__global__"
) -> str:
    uuid_namespace = uuid.NAMESPACE_DNS
    resource_path = f"{name}.{resource_type}.{namespace}.{cluster}"
    # print()
    return str(uuid.uuid5(uuid_namespace, resource_path))
