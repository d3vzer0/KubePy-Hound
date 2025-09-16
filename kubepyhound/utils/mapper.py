from kubernetes import client, config, dynamic
from kubernetes.client.rest import ApiException
from kubernetes.dynamic.resource import Resource, ResourceList
from kubepyhound.models.k8s.dynamic import DynamicResource
from kubepyhound.models.k8s.role import Rule, Role
from pathlib import Path
import glob
import json

__BUILTIN_NODES__ = [
    "Pod",
    "ClusterRole",
    "ClusterRoleBinding",
    "Role",
    "RoleBinding",
    "Namespace",
    "Node",
    "Service",
    "ServiceAccount",
]


class NamespaceResourceMapper:
    def __init__(self, api_resources_path):
        config.load_kube_config()
        self.api_client = client.ApiClient()
        self.dyn_client = dynamic.DynamicClient(self.api_client)
        self.api_resources_path = Path(api_resources_path)
        # Load local CRD definitions
        self.api_groups = {}
        self.resource_types = {}

    def _get_all_resources(self, api_group: str, namespace: str) -> list:
        resource_list = []
        # Search the unique resource types for the specified API group and iterate
        # over each available resource. This does not yet show if the resource is actually
        # used yet, just which are available
        # TODO: maybe replace this loop based on the previously dumped lookup
        # if api_group not in self.resource_types:
        search_resource_types = self.dyn_client.resources.search(group=api_group)
        # self.resource_types[api_group] = search_resource_types
        # else:
        # search_resource_types = self.resource_types[api_group]

        # test2 = self.dyn_client.resources.search()
        unique_resource_types = {}
        for resource_type in search_resource_types:
            unique_resource_types[resource_type.name] = resource_type

        # print(len(unique_resource_types))
        for resource_key, resource_type in unique_resource_types.items():
            if resource_type.verbs and "list" in resource_type.verbs:
                # Normally the API group is empty for the core k8s resources,
                # though I saved them into the "__core__" group to categorize
                # the different resource types (ie. core vs custom) internally
                api_group_key = api_group if api_group != "" else "__core__"
                version_lookup = self.api_groups[api_group_key]

                # Based on the previously dumped lookup file, get the prefered version
                api_group_version = version_lookup["preferred_version"]["group_version"]
                try:
                    # Initiallise the API and specify which resource to fetch
                    api = self.dyn_client.resources.get(
                        api_version=api_group_version, name=resource_type.name
                    )
                    # Now find the deployed resource in the specified namespace
                    get_resource = api.get(namespace=namespace)
                    for resource in get_resource.to_dict()["items"]:
                        resource_list.append(resource)

                except Exception as err:
                    pass
        return resource_list

    def discover_resources_for_rule(self, rule: Rule, namespace: str) -> list:
        resource_list = []
        for api_group in rule.api_groups:
            api_group = api_group if api_group != "__core__" else ""
            for resource_type in rule.resources:
                if resource_type == "*":
                    resource_list = self._get_all_resources(api_group, namespace)

        return resource_list
