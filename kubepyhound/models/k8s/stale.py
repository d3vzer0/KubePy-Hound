from kubepyhound.models.entries import (
    Node,
    NodeProperties,
    StaleReference,
    EdgePath,
    Edge,
)


class ExtendedProperties(NodeProperties):
    source_ref: str
    source_edge_type: str


class StaleNode(Node):
    properties: ExtendedProperties

    @property
    def _source_refs(self):
        start_path = EdgePath(value=self.properties.source_ref, match_by="id")
        end_path = EdgePath(value=self.id, match_by="id")
        edge = Edge(
            kind=self.properties.source_edge_type,
            start=start_path,
            end=end_path,
            properties={"stale": True},
        )
        return edge

    @property
    def edges(self):
        return [self._source_refs]

    @classmethod
    def from_input(cls, **kwargs) -> "StaleNode":
        model = StaleReference(**kwargs)
        properties = ExtendedProperties(
            name=model.name,
            displayname=model.name,
            exists=False,
            source_ref=model.source_ref.uid,
            source_edge_type=model.edge_type,
        )
        return cls(kinds=[model.resource_type], properties=properties)
