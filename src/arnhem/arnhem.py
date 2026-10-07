"""Asynchronous Python client providing Open Data information of Arnhem."""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from importlib import metadata
from typing import Any, Self

from aiohttp import ClientError, ClientSession
from aiohttp.hdrs import METH_GET
from yarl import URL

from .exceptions import (
    ODPArnhemConnectionError,
    ODPArnhemError,
    ODPArnhemNoResultsError,
)
from .models import ParkingCollection, ParkingSpot

VERSION: str = metadata.version("arnhem")


@dataclass
class ODPArnhem:
    """Main class for handling data fetchting from Open Data Platform of Arnhem."""

    request_timeout: float = 10.0
    session: ClientSession | None = None

    _close_session: bool = False

    async def _request(
        self,
        uri: str,
        *,
        method: str = METH_GET,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Handle a request to the Open Data Platform API of Arnhem.

        Args:
        ----
            uri: Request URI, without '/', for example, 'status'
            method: HTTP method to use, for example, 'GET'
            params: Extra options to improve or limit the response.

        Returns:
        -------
            A Python dictionary with the response from
            the Open Data Platform API of Arnhem.

        Raises:
        ------
            ODPArnhemConnectionError: An error occurred while
                communicating with the Open Data Platform API of Arnhem.
            ODPArnhemError: Received an unexpected response from
                the Open Data Platform API of Arnhem.

        """
        url = URL.build(
            scheme="https",
            host="geo.arnhem.nl",
            path="/arcgis/rest/services/",
        ).join(
            URL(uri),
        )

        headers = {
            "Accept": "application/json",
            "User-Agent": f"PythonODPArnhem/{VERSION}",
        }

        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        try:
            async with asyncio.timeout(self.request_timeout):
                response = await self.session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    ssl=True,
                )
                response.raise_for_status()
        except TimeoutError as exception:
            msg = "Timeout occurred while connecting to the Open Data Platform API."
            raise ODPArnhemConnectionError(msg) from exception
        except (ClientError, socket.gaierror) as exception:
            msg = "Error occurred while communicating with the Open Data Platform API."
            raise ODPArnhemConnectionError(msg) from exception

        content_type = response.headers.get("Content-Type", "")
        if not any(
            kind in content_type
            for kind in ("application/json", "application/geo+json")
        ):
            text = await response.text()
            msg = "Unexpected content type response from the Open Data Platform API."
            raise ODPArnhemError(msg, {"Content-Type": content_type, "response": text})

        return await response.json()

    async def locations(
        self,
        limit: int = 10,
        set_filter: str = "1=1",
    ) -> list[ParkingSpot]:
        """Get all the parking locations.

        Args:
        ----
            limit: The number of results to return.
            filter: A filter to apply to the results.

        Returns:
        -------
            A list of ParkingSpot objects.

        """
        msg: str = "No results found, check your filter."
        locations = await self._request(
            "OpenData/Parkeervakken/MapServer/0/query",
            params={
                "where": set_filter,
                "outFields": "*",
                "outSR": "4326",
                "f": "json",
                "resultRecordCount": limit,
            },
        )

        try:
            results: list[ParkingSpot] = [
                ParkingSpot.from_json(item) for item in locations["features"]
            ]
        except KeyError as exception:
            # when wrong filter is given
            raise ODPArnhemNoResultsError(msg) from exception

        # when filter is incorrect/empty
        if locations["features"] == []:
            raise ODPArnhemNoResultsError(msg)
        return results

    async def _collection_query(self, params: dict[str, Any]) -> dict[str, Any]:
        """Reject ArcGIS errors even when the server returns HTTP 200."""
        response = await self._request(
            "OpenData/Parkeervakken/MapServer/0/query", params=params
        )
        if not isinstance(response, dict) or "error" in response:
            msg = "Invalid Arnhem query response"
            raise ODPArnhemError(msg)
        return response

    async def _selection_ids(self, set_filter: str) -> set[int]:
        """Compare an unlimited ID query with the independent selection count."""
        count_response = await self._collection_query(
            {"where": set_filter, "returnCountOnly": "true", "f": "json"}
        )
        count = count_response.get("count")
        response = await self._collection_query(
            {"where": set_filter, "returnIdsOnly": "true", "f": "json"}
        )
        ids = response.get("objectIds")
        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            or response.get("objectIdFieldName") != "OBJECTID"
            or response.get("exceededTransferLimit", False) is not False
            or not isinstance(ids, list)
            or any(
                isinstance(value, bool) or not isinstance(value, int) or value <= 0
                for value in ids
            )
            or len(set(ids)) != count
            or len(ids) != count
        ):
            msg = "Arnhem count and unique object IDs differ"
            raise ODPArnhemError(msg)
        return set(ids)

    async def parking_collection(
        self,
        set_filter: str = "1=1",
        *,
        page_size: int = 500,
        max_records: int = 10000,
    ) -> ParkingCollection:
        """Fetch every selected object and verify selection membership again.

        Same-ID in-place edits are not a transactional snapshot guarantee.
        Source attributes and all geometry rings are retained for consumers.
        """
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or not 1 <= page_size <= 2000
            or isinstance(max_records, bool)
            or not isinstance(max_records, int)
            or max_records < 1
        ):
            msg = "Invalid Arnhem collection limits"
            raise ValueError(msg)
        expected = await self._selection_ids(set_filter)
        if len(expected) > max_records:
            msg = "Arnhem selection exceeds the collection limit"
            raise ODPArnhemError(msg)
        ordered_ids = sorted(expected)
        records: list[ParkingSpot] = []
        pages = 0
        for offset in range(0, len(ordered_ids), page_size):
            batch = ordered_ids[offset : offset + page_size]
            response = await self._collection_query(
                {
                    "where": set_filter,
                    "objectIds": ",".join(map(str, batch)),
                    "outFields": "*",
                    "outSR": "4326",
                    "f": "geojson",
                    "returnGeometry": "true",
                }
            )
            features = response.get("features")
            if (
                response.get("type") != "FeatureCollection"
                or "crs" in response
                or response.get("exceededTransferLimit", False) is not False
                or not isinstance(features, list)
                or len(features) != len(batch)
            ):
                msg = "Incomplete Arnhem feature batch"
                raise ODPArnhemError(msg)
            try:
                parsed = [ParkingSpot.from_geojson(item) for item in features]
            except (ValueError, TypeError, KeyError, AttributeError) as error:
                msg = "Invalid Arnhem source record"
                raise ODPArnhemError(msg) from error
            if {item.spot_id for item in parsed} != set(batch):
                msg = "Arnhem batch object IDs differ"
                raise ODPArnhemError(msg)
            records.extend(parsed)
            pages += 1
        if len({item.asset_id for item in records}) != len(expected):
            msg = "Duplicate Arnhem asset IDs"
            raise ODPArnhemError(msg)
        if await self._selection_ids(set_filter) != expected:
            msg = "Arnhem selection changed during collection"
            raise ODPArnhemError(msg)
        return ParkingCollection(records, len(expected), pages)

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> Self:
        """Async enter.

        Returns
        -------
            The Open Data Platform Arnhem object.

        """
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        """Async exit.

        Args:
        ----
            _exc_info: Exec type.

        """
        await self.close()
