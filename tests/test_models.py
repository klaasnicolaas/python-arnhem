"""Test the models."""

from __future__ import annotations

import pytest
from aresponses import ResponsesMockServer
from syrupy.assertion import SnapshotAssertion

from arnhem import (
    ODPArnhem,
    ODPArnhemNoResultsError,
    ParkingSpot,
)

from . import load_fixtures


async def test_all_locations(
    aresponses: ResponsesMockServer,
    snapshot: SnapshotAssertion,
    odp_arnhem_client: ODPArnhem,
) -> None:
    """Test the parking locations model."""
    aresponses.add(
        "geo.arnhem.nl",
        "/arcgis/rest/services/OpenData/Parkeervakken/MapServer/0/query",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("e6a_parking.json"),
        ),
    )
    locations: list[ParkingSpot] = await odp_arnhem_client.locations()
    assert locations == snapshot


async def test_wrong_filter(
    aresponses: ResponsesMockServer,
    odp_arnhem_client: ODPArnhem,
) -> None:
    """Test when a wrong filter is provided."""
    aresponses.add(
        "geo.arnhem.nl",
        "/arcgis/rest/services/OpenData/Parkeervakken/MapServer/0/query",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("wrong_filter.json"),
        ),
    )
    with pytest.raises(ODPArnhemNoResultsError):
        await odp_arnhem_client.locations(set_filter="wrong=filter")


async def test_incorrect_filter(
    aresponses: ResponsesMockServer,
    odp_arnhem_client: ODPArnhem,
) -> None:
    """Test when an incorrect filter is provided."""
    aresponses.add(
        "geo.arnhem.nl",
        "/arcgis/rest/services/OpenData/Parkeervakken/MapServer/0/query",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixtures("incorrect_filter.json"),
        ),
    )
    with pytest.raises(ODPArnhemNoResultsError):
        await odp_arnhem_client.locations(set_filter="incorrect")
