from pydantic import BaseModel
from datetime import datetime


class Spec(BaseModel):
    type: str
    selector: dict | None = None


class Metadata(BaseModel):
    name: str
    uid: str
    creation_timestamp: datetime
    labels: dict | None = None
    namespace: str


class Service(BaseModel):
    metadata: Metadata
    spec: Spec
