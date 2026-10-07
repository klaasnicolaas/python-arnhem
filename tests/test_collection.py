"""Verify full Arnhem selection retrieval and lossless source records."""

from copy import deepcopy
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from arnhem import ODPArnhem, ODPArnhemError, ParkingRecord


def feature(object_id: int = 1, asset_id: int = 1001) -> dict[str, Any]:
    """Small GeoJSON source record with an interior polygon ring."""
    return {
        "type": "Feature",
        "id": object_id,
        "properties": {
            "OBJECTID": object_id,
            "ID": asset_id,
            "RVV_SOORT": "E6a",
            "STRAAT": None,
            "BORD": "bezoekers",
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[5.9, 52], [5.91, 52], [5.91, 52.01], [5.9, 52]],
                [[5.901, 52.001], [5.902, 52.001], [5.902, 52.002], [5.901, 52.001]],
            ],
        },
    }


def ids(*values: int) -> dict[str, Any]:
    """Represent the unlimited object ID response."""
    return {"objectIdFieldName": "OBJECTID", "objectIds": list(values)}


def page(*features: dict[str, Any]) -> dict[str, Any]:
    """Represent a WGS84 GeoJSON batch."""
    return {"type": "FeatureCollection", "features": list(features)}


async def test_complete_batches_preserve_asset_identity_and_all_rings() -> None:
    """Order by original IDs, verify counts twice, preserve every source claim."""
    first, second = feature(), feature(2, 1002)
    request = AsyncMock(
        side_effect=[
            {"count": 2},
            ids(2, 1),
            page(first),
            page(second),
            {"count": 2},
            ids(1, 2),
        ]
    )
    with patch.object(ODPArnhem, "_request", request):
        result = await ODPArnhem().parking_collection("RVV_SOORT='E6a'", page_size=1)
    assert result.total_count == 2
    assert result.pages_fetched == 2
    assert result.complete
    assert [item.spot_id for item in result.records] == [1001, 1002]
    assert result.records[0].geometry == first["geometry"]
    assert result.records[0].source_attributes == first["properties"]
    params = request.call_args_list[2].kwargs["params"]
    assert params["objectIds"] == "1"
    assert params["where"] == "RVV_SOORT='E6a'"
    assert params["outSR"] == "4326"


@pytest.mark.parametrize(
    "responses",
    [
        [{"error": {"code": 400}}],
        [None],
        [{"count": True}, ids(1)],
        [{"count": -1}, ids()],
        [{"count": 2}, ids(1, 1)],
        [{"count": 1}, ids(True)],  # noqa: FBT003 - invalid source ID
        [{"count": 1}, {"objectIdFieldName": "ID", "objectIds": [1]}],
        [{"count": 2}, ids(1)],
        [{"count": 1}, ids(1), page()],
        [{"count": 1}, ids(1), {**page(feature()), "exceededTransferLimit": True}],
        [{"count": 1}, ids(1), {**page(feature()), "crs": {}}],
        [{"count": 1}, ids(1), page(feature(2))],
        [{"count": 2}, ids(1, 2), page(feature(), feature(2))],
        [{"count": 1}, ids(1), page(feature()), {"count": 1}, ids(2)],
        [{"count": 1}, ids(1), page(feature()), {"count": 2}, ids(1)],
        [{"count": 1}, ids(1), page({**feature(), "geometry": None})],
    ],
)
async def test_invalid_or_changed_selection_fails(responses: list[Any]) -> None:
    """Never return a partial collection after source errors or changed IDs."""
    with (
        patch.object(ODPArnhem, "_request", AsyncMock(side_effect=responses)),
        pytest.raises(ODPArnhemError),
    ):
        await ODPArnhem().parking_collection()


async def test_collection_limit_and_empty_selection() -> None:
    """An empty source remains explicit; an oversized source fails."""
    with patch.object(
        ODPArnhem,
        "_request",
        AsyncMock(
            side_effect=[
                {"count": 0},
                ids(),
                {"count": 0},
                ids(),
            ]
        ),
    ):
        result = await ODPArnhem().parking_collection()
    assert result.total_count == 0
    assert result.records == []
    assert result.pages_fetched == 0
    with (
        patch.object(
            ODPArnhem,
            "_request",
            AsyncMock(
                side_effect=[
                    {"count": 2},
                    ids(1, 2),
                ]
            ),
        ),
        pytest.raises(ODPArnhemError, match="limit"),
    ):
        await ODPArnhem().parking_collection(max_records=1)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"page_size": 0},
        {"page_size": 2001},
        {"page_size": True},
        {"max_records": 0},
        {"max_records": True},
    ],
)
async def test_invalid_limits(kwargs: dict[str, Any]) -> None:
    """Reject invalid arguments before any HTTP request."""
    with pytest.raises(ValueError, match="limits"):
        await ODPArnhem().parking_collection(**kwargs)


@pytest.mark.parametrize(
    "change",
    [
        {"type": "Point", "coordinates": [5.9, 52]},
        {"type": "Polygon", "coordinates": []},
        {"type": "Polygon", "coordinates": [[]]},
        {"type": "Polygon", "coordinates": [[[5.9, 52]]]},
        {"type": "Polygon", "coordinates": [[[True, 52]] * 4]},
        {"type": "Polygon", "coordinates": [[[5.9, float("nan")]] * 4]},
        {"type": "Polygon", "coordinates": [[[5.9, 91]] * 4]},
        {"type": "Polygon", "coordinates": [[[5.9]] * 4]},
        {
            "type": "Polygon",
            "coordinates": [[[5.9, 52], [5.9, 52], [5.9, 52], [5.91, 52]]],
        },
    ],
)
def test_invalid_geometry(change: dict[str, Any]) -> None:
    """Reject invalid WGS84 positions and unclosed rings."""
    with pytest.raises(ValueError, match="Arnhem"):
        ParkingRecord.from_geojson({**feature(), "geometry": change})


@pytest.mark.parametrize(
    ("field", "value"),
    [("ID", None), ("ID", True), ("ID", 0), ("OBJECTID", "1"), ("OBJECTID", -1)],
)
def test_invalid_source_ids(field: str, value: object) -> None:
    """Do not coerce missing, boolean or string IDs."""
    source = feature()
    source["properties"][field] = value
    with pytest.raises(ValueError, match="Arnhem"):
        ParkingRecord.from_geojson(source)


def test_multipolygon_keeps_every_polygon_and_rejects_wrapper_mismatch() -> None:
    """Do not truncate multipolygons or substitute the GeoJSON wrapper ID."""
    source = deepcopy(feature())
    source["geometry"] = {
        "type": "MultiPolygon",
        "coordinates": [
            source["geometry"]["coordinates"],
            source["geometry"]["coordinates"],
        ],
    }
    assert ParkingRecord.from_geojson(source).geometry == source["geometry"]
    source["id"] = 2
    with pytest.raises(ValueError, match="OBJECTID"):
        ParkingRecord.from_geojson(source)
