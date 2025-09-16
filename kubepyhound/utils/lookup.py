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
        self.con.execute(*args)
        result = self.con.fetchone()
        return str(result[0]) if result else ""

    def nodes(self, name: str) -> str:
        print(name)
        self.con.execute(
            f"SELECT metadata.uid FROM nodes WHERE metadata.name = ?", [name]
        )
        result = self.con.fetchone()
        return str(result[0]) if result else ""

    def custom_resource_definitions(self, resource: str) -> str:
        return self._find_uid(
            f"SELECT uid FROM custom_resource_definitions WHERE name = ?",
            [resource],
        )

    def resource_definitions(self, resource: str) -> str:
        return self._find_uid(
            f"SELECT uid FROM resource_definitions WHERE name = ?", [resource]
        )

    def service_accounts(self, name: str, namespace: str) -> str:
        return self._find_uid(
            f"SELECT metadata.uid FROM service_accounts WHERE metadata.name = ? AND metadata.namespace = ?",
            [name, namespace],
        )

    def roles(self, name: str, namespace: str) -> str:
        return self._find_uid(
            f"SELECT metadata.uid FROM roles WHERE metadata.name = ? AND metadata.namespace = ?",
            [name, namespace],
        )

    def cluster_roles(self, name: str) -> str:
        return self._find_uid(
            f"SELECT metadata.uid FROM cluster_roles WHERE metadata.name = ?",
            [name],
        )

    def namespaces(self, name) -> str:
        return self._find_uid(
            f"SELECT metadata.uid FROM namespaces WHERE metadata.name = ?",
            [name],
        )

    def users(self, name: str) -> str:
        return self._find_uid(f"SELECT uid FROM users WHERE name = ?", [name])

    def groups(self, name: str) -> str:
        return self._find_uid(f"SELECT uid FROM groups WHERE name = ?", [name])

    def bootstrap(self) -> None:
        populate_db = [
            """CREATE TABLE IF NOT EXISTS nodes AS SELECT * FROM read_json(
                'output/nodes/*.json',
                columns = {
                    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))'
                }
            );""",
            """CREATE TABLE IF NOT EXISTS pods AS SELECT * FROM read_json(
                'output/namespaces/**/pods/*.json',
                columns = {
                    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, namespace VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
                    spec: 'STRUCT(node_name VARCHAR, service_account_name VARCHAR, containers STRUCT(image VARCHAR, security_context STRUCT(allow_privilege_escalation BOOLEAN, privileged BOOLEAN), volume_mounts STRUCT(mount_path VARCHAR, name VARCHAR)[])[])'
                }
            );""",
            """CREATE TABLE IF NOT EXISTS services AS SELECT * FROM read_json(
                'output/namespaces/**/services/*.json',
                columns = {
                    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, namespace VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
                    spec: 'STRUCT(type VARCHAR, selector MAP(VARCHAR, VARCHAR))'
                }
            );""",
            """CREATE TABLE IF NOT EXISTS serviceaccounts AS SELECT * FROM read_json(
                'output/namespaces/**/serviceaccounts/*.json',
                columns = {
                    kind: 'VARCHAR',
                    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, namespace VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
                    automount_service_account_token: 'BOOLEAN',
                    secrets: 'STRUCT(name VARCHAR)[]',
                    exists: 'BOOLEAN'
                }
            );""",
            """CREATE TABLE IF NOT EXISTS roles AS SELECT * FROM read_json(
                'output/namespaces/**/roles/*.json',
                columns = {
                    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, namespace VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
                    rules: 'STRUCT(api_groups VARCHAR[], resources VARCHAR[], verbs VARCHAR[], resource_names VARCHAR[])[]'
                }
            );""",
            """CREATE TABLE IF NOT EXISTS role_bindings AS SELECT * FROM read_json(
                'output/namespaces/**/role_bindings/*.json',
                columns = {
                    kind: 'VARCHAR',
                    subjects: 'STRUCT(api_group VARCHAR, kind VARCHAR, name VARCHAR, namespace VARCHAR)[]',
                    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, namespace VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
                    role_ref: 'STRUCT(api_group VARCHAR, kind VARCHAR, name VARCHAR)'
                }
            );""",
            """CREATE TABLE IF NOT EXISTS cluster_role_bindings AS SELECT * FROM read_json(
                'output/cluster_role_bindings/*.json',
                columns = {
                    kind: 'VARCHAR',
                    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
                    role_ref: 'STRUCT(api_group VARCHAR, kind VARCHAR, name VARCHAR)',
                    subjects: 'STRUCT(api_group VARCHAR, kind VARCHAR, name VARCHAR, namespace VARCHAR)[]'
                }
            );""",
            """CREATE TABLE IF NOT EXISTS cluster_roles AS SELECT * FROM read_json(
                'output/cluster_roles/*.json',
                columns = {
                    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))',
                    rules: 'STRUCT(api_groups VARCHAR[], resources VARCHAR[], verbs VARCHAR[], resource_names VARCHAR[])[]'
                }
            );""",
            """CREATE TABLE IF NOT EXISTS groups AS SELECT * FROM read_json(
                'output/group/*.json',
                columns = {
                    name: 'VARCHAR',
                    api_group: 'VARCHAR',
                    uid: 'VARCHAR',
                    members: 'VARCHAR[]'
                }
            );""",
            """CREATE TABLE IF NOT EXISTS users AS SELECT * FROM read_json(
                'output/user/*.json',
                columns = {
                    name: 'VARCHAR',
                    api_group: 'VARCHAR',
                    uid: 'VARCHAR',
                    groups: 'VARCHAR[]'
                }
            );""",
            """CREATE TABLE IF NOT EXISTS namespaces AS SELECT * FROM read_json(
                'output/namespaces/*.json',
                columns = {
                    metadata: 'STRUCT(name VARCHAR, uid VARCHAR, creation_timestamp VARCHAR, labels MAP(VARCHAR, VARCHAR))'
                }
            );""",
            """CREATE TABLE IF NOT EXISTS resource_definitions AS SELECT * FROM read_json(
                'output/resource_definitions/**/*.json',
                columns = {
                    name: 'VARCHAR',
                    categories: 'VARCHAR[]',
                    kind: 'VARCHAR',
                    'group': 'VARCHAR',
                    singular_name: 'VARCHAR',
                    namespaced: 'BOOLEAN',
                    uid: 'VARCHAR',
                    api_group_name: 'VARCHAR',
                    api_group_uid: 'VARCHAR'
                }
            );""",
            """CREATE TABLE IF NOT EXISTS custom_resource_definitions AS SELECT * FROM read_json(
                'output/custom_resource_definitions/**/*.json',
                columns = {
                    name: 'VARCHAR',
                    categories: 'VARCHAR[]',
                    kind: 'VARCHAR',
                    'group': 'VARCHAR',
                    singular_name: 'VARCHAR',
                    namespaced: 'BOOLEAN',
                    uid: 'VARCHAR',
                    api_group_name: 'VARCHAR',
                    api_group_uid: 'VARCHAR'
                }
            );""",
            """CREATE TABLE IF NOT EXISTS api_groups AS SELECT * FROM read_json(
                'output/api_groups/*.json',
                columns = {
                    name: 'VARCHAR',
                    api_version: 'VARCHAR',
                    preferred_version: 'STRUCT(group_version VARCHAR, version VARCHAR)',
                    versions: 'STRUCT(group_version VARCHAR, version VARCHAR)[]',
                    uid: 'VARCHAR'
                }
            );""",
        ]

        for query in populate_db:
            self.con.execute(query)

    @property
    def cluster(self) -> Dict[str, Any]:
        if self._cluster is None:
            self._cluster = self._load_json("cluster/cluster.json")
        return self._cluster

    # @property
    # def endpoint_slices(self) -> Dict[str, Any]:
    #     if self._endpoint_slices is None:
    #         self._endpoint_slices = self._load_json("endpoint-slices.json")
    #     return self._endpoint_slices
