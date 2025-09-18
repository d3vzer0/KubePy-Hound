from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator
from abc import ABC, abstractmethod
from typing import Optional
from kubepyhound.utils.guid import get_guid
from datetime import datetime
from kubepyhound.utils.lookup import LookupManager


class SourceRef(BaseModel):
    name: str
    uid: str


class StaleReference(BaseModel):
    resource_type: str
    namespace: Optional[str] = None
    name: str
    source_ref: SourceRef
    edge_type: str
    uid: str | None = None

    @model_validator(mode="after")
    def set_guid(self) -> "StaleReference":
        self.uid = get_guid(
            self.name,
            scope="system/{source_ref}",
            kube_type="serviceaccount",
            name=self.name,
        )
        return self


class StaleReferenceCollector(BaseModel):
    stale_refs: list[StaleReference] = Field(default_factory=list)

    def add(self, ref: StaleReference):
        self.stale_refs.append(ref)

    @property
    def unique(self) -> dict[str, StaleReference]:
        unique = {}
        for ref in self.stale_refs:
            if ref.uid not in unique:
                unique[ref.uid] = ref
        return unique


class NodeProperties(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    displayname: str
    exists: bool = True
    last_seen: datetime = Field(default_factory=datetime.now)


class Node(BaseModel, ABC):
    model_config = ConfigDict(extra="allow")
    id: str
    kinds: list[str]
    properties: NodeProperties
    _stale_collection: StaleReferenceCollector = PrivateAttr(
        default_factory=StaleReferenceCollector
    )
    _lookup: LookupManager = PrivateAttr()

    @classmethod
    @abstractmethod
    def from_input(cls, **kwargs) -> "Node": ...

    @property
    @abstractmethod
    def edges(self) -> list["Edge"]: ...

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.lookup = Field(exclude=True)


class EdgePath(BaseModel):
    value: str
    match_by: str


class EdgeProperties(BaseModel):
    model_config = ConfigDict(extra="allow")
    composed: bool = False


class Edge(BaseModel):
    kind: str
    start: EdgePath
    end: EdgePath
    properties: EdgeProperties = Field(default_factory=EdgeProperties)
