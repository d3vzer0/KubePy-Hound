from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class TargetRef(BaseModel):
    api_version: str | None = None
    field_path: str | None = None
    name: str
    namespace: str
    uid: str


class Endpoint(BaseModel):
    target_ref: TargetRef | None = None


class Labels(BaseModel):
    model_config = ConfigDict(extra='allow')
    service_name: str = Field(alias="kubernetes.io/service-name")


class Metadata(BaseModel):
    name: str
    uid: str
    creation_timestamp: datetime
    labels: Labels
    namespace: str


class EndpointSlice(BaseModel):
    address_type: str
    metadata: Metadata
    endpoints: list[Endpoint]
