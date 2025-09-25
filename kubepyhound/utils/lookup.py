import json
import os
import duckdb
from duckdb import DuckDBPyConnection
import glob
from typing import Dict, Any, Optional
from pathlib import Path


class LookupManager:

    def __init__(self, directory: str = "./output"):
        self.directory = directory
        self._cluster: Optional[Dict] = None
        self.db = "data"
        # self.con: DuckDBPyConnection = duckdb.connect(
        #     database="k8s.duckdb", read_only=False
        # )
        self.con: DuckDBPyConnection = duckdb.connect()

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

    def _find_resources(self, *args) -> list:
        self.con.execute(*args)
        results = self.con.fetchall()
        return results

    def nodes(self, name: str) -> str:
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
            f"SELECT metadata.uid FROM serviceaccounts WHERE metadata.name = ? AND metadata.namespace = ?",
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

    def allowed_system_resources(self, resource_type: str):
        return self._find_resources(
            f"""SELECT 
                r.metadata.name,
                r.kind,
                rd.singular_name,
                rd.name AS definition
            FROM resources r
            JOIN resource_definitions rd ON r.kind = rd.kind
            WHERE definition GLOB ?;""",
            [resource_type],
        )

    def allowed_namespaced_resources(self, resource_type: str, namespace: str):
        return self._find_resources(
            f"""SELECT 
                r.metadata.name,
                r.kind,
                rd.singular_name,
                rd.name AS definition
            FROM resources r
            JOIN resource_definitions rd ON r.kind = rd.kind
            WHERE definition GLOB ? AND metadata.namespace = ?;""",
            [resource_type, namespace],
        )

    def bootstrap(self, query_path: Path) -> None:
        bootstrap_files = glob.glob(f"{query_path}/*.sql")
        for query in bootstrap_files:
            with open(query, "r") as query_file:
                sql_content = query_file.read()
                self.con.execute(sql_content)
        self.con.close()

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
