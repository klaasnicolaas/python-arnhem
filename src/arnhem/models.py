"""Models for Open Data Platform of Arnhem."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class ParkingSpot:
    """Object representing a parking spot."""

    spot_id: int
    parking_type: str
    street: str
    traffic_sign: str

    neighborhood: str
    neighborhood_code: str
    district: str
    district_code: str
    area: str

    coordinates: list[float]

    @classmethod
    def from_json(cls: type[ParkingSpot], data: dict[str, Any]) -> ParkingSpot:
        """Return a ParkingSpot object from a JSON dictionary.

        Args:
        ----
            data: The JSON data from the API.

        Returns:
        -------
            A ParkingSpot object.

        """
        attr = data["attributes"]
        geo = data["geometry"].get("rings")[0]
        return cls(
            spot_id=attr["OBJECTID"],
            parking_type=attr["SOORT"],
            street=attr["STRAAT"],
            traffic_sign=attr["RVV_SOORT"],
            neighborhood=attr["BUURTNAAM"],
            neighborhood_code=attr["BUURTCODE"],
            district=attr["WIJKNAAM"],
            district_code=attr["WIJKCODE"],
            area=attr["GEBIED"],
            coordinates=geo,
        )


@dataclass
class ParkingRecord:
    """An original asset ID, full WGS84 geometry and all source claims."""

    spot_id: int
    object_id: int
    geometry: dict[str, Any]
    source_attributes: dict[str, Any]

    @classmethod
    def from_geojson(cls, feature: dict[str, Any]) -> ParkingRecord:
        """Validate identity and polygon positions without discarding any rings."""
        attributes = feature["properties"]
        asset_id, object_id = attributes["ID"], attributes["OBJECTID"]
        for value in (asset_id, object_id):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                msg = "Invalid Arnhem record identity"
                raise ValueError(msg)
        if feature.get("type") != "Feature" or feature.get("id") != object_id:
            msg = "Arnhem feature ID differs from OBJECTID"
            raise ValueError(msg)
        geometry = feature["geometry"]
        if not isinstance(geometry, dict):
            msg = "Missing Arnhem geometry"
            raise TypeError(msg)
        cls._validate_geometry(geometry)
        return cls(asset_id, object_id, geometry, attributes.copy())

    @staticmethod
    def _validate_geometry(geometry: dict[str, Any]) -> None:
        """Check all Polygon and MultiPolygon positions in WGS84."""
        coordinates = geometry.get("coordinates")
        if geometry.get("type") == "Polygon":
            polygons = [coordinates]
        elif geometry.get("type") == "MultiPolygon":
            polygons = coordinates
        else:
            msg = "Expected an Arnhem Polygon or MultiPolygon"
            raise ValueError(msg)
        if not isinstance(polygons, list) or not polygons:
            msg = "Empty Arnhem geometry"
            raise ValueError(msg)
        for polygon in polygons:
            if not isinstance(polygon, list) or not polygon:
                msg = "Empty Arnhem polygon"
                raise ValueError(msg)
            for ring in polygon:
                if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
                    msg = "Invalid Arnhem polygon ring"
                    raise ValueError(msg)
                for point in ring:
                    if not isinstance(point, list) or len(point) != 2:
                        msg = "Invalid Arnhem position"
                        raise ValueError(msg)
                    for value, bound in zip(point, (180, 90), strict=True):
                        if (
                            isinstance(value, bool)
                            or not isinstance(value, (int, float))
                            or not math.isfinite(value)
                            or not -bound <= value <= bound
                        ):
                            msg = "Invalid Arnhem WGS84 coordinate"
                            raise ValueError(msg)


@dataclass
class ParkingCollection:
    """A selection verified against independent counts and original object IDs."""

    records: list[ParkingRecord]
    total_count: int
    pages_fetched: int
    complete: bool = True
