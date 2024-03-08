"""Test the models."""

from __future__ import annotations

import pytest
from aiohttp import ClientSession
from aresponses import ResponsesMockServer

from arnhem import (
    ODPArnhem,
    ODPArnhemNoResultsError,
    ParkingSpot,
)

from . import load_fixtures


async def test_all_locations(aresponses: ResponsesMockServer) -> None:
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
    async with ClientSession() as session:
        client = ODPArnhem(session=session)
        locations: list[ParkingSpot] = await client.locations()
        assert locations is not None
        for item in locations:
            assert isinstance(item, ParkingSpot)
            assert isinstance(item.spot_id, int)
            assert isinstance(item.parking_type, str)
            assert isinstance(item.street, str) or item.street is None
            assert item.coordinates is not None
            assert isinstance(item.coordinates, list)


async def test_wrong_filter(aresponses: ResponsesMockServer) -> None:
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
    async with ClientSession() as session:
        client = ODPArnhem(session=session)
        with pytest.raises(ODPArnhemNoResultsError):
            await client.locations(set_filter="wrong=filter")


async def test_incorrect_filter(aresponses: ResponsesMockServer) -> None:
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
    async with ClientSession() as session:
        client = ODPArnhem(session=session)
        with pytest.raises(ODPArnhemNoResultsError):
            await client.locations(set_filter="incorrect")
