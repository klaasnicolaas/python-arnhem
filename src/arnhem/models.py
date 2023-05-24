"""Models for Open Data Platform of Arnhem."""
from __future__ import annotations

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
