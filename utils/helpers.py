import typer
import json
from pathlib import Path
from functools import wraps
from enum import Enum
from pydantic import BaseModel


class OutputFormat(str, Enum):
    json = "json"
    ndjson = "ndjson"


def load_json(input_file: str):
    with open(input_file, "r") as f:
        json_object = json.loads(f.read())
    return json_object


class DumpClient:
    def __init__(self, base_dir: Path, mode: OutputFormat = OutputFormat.json):
        self.base_dir = Path(base_dir).resolve()
        self._writer = {
            OutputFormat.json: self._to_json,
            OutputFormat.ndjson: self._to_ndjson,
        }[mode]

    def write(
        self, data: BaseModel, name: str, resource: str, namespace: str | None = None
    ) -> None:
        self._writer(data, name, resource, namespace)

    def _to_json(
        self, data: BaseModel, name: str, resource: str, namespace: str | None = None
    ):
        output_path = (
            self.base_dir / "namespaces" / namespace / resource / f"{name}.json"
            if namespace
            else self.base_dir / resource / f"{name}.json"
        )
        resolved_path = output_path.resolve()
        if not resolved_path.is_relative_to(self.base_dir):
            raise Exception(
                f"Filename {output_path} is not in {self.base_dir} directory"
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as file_obj:
            file_obj.write(data.model_dump_json(indent=2))

    def _to_ndjson(
        self, data: BaseModel, name: str, resource: str, namespace: str | None = None
    ):
        output_file = self.base_dir / f"{resource}.ndjson"
        with open(output_file, "a") as file_obj:
            file_obj.write(f"{data.model_dump_json().replace("\n", "")}\n")


def process_stale_refs(resource_type: str, output_dir: str = "./output"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            stale_refs = func(*args, **kwargs)
            typer.echo(
                f"Processing {len(stale_refs)} stale references for {resource_type}"
            )
            for stale_ref in stale_refs:
                stale_path = (
                    f"{output_dir}/stale_objects/{resource_type}/{stale_ref.name}.json"
                )
                out_path = Path(stale_path)
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with open(stale_path, "w") as file_obj:
                    file_obj.write(stale_ref.model_dump_json())
            return stale_refs

        return wrapper

    return decorator
