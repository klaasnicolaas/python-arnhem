"""Asynchronous Python client providing Open Data information of Arnhem."""
from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass
from importlib import metadata
from typing import Any, cast

import async_timeout
from aiohttp import ClientError, ClientSession
from aiohttp.hdrs import METH_GET
from yarl import URL

from .exceptions import (
    ODPArnhemConnectionError,
    ODPArnhemError,
    ODPArnhemNoResultsError,
)
from .models import ParkingSpot


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
        version = metadata.version(__package__)
        url = URL.build(
            scheme="https",
            host="geo.arnhem.nl",
            path="/arcgis/rest/services/",
        ).join(
            URL(uri),
        )

        headers = {
            "Accept": "application/json",
            "User-Agent": f"PythonODPArnhem/{version}",
        }

        if self.session is None:
            self.session = ClientSession()
            self._close_session = True

        try:
            async with async_timeout.timeout(self.request_timeout):
                response = await self.session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    ssl=True,
                )
                response.raise_for_status()
        except asyncio.TimeoutError as exception:
            msg = "Timeout occurred while connecting to the Open Data Platform API."
            raise ODPArnhemConnectionError(msg) from exception
        except (ClientError, socket.gaierror) as exception:
            msg = "Error occurred while communicating with the Open Data Platform API."
            raise ODPArnhemConnectionError(msg) from exception

        content_type = response.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            text = await response.text()
            msg = "Unexpected content type response from the Open Data Platform API."
            raise ODPArnhemError(msg, {"Content-Type": content_type, "response": text})

        return cast(dict[str, Any], await response.json())

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
        results: list[ParkingSpot] = []
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
            for item in locations["features"]:
                results.append(ParkingSpot.from_json(item))
        except KeyError as exception:
            # when wrong filter is given
            raise ODPArnhemNoResultsError(msg) from exception

        # when filter is incorrect/empty
        if locations["features"] == []:
            raise ODPArnhemNoResultsError(msg)
        return results

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> ODPArnhem:
        """Async enter.

        Returns
        -------
            The Open Data Platform Arnhem object.
        """
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        """Async exit.

        Args:
        ----
            _exc_info: Exec type.
        """
        await self.close()
