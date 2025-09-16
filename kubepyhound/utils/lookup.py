import json
import os
from typing import Dict, Any, Optional
import duckdb


class LookupManager:

    def __init__(self, directory: str = "./output"):
        self.directory = directory
        self._cluster: Optional[Dict] = None
        self.db = "data"
        self.con = duckdb.connect(database="k8s.duckdb", read_only=False)

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

    def bootstrap(self) -> None:
        populate_db = [
            "CREATE TABLE IF NOT EXISTS pods AS SELECT * FROM read_json('output/namespaces/**/pods/*.json', columns = {metadata: 'JSON', spec: 'JSON'});",
            "CREATE TABLE IF NOT EXISTS services AS SELECT * FROM read_json('output/namespaces/**/services/*.json', columns = {metadata: 'JSON', spec: 'JSON'});",
            "CREATE TABLE IF NOT EXISTS serviceaccounts AS SELECT * FROM read_json('output/namespaces/**/serviceaccounts/*.json', columns = {metadata: 'JSON', spec: 'JSON', exists: 'BOOLEAN'});",
            "CREATE TABLE IF NOT EXISTS nodes AS SELECT * FROM read_json('output/nodes/*.json', columns = {metadata: 'JSON'});",
            "CREATE TABLE IF NOT EXISTS roles AS SELECT * FROM read_json('output/namespaces/**/roles/*.json', columns = {metadata: 'JSON', rules: 'JSON'});",
            "CREATE TABLE IF NOT EXISTS role_bindings AS SELECT * FROM read_json('output/namespaces/**/role_bindings/*.json', columns = {metadata: 'JSON', subjects: 'JSON', role_ref: 'JSON'});",
            "CREATE TABLE IF NOT EXISTS cluser_role_bindings AS SELECT * FROM read_json('output/cluster_role_bindings/*.json', columns = {metadata: 'JSON', subjects: 'JSON', role_ref: 'JSON'});",
            "CREATE TABLE IF NOT EXISTS cluster_roles AS SELECT * FROM read_json('output/cluster_role_bindings/*.json', columns = {metadata: 'JSON', rules: 'JSON'});",
            "CREATE TABLE IF NOT EXISTS groups AS SELECT * FROM read_json('output/group/*.json', columns = {name: 'VARCHAR', api_group: 'VARCHAR', uid: 'VARCHAR', members: 'JSON'});",
            "CREATE TABLE IF NOT EXISTS users AS SELECT * FROM read_json('output/user/*.json', columns = {name: 'VARCHAR', api_group: 'VARCHAR', uid: 'VARCHAR', groups: 'JSON'});",
            "CREATE TABLE IF NOT EXISTS namespaces AS SELECT * FROM read_json('output/namespaces/*.json', columns = {metadata: 'JSON'});",
            "CREATE TABLE IF NOT EXISTS resource_definitions AS SELECT * FROM read_json('output/resource_definitions/**/*.json', columns = {name: 'VARCHAR', kind: 'VARCHAR', namespaced: 'BOOLEAN', uid: 'VARCHAR', api_group_name: 'VARCHAR', api_group_uid: 'VARCHAR', singular_name: 'VARCHAR'});",
            "CREATE TABLE IF NOT EXISTS custom_resource_definitions AS SELECT * FROM read_json('output/custom_resource_definitions/**/*.json', columns = {name: 'VARCHAR', kind: 'VARCHAR', namespaced: 'BOOLEAN', uid: 'VARCHAR', api_group_name: 'VARCHAR', api_group_uid: 'VARCHAR', singular_name: 'VARCHAR'});",
            "CREATE TABLE IF NOT EXISTS api_groups AS SELECT * FROM read_json('output/api_groups/*.json', columns = {name: 'VARCHAR', uid: 'VARCHAR', api_version: 'VARCHAR', preferred_version: 'JSON', versions: 'JSON'});",
        ]
        for query in populate_db:
            self.con.execute(query)

    @property
    def cluster(self) -> Dict[str, Any]:
        if self._cluster is None:
            self._cluster = self._load_json("clusters/cluster.json")
        return self._cluster

    # @property
    # def endpoint_slices(self) -> Dict[str, Any]:
    #     if self._endpoint_slices is None:
    #         self._endpoint_slices = self._load_json("endpoint-slices.json")
    #     return self._endpoint_slices
