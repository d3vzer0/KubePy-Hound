import json
import os
from typing import Dict, Any, Optional
import duckdb


class LookupManager:

    def __init__(self, directory: str = "./output"):
        self.directory = directory
        self._cluster: Optional[Dict] = None
        self.db = "data"
        self.con = duckdb.connect(database="data.duckdb", read_only=True)

    def _load_json(self, filename: str) -> Dict[str, Any]:
        filepath = os.path.join(self.directory, filename)
        if not os.path.exists(filepath):
            return {}
        with open(filepath, "r") as f:
            return json.load(f)

    def _find_uid(self, *args) -> str:
        self.con.execute(args)
        result = self.con.fetchone()
        return str(result[0]) if result else ""

    def nodes(self, name: str) -> str:
        return self._find_uid(
            f"SELECT metadata.uid FROM {self.db}.nodes WHERE metadata.name = ?", [name]
        )

    def custom_resource_definitions(self, resource: str) -> str:
        return self._find_uid(
            f"SELECT uid FROM {self.db}.custom_resource_definitions WHERE name = ?",
            [resource],
        )

    def resource_definitions(self, resource: str) -> str:
        return self._find_uid(
            f"SELECT uid FROM {self.db}.resource_definitions WHERE name = ?", [resource]
        )

    def service_accounts(self, name: str, namespace: str) -> str:
        return self._find_uid(
            f"SELECT metadata.uid FROM {self.db}.service_accounts WHERE metadata.name = ? AND metadata.namespace = ?",
            [name, namespace],
        )

    def roles(self, name: str, namespace: str) -> str:
        return self._find_uid(
            f"SELECT metadata.uid FROM {self.db}.roles WHERE metadata.name = ? AND metadata.namespace = ?",
            [name, namespace],
        )

    def cluster_roles(self, name: str) -> str:
        return self._find_uid(
            f"SELECT metadata.uid FROM {self.db}.cluster_roles WHERE metadata.name = ?",
            [name],
        )

    def namespaces(self, name) -> str:
        return self._find_uid(
            f"SELECT metadata.uid FROM {self.db}.namespaces WHERE metadata.name = ?",
            [name],
        )

    def users(self, name: str) -> str:
        return self._find_uid(f"SELECT uid FROM {self.db}.users WHERE name = ?", [name])

    def groups(self, name: str) -> str:
        return self._find_uid(
            f"SELECT uid FROM {self.db}.groups WHERE name = ?", [name]
        )

    @property
    def cluster(self) -> Dict[str, Any]:
        if self._cluster is None:
            self._cluster = self._load_json("cluster.json")
        return self._cluster

    # @property
    # def endpoint_slices(self) -> Dict[str, Any]:
    #     if self._endpoint_slices is None:
    #         self._endpoint_slices = self._load_json("endpoint-slices.json")
    #     return self._endpoint_slices
